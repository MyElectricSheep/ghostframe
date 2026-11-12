"""Profiles, framing, error correction, embedding and safe image I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import io
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageOps
import torch
import torch.nn.functional as F

from ghostframe import SHA256 as CHECKPOINT_SHA256, embedding
from ghostframe_png import backbones

MAX_PIXELS = 4_000_000
SALT_BYTES = 16
TAG_BYTES = 16
RS_BLOCK = 255
DATA_DIR = Path(__file__).with_name("data")
CALIBRATION = DATA_DIR / "squeezenet1_1-tile-mean-v1.npy"
CALIBRATION_PIN = "e3bc8df735be7085095f21733ce455190c5ac77ec3782279f93d829d7910648e"


class InputError(ValueError):
    """The image or request is outside the supported contract."""


class CapacityError(ValueError):
    """The message does not fit the selected profile."""


class DecodeError(ValueError):
    """No authenticated frame was recovered. Never carries partial plaintext."""


@dataclass(frozen=True)
class Profile:
    name: str
    cols: int
    rows: int
    bits: int                  # projection signs per tile
    parity: int                # total Reed-Solomon parity bytes across all blocks
    epsilon: int               # maximum change per RGB channel, in 8-bit levels
    centered: bool = True      # remove the calibration mean from each direction
    margin: float = 0.01       # optimizer target for every signed score
    safety: float = 0.002      # scores below this count as possible errors (numerics are ~1e-7)
    steps: int = 40            # optimizer updates per tile per round
    rounds: int = 3            # repair rounds for tiles holding at-risk bytes
    lr: float = 1.0            # Adam step size in 8-bit levels
    min_tile: int = 16
    experimental: bool = True
    notes: str = ""
    aad_extra: tuple = field(default=(), compare=False)
    backbone: str = "squeezenet1_1"  # frozen feature extractor; others live in backbones.py

    @property
    def codeword_bytes(self):
        return self.cols * self.rows * self.bits // 8

    @property
    def blocks(self):
        return -(-self.codeword_bytes // RS_BLOCK)

    def block_layout(self):
        """Per-block (codeword length, parity) for an interleaved codeword."""
        n, b = self.codeword_bytes, self.blocks
        lengths = [n // b + (i < n % b) for i in range(b)]
        parities = [self.parity // b + (i < self.parity % b) for i in range(b)]
        return list(zip(lengths, parities))

    @property
    def frame_bytes(self):
        return self.codeword_bytes - self.parity

    @property
    def length_bytes(self):
        return 1 if self.frame_bytes - SALT_BYTES - TAG_BYTES - 1 <= 255 else 2

    @property
    def capacity(self):
        return self.frame_bytes - SALT_BYTES - TAG_BYTES - self.length_bytes

    @property
    def identity(self):
        if self.backbone != "squeezenet1_1":  # SqueezeNet identities stay exactly as scored
            backbone = backbones.BACKBONES[self.backbone]
            fields = (self.name, self.cols, self.rows, self.bits, self.parity, int(self.centered),
                      self.backbone, backbone.sha256[:16],
                      backbones.calibration_mean(backbone)[1][:16] if self.centered else "-")
            return "ghostframe-png/v1/" + "/".join(map(str, fields))
        fields = (self.name, self.cols, self.rows, self.bits, self.parity, int(self.centered),
                  CHECKPOINT_SHA256[:16], _calibration_digest()[:16] if self.centered else "-")
        return "ghostframe-png/v1/" + "/".join(map(str, fields))

    @property
    def dim(self):
        return 512 if self.backbone == "squeezenet1_1" else backbones.BACKBONES[self.backbone].dim

    def validate(self):
        if self.cols * self.rows * self.bits % 8:
            raise ValueError(f"{self.name}: codeword is not a whole number of bytes")
        if any(p >= n or n - p < 1 for n, p in self.block_layout()):
            raise ValueError(f"{self.name}: parity leaves no data in a block")
        if self.capacity < 1:
            raise ValueError(f"{self.name}: no room for a payload")
        if not 1 <= self.bits <= self.dim:
            raise ValueError(f"{self.name}: bits per tile must be 1-{self.dim}")


def _p(name, cols, rows, bits, parity, epsilon, **kw):
    profile = Profile(name, cols, rows, bits, parity, epsilon, **kw)
    profile.validate()
    return profile


# Registered profiles. Promotion decisions and evidence: docs/PNG_PROFILES.md.
PROFILES = {p.name: p for p in (
    _p("png-l2-c10x8b12", 10, 8, 12, 24, 2, notes="Low-distortion candidate on the 49-byte legacy layout"),
    _p("png-l8-c10x8b24", 10, 8, 24, 32, 8, notes="High-capacity candidate on the 161-byte legacy layout"),
    # Preregistered finalists, kept under the names they were scored with (the name is part of
    # the identity, so renaming would change the carriers). Evidence: docs/BENCHMARK.md.
    _p("sw-l2-c10x8b16p48", 10, 8, 16, 48, 2, notes="Recommended experimental 2-level profile (79 B)"),
    _p("sw-l8-c10x8b40p64", 10, 8, 40, 64, 8, notes="Recommended experimental 8-level profile (302 B)"),
    # MobileNetV3-Small backbone, held out under bench/PREREGISTRATION-BACKBONES.md. Margins are
    # SqueezeNet's scaled by the backbone's median clean |score| (1.0805).
    *(_p(f"bb-mobilenet_v3_small-l{cap}-b{bits}p{parity}", 10, 8, bits, parity, cap, backbone="mobilenet_v3_small",
         margin=0.010805, safety=0.002161, notes=notes) for cap, bits, parity, notes in (
        (2, 16, 48, "Recommended experimental MobileNetV3 2-level profile (79 B)"),
        (8, 40, 64, "Recommended experimental MobileNetV3 8-level profile (302 B)"),
        (8, 64, 112, "Recommended experimental MobileNetV3 8-level profile (494 B)"))),
)}


def register(profile):
    profile.validate()
    PROFILES[profile.name] = profile
    return profile


def capacity(profile):
    return PROFILES[profile].capacity if isinstance(profile, str) else profile.capacity


# --------------------------------------------------------------------------- image I/O

def _open(path, formats):
    try:
        image = Image.open(path, formats=formats)
    except Image.UnidentifiedImageError as exc:
        raise InputError(f"Unsupported image format; expected {'/'.join(formats)}") from exc
    if image.width * image.height > MAX_PIXELS:
        image.close()
        raise InputError(f"Image exceeds {MAX_PIXELS} pixels")
    return image


SRGB_NAMES = ("sRGB", "c2")  # "c2" is the compact sRGB profile Wikimedia thumbnails embed.


def _to_rgb(image, info=None):
    """8-bit sRGB pixels. Other colour profiles are converted with LittleCMS (perceptual intent)."""
    if image.mode in ("I", "F") or image.mode.startswith("I;16"):
        raise InputError(f"Unsupported {image.mode} image: use 8-bit RGB")
    if image.mode in ("CMYK", "LAB", "HSV", "YCbCr"):
        raise InputError(f"Unsupported {image.mode} image: convert to sRGB first")
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode in ("RGBA", "LA", "PA", "RGBa", "La"):
        if np.asarray(image.getchannel("A")).min() < 255:
            raise InputError("Image has transparent pixels: flatten it onto a background first")
        image = image.convert("RGB" if image.mode in ("RGBA", "RGBa", "PA") else "L")
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    icc = image.info.get("icc_profile")
    if icc:
        from PIL import ImageCms

        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            name = ImageCms.getProfileDescription(source).strip()
            if not any(tag in name for tag in SRGB_NAMES):
                image = ImageCms.profileToProfile(image, source, ImageCms.createProfile("sRGB"),
                                                  renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="RGB")
                if info is not None:
                    info["colour_conversion"] = f"{name} -> sRGB"
        except (ImageCms.PyCMSError, OSError) as exc:
            raise InputError(f"Unreadable colour profile: {exc}") from exc
    return image.convert("RGB")


def load_cover(path, info=None):
    """Read a PNG or JPEG cover as sRGB. Applies EXIF orientation; nothing else is carried over."""
    with _open(path, ["PNG", "JPEG"]) as image:
        image.load()
        return np.array(_to_rgb(ImageOps.exif_transpose(image), info), dtype=np.uint8)


def load_png(path):
    """Read a marked PNG. Only pixel values are used; metadata and orientation are ignored."""
    with _open(path, ["PNG"]) as image:
        image.load()
        return np.array(_to_rgb(image), dtype=np.uint8)


def png_bytes(rgb):
    """Serialize pixels only: a fresh image object carries no ICC, EXIF or text chunks."""
    buffer = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgb, dtype=np.uint8), "RGB").save(buffer, format="PNG", compress_level=6)
    return buffer.getvalue()


def check_output(path):
    path = Path(path)
    if path.suffix.lower() != ".png":
        raise InputError("Output must be a .png file")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Output already exists: {path}")
    if not path.parent.is_dir():
        raise InputError(f"Output directory does not exist: {path.parent}")
    if not os.access(path.parent, os.W_OK):
        raise InputError(f"Output directory is not writable: {path.parent}")
    return path


def write_new(path, data):
    """Write bytes to a new file without ever replacing an existing one or leaving a partial file."""
    path = check_output(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ghostframe-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise
        except OSError:  # Filesystems without hard links.
            with open(path, "xb") as handle:
                handle.write(data)
    finally:
        os.unlink(temporary)


# --------------------------------------------------------------------------- geometry and carriers

def tile_boxes(shape, profile):
    height, width = shape[:2]
    if min(width // profile.cols, height // profile.rows) < profile.min_tile:
        raise InputError(
            f"Image is too small for {profile.name}: needs at least "
            f"{profile.cols * profile.min_tile}x{profile.rows * profile.min_tile} pixels")
    return [(c * width // profile.cols, r * height // profile.rows,
             (c + 1) * width // profile.cols, (r + 1) * height // profile.rows)
            for r in range(profile.rows) for c in range(profile.cols)]


_calibration_cache = {}


def _calibration_digest():
    if "sha" not in _calibration_cache:
        _calibration_cache["sha"] = hashlib.sha256(CALIBRATION.read_bytes()).hexdigest()
        if _calibration_cache["sha"] != CALIBRATION_PIN:
            raise RuntimeError(f"Unexpected calibration digest for {CALIBRATION}")
    return _calibration_cache["sha"]


def _calibration():
    if "mean" not in _calibration_cache:
        _calibration_digest()
        mean = torch.from_numpy(np.load(CALIBRATION, allow_pickle=False).astype(np.float32))
        _calibration_cache["mean"] = mean / mean.norm()
    return _calibration_cache["mean"]


_carrier_cache = {}


def carriers(profile, index):
    """Unit directions for one tile. Public: confidentiality comes from the frame."""
    key = (profile.identity, index)
    if key not in _carrier_cache:
        rows = []
        for bit in range(profile.bits):
            domain = f"{profile.identity}/tile/{index}/bit/{bit}".encode()
            digest = hmac.digest(b"ghostframe-png public carriers", domain, hashlib.sha256)
            signs = np.unpackbits(np.frombuffer(hashlib.shake_256(digest).digest(profile.dim // 8), np.uint8))
            rows.append(signs.astype(np.float32) * 2 - 1)
        matrix = torch.from_numpy(np.stack(rows))
        if profile.centered:
            mean = _calibration() if profile.backbone == "squeezenet1_1" else \
                backbones.calibration_mean(backbones.BACKBONES[profile.backbone])[0]
            matrix = matrix - (matrix @ mean)[:, None] * mean
        _carrier_cache[key] = matrix / matrix.norm(dim=1, keepdim=True)
    return _carrier_cache[key]


# --------------------------------------------------------------------------- frame and ECC

def _keys(passphrase, salt):
    material = hashlib.scrypt(passphrase, salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024**2, dklen=44)
    return material[:32], material[32:]


def seal(message, passphrase, profile, *, _salt=None):
    """salt(16) || AES-256-GCM(len || message || zero padding) || tag(16).

    Key and nonce both come from scrypt(passphrase, salt), so every frame uses a fresh
    key. ``_salt`` exists for benchmark fixtures only; production callers leave it unset.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not isinstance(message, (bytes, bytearray)):
        raise TypeError("Message must be bytes")
    if len(message) > profile.capacity:
        raise CapacityError(f"Message is {len(message)} bytes; {profile.name} carries at most {profile.capacity}")
    if not passphrase:
        raise InputError("Passphrase cannot be empty")
    salt = os.urandom(SALT_BYTES) if _salt is None else bytes(_salt)
    key, nonce = _keys(passphrase, salt)
    plain = len(message).to_bytes(profile.length_bytes, "big") + bytes(message)
    plain = plain.ljust(profile.frame_bytes - SALT_BYTES - TAG_BYTES, b"\0")
    return salt + AESGCM(key).encrypt(nonce, plain, profile.identity.encode())


def open_frame(frame, passphrase, profile, *, _key_cache=None):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(frame) != profile.frame_bytes:
        raise DecodeError("Invalid frame")
    salt = bytes(frame[:SALT_BYTES])
    cache = {} if _key_cache is None else _key_cache
    if salt not in cache:
        cache[salt] = _keys(passphrase, salt)
    key, nonce = cache[salt]
    try:
        plain = AESGCM(key).decrypt(nonce, bytes(frame[SALT_BYTES:]), profile.identity.encode())
    except InvalidTag as exc:
        raise DecodeError("Invalid frame") from exc
    length = int.from_bytes(plain[:profile.length_bytes], "big")
    body = plain[profile.length_bytes:]
    if length > profile.capacity or any(body[length:]):
        raise DecodeError("Invalid frame")
    return body[:length]


def _interleave_index(profile):
    """Codeword byte j belongs to block j % blocks, so a damaged tile spreads across blocks."""
    b = profile.blocks
    return [np.arange(i, profile.codeword_bytes, b) for i in range(b)]


def rs_encode(frame, profile):
    from reedsolo import RSCodec

    layout, slots = profile.block_layout(), _interleave_index(profile)
    codeword = np.zeros(profile.codeword_bytes, np.uint8)
    offset = 0
    for (length, parity), slot in zip(layout, slots, strict=True):
        data = frame[offset:offset + length - parity]
        offset += length - parity
        block = bytes(RSCodec(parity).encode(data)) if parity else bytes(data)
        assert len(block) == length == len(slot)
        codeword[slot] = np.frombuffer(block, np.uint8)
    assert offset == len(frame)
    return codeword.tobytes()


def rs_candidates(received, confidence, profile, levels=(0, .25, .5, .75, 1.0)):
    """Yield (frame, corrected_symbols, erasures) candidates; every one still needs authentication."""
    from reedsolo import RSCodec, ReedSolomonError

    received = np.frombuffer(bytes(received), np.uint8)
    layout, slots = profile.block_layout(), _interleave_index(profile)
    seen = set()
    for level in levels:
        parts, corrected, erased = [], 0, 0
        for (length, parity), slot in zip(layout, slots, strict=True):
            block, conf = received[slot].tobytes(), confidence[slot]
            if not parity:
                parts.append(block)
                continue
            erase = [int(i) for i in np.argsort(conf, kind="stable")[:int(parity * level)]]
            decoded = None
            for attempt in (erase, []) if erase else ([],):
                try:
                    message, _, errata = RSCodec(parity).decode(block, erase_pos=attempt or None)
                    decoded = bytes(message)
                    corrected += len(errata)
                    erased += len(attempt)
                    break
                except (ReedSolomonError, ZeroDivisionError, ValueError, IndexError):
                    continue
            if decoded is None:
                break
            parts.append(decoded)
        else:
            frame = b"".join(parts)
            if frame not in seen:
                seen.add(frame)
                yield frame, corrected, erased


# --------------------------------------------------------------------------- channel

def _tensor(rgb):
    return torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1)[None].float() / 255


def _embed(model, image):
    embed = getattr(model, "ghostframe_embed", None)
    return embed(image) if embed else embedding(model, image)


def read_scores(rgb, profile, model):
    """Signed scores for every carrier bit, tile-major. One independent forward pass per tile."""
    out = []
    with torch.inference_mode():
        for index, (l, t, r, b) in enumerate(tile_boxes(rgb.shape, profile)):
            out.append((_embed(model, _tensor(rgb[t:b, l:r])) @ carriers(profile, index).T)[0])
    return torch.cat(out).numpy()


def scores_to_bytes(scores):
    bits = scores > 0
    confidence = np.abs(scores).reshape(-1, 8).min(axis=1)
    return np.packbits(bits).tobytes(), confidence


def _optimize(model, cover_tiles, start_tiles, directions, targets, profile, steps, batch=16, on_step=None):
    """Sign-margin optimization on quantized pixels (straight-through estimator).

    Tiles leave the batch as soon as every signed score reaches the margin, and the
    remaining active tiles are re-batched each step, so finished tiles cost nothing.
    Adam runs per tile (bias-corrected by each tile's own step count).
    `on_step(finished, steps_done)` is called after every step; it only observes.
    """
    eps, lr = profile.epsilon / 255, profile.lr / 255
    n = len(cover_tiles)
    delta = (start_tiles - cover_tiles).clone()
    m, v = torch.zeros_like(delta), torch.zeros_like(delta)
    t = torch.zeros(n)
    best = start_tiles.clone()
    best_key = torch.full((n,), -float("inf"))
    active = torch.ones(n, dtype=torch.bool)
    for step in range(steps + 1):
        index = active.nonzero().flatten()
        if not len(index):
            break
        for chunk in index.split(batch):
            d = delta[chunk].clone().requires_grad_(True)
            candidate = (cover_tiles[chunk] + d).clamp(0, 1)
            quantized = (candidate * 255).round() / 255
            straight = quantized.detach() + (candidate - candidate.detach())
            signed = torch.einsum("bd,bnd->bn", _embed(model, straight), directions[chunk]) * targets[chunk]
            worst = signed.detach().min(dim=1).values
            key = torch.minimum(worst, torch.tensor(profile.margin))
            improve = key > best_key[chunk]
            best[chunk[improve]] = quantized.detach()[improve]
            best_key[chunk[improve]] = key[improve]
            done = worst >= profile.margin
            active[chunk[done]] = False
            if step == steps or done.all():
                continue
            loss = (profile.margin * 1.25 - signed[~done]).relu().square().sum()
            (grad,) = torch.autograd.grad(loss, d)
            with torch.no_grad():
                live = chunk[~done]
                g = grad[~done]
                t[live] += 1
                m[live] = 0.9 * m[live] + 0.1 * g
                v[live] = 0.999 * v[live] + 0.001 * g.square()
                c1 = (1 - 0.9 ** t[live]).view(-1, 1, 1, 1)
                c2 = (1 - 0.999 ** t[live]).view(-1, 1, 1, 1)
                delta[live] = (delta[live] - lr * (m[live] / c1) / ((v[live] / c2).sqrt() + 1e-8)).clamp(-eps, eps)
        if on_step is not None:
            on_step(int((~active).sum()), step + 1)
    return best


def safety_report(signed_bits, profile):
    """Per-block wrong and at-risk bytes. Safe when 2 * (wrong + at_risk) <= parity in every block."""
    per_byte = signed_bits.reshape(-1, 8).min(axis=1)
    wrong, risky = per_byte <= 0, (per_byte > 0) & (per_byte < profile.safety)
    blocks = []
    for (length, parity), slot in zip(profile.block_layout(), _interleave_index(profile), strict=True):
        blocks.append(dict(wrong=int(wrong[slot].sum()), at_risk=int(risky[slot].sum()), parity=parity,
                           safe=2 * int(wrong[slot].sum() + risky[slot].sum()) <= parity))
    return blocks


BATCH = 16  # tiles per optimizer pass; memory and speed only, each tile is optimized independently


def _round_span(round_index, rounds):
    """Share of the progress bar for each round: the first round does almost all the work."""
    if round_index == 0:
        return 0.0, 0.9 if rounds > 1 else 1.0
    step = 0.1 / (rounds - 1)
    return 0.9 + step * (round_index - 1), 0.9 + step * round_index


def embed(cover, codeword, profile, model, *, batch=None, progress=None):
    """Return marked RGB pixels and per-round diagnostics. Cover is HxWx3 uint8.

    `progress(fraction)` is called with an estimate in [0, 1]. It only observes: the pixels are
    the same with or without it. It may raise to cancel; nothing is returned or written then.
    """
    batch = batch or BATCH
    boxes = tile_boxes(cover.shape, profile)
    bits = np.unpackbits(np.frombuffer(codeword, np.uint8)).reshape(len(boxes), profile.bits)
    targets = torch.from_numpy(bits.astype(np.float32) * 2 - 1)
    marked = cover.copy()
    pending = list(range(len(boxes)))
    history = []
    for round_index in range(profile.rounds):
        low, high = _round_span(round_index, profile.rounds)
        total, finished_groups = max(1, len(pending)), 0
        groups = {}
        for i in pending:
            l, t, r, b = boxes[i]
            groups.setdefault((r - l, b - t), []).append(i)
        for group in groups.values():
            take = lambda array: torch.cat([_tensor(array[boxes[i][1]:boxes[i][3], boxes[i][0]:boxes[i][2]])
                                           for i in group])
            on_step = None
            if progress is not None:
                def on_step(finished, steps_done, size=len(group), base=finished_groups):
                    share = max(finished / size, steps_done / (profile.steps + 1))
                    progress(low + (high - low) * (base + share * size) / total)
            result = _optimize(model, take(cover), take(marked), torch.stack([carriers(profile, i) for i in group]),
                               targets[group], profile, profile.steps, batch, on_step)
            finished_groups += len(group)
            for i, tile in zip(group, result, strict=True):
                l, t, r, b = boxes[i]
                marked[t:b, l:r] = (tile.permute(1, 2, 0) * 255).round().to(torch.uint8).numpy()
        # Verify on the serialized pixels with the independent single-tile reader.
        reopened = np.asarray(Image.open(io.BytesIO(png_bytes(marked))).convert("RGB"))
        signed = read_scores(reopened, profile, model) * targets.numpy().reshape(-1)
        blocks = safety_report(signed, profile)
        per_tile = signed.reshape(len(boxes), -1).min(axis=1)
        pending = [i for i in range(len(boxes)) if per_tile[i] < profile.safety]
        history.append(dict(round=round_index, tiles_at_risk=len(pending), bit_errors=int((signed <= 0).sum()),
                            wrong_bytes=sum(b["wrong"] for b in blocks), at_risk_bytes=sum(b["at_risk"] for b in blocks),
                            min_signed=float(signed.min()), safe=all(b["safe"] for b in blocks)))
        if history[-1]["safe"]:
            break
    assert int(np.abs(marked.astype(np.int16) - cover).max()) <= profile.epsilon
    return marked, history


# --------------------------------------------------------------------------- message API

def decode_message(rgb, passphrase, profile, model, *, soft=True, report=None):
    """Return authenticated plaintext or raise DecodeError. Bounded work for any input."""
    if isinstance(profile, str):
        profile = PROFILES[profile]
    received, confidence = scores_to_bytes(read_scores(rgb, profile, model))
    keys = {}
    levels = (0, .25, .5, .75, 1.0) if soft else (0,)
    for frame, corrected, erased in rs_candidates(received, confidence, profile, levels):
        if len(keys) >= 8:
            break
        try:
            message = open_frame(frame, passphrase, profile, _key_cache=keys)
        except DecodeError:
            continue
        if report is not None:
            report.update(corrected_symbols=corrected, erasures=erased, received=received)
        return message
    if report is not None:
        report.update(received=received)
    raise DecodeError("No authenticated message recovered")


def encode_message(cover, message, passphrase, profile, model, *, attempts=2, report=None, progress=None, _salt=None):
    """Mark a cover and return PNG bytes that were verified to authenticate after reopening.

    `progress(fraction)` receives a non-decreasing estimate in [0, 1], ending at 1.0 on success.
    It never changes the result, and it may raise to cancel the encode.
    """
    if isinstance(profile, str):
        profile = PROFILES[profile]
    tile_boxes(cover.shape, profile)
    shown = [0.0]

    def report_progress(fraction, start=0.0):
        value = min(1.0, start + (1 - start) * fraction)
        if value > shown[0]:
            shown[0] = value
            progress(value)

    for attempt in range(attempts):
        frame = seal(message, passphrase, profile, _salt=_salt if attempt == 0 else None)
        codeword = rs_encode(frame, profile)
        # A second attempt continues from where the bar stopped instead of going backwards.
        start = shown[0]
        on_progress = None if progress is None else (lambda f, start=start: report_progress(0.98 * f, start))
        marked, history = embed(cover, codeword, profile, model, progress=on_progress)
        data = png_bytes(marked)
        reopened = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
        info = {}
        try:
            ok = history[-1]["safe"] and decode_message(reopened, passphrase, profile, model, report=info) == message
        except DecodeError:
            ok = False
        if report is not None:
            received = info.get("received")
            report.setdefault("attempts", []).append(dict(
                history=history, authenticated=ok,
                byte_errors=None if received is None else sum(a != b for a, b in zip(received, codeword)),
                corrected_symbols=info.get("corrected_symbols"), erasures=info.get("erasures")))
            report["codeword"] = codeword
        if ok:
            if progress is not None:
                report_progress(1.0)
            return data
    raise CapacityError("Encoding budget exhausted before the saved PNG authenticated. No output written.")
