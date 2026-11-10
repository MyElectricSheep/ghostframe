"""Ghostframe v1 raw-bit channel. Any image produces bits, even with a wrong key."""
import argparse
import hashlib
import math
import hmac
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import torch
import torch.nn.functional as F
from torchvision.models import squeezenet1_1


URL = "https://download.pytorch.org/models/squeezenet1_1-b8a52dc0.pth"
SHA256 = "b8a52dc049b60e4b6ab68ad0df457362afab8b6304b2febdc1650a5dab4d7e7b"
SIZE = 224
MAX_PIXELS = 4_000_000
DIM = 512


def load_checkpoint(url, sha256):
    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / url.rsplit("/", 1)[-1]
    if not checkpoint.exists():
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        torch.hub.download_url_to_file(url, str(checkpoint), hash_prefix=sha256)
    with checkpoint.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != sha256:
            raise ValueError(f"Unexpected checkpoint digest for {checkpoint}")
        file.seek(0)
        return torch.load(file, map_location="cpu", weights_only=True)


def load_model(device):
    weights = load_checkpoint(URL, SHA256)
    model = squeezenet1_1()
    model.load_state_dict(weights)
    return model.features.to(device).eval().requires_grad_(False)


def read_image(path):
    with Image.open(path, formats=["PNG", "JPEG"]) as image:
        if image.width * image.height > MAX_PIXELS or min(image.size) < 16:
            raise ValueError("Use a PNG or JPEG of at least 16 pixels per side and at most 4 MP")
        return ImageOps.exif_transpose(image).convert("RGB")


def tensor(image, device):
    rgb = np.array(image, dtype=np.uint8)
    return torch.from_numpy(rgb).permute(2, 0, 1)[None].to(device, torch.float32) / 255


def pixels(x):
    rgb = (x.detach()[0].permute(1, 2, 0) * 255).round().to(torch.uint8).cpu().numpy()
    return Image.fromarray(rgb)


def projections(key, length, device="cpu", *, dimension=DIM):
    if not key or not 1 <= length <= DIM:
        raise ValueError("Provide a nonempty key and a payload length from 1 to 512")
    if dimension < 8 or dimension % 8:
        raise ValueError("Projection dimension must be a positive multiple of eight")
    rows = []
    for index in range(length):
        domain = b"ghostframe/squeezenet/v1/" + index.to_bytes(2, "big")
        digest = hmac.digest(key.encode("utf-8"), domain, hashlib.sha256)
        signs = np.unpackbits(np.frombuffer(hashlib.shake_256(digest).digest(dimension // 8), np.uint8))
        rows.append(signs.astype(np.float32) * 2 - 1)
    return torch.from_numpy(np.stack(rows)).to(device) / dimension**0.5


def embedding(model, image):
    resized = F.interpolate(image, (SIZE, SIZE), mode="bilinear", align_corners=False, antialias=True)
    mean = resized.new_tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = resized.new_tensor([0.229, 0.224, 0.225])[None, :, None, None]
    feature = model((resized - mean) / std).mean(dim=(-1, -2))
    return F.normalize(feature, dim=-1)


def scores(model, image, carriers):
    return embedding(model, image) @ carriers.T


def decode(image, key, length, model):
    device = next(model.parameters()).device
    with torch.inference_mode():
        carriers = projections(key, length, device, dimension=getattr(model, "embedding_dim", DIM))
        signs = scores(model, tensor(image, device), carriers)[0] > 0
    return "".join(str(int(bit)) for bit in signs.tolist())


def encode(image, bits, key, model, *, steps=100, epsilon=8, margin=0.035, crops=(), carriers=None, extra_views=(), delta_stride=1):
    if not bits or set(bits) - {"0", "1"}:
        raise ValueError("Provide a nonempty binary string")
    if steps < 1 or not 1 <= epsilon <= 255 or not 0 < margin < 1:
        raise ValueError("Invalid optimization settings")
    if not isinstance(delta_stride, int) or delta_stride < 1:
        raise ValueError("delta_stride must be a positive integer")
    device = next(model.parameters()).device
    original = tensor(image, device)
    if carriers is None:
        carriers = projections(key, len(bits), device, dimension=getattr(model, "embedding_dim", DIM))
    targets = original.new_tensor([1 if bit == "1" else -1 for bit in bits])
    height, width = original.shape[-2:]
    if delta_stride == 1:
        delta = torch.zeros_like(original, requires_grad=True)
    else:
        grid = (math.ceil(height / delta_stride), math.ceil(width / delta_stride))
        delta = original.new_zeros((1, 3, *grid), requires_grad=True)
    optimizer = torch.optim.Adam([delta], lr=1 / 255)
    best_rank = (-1, -float("inf"))
    best_image = original
    for step in range(steps + 1):
        perturbation = delta if delta_stride == 1 else F.interpolate(
            delta, size=(height, width), mode="bilinear", align_corners=False
        )
        candidate = (original + perturbation).clamp(0, 1)
        quantized = (candidate * 255).round() / 255
        # The forward pass sees the exact 8-bit pixels that will be saved.
        straight_through = quantized.detach() + (candidate - candidate.detach())
        views = [straight_through]
        views.extend(straight_through[..., top:bottom, left:right]
                     for left, top, right, bottom in crops)
        views.extend(transform(straight_through) for transform in extra_views)
        signed = torch.cat([scores(model, view, carriers) for view in views]) * targets
        distortion = (candidate - original).square().mean()
        loss = (margin - signed).relu().square().mean() + 0.05 * distortion
        rank = (int(((signed.detach() > 0) | ((signed.detach() == 0) & (targets < 0))).sum()), -float(loss.detach()))
        if rank > best_rank:
            best_rank, best_image = rank, quantized.detach()
        if float(signed.detach().min()) >= margin or step == steps:
            break
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            delta.clamp_(-epsilon / 255, epsilon / 255)
    return pixels(best_image)


def transforms(image):
    for quality in (95, 85, 70):
        stream = io.BytesIO()
        image.save(stream, format="JPEG", quality=quality, subsampling=2)
        stream.seek(0)
        with Image.open(stream) as jpeg:
            yield f"jpeg{quality}_420", jpeg.convert("RGB")
    w, h = image.size
    yield "resize_75pct", image.resize((w * 3 // 4, h * 3 // 4), Image.Resampling.LANCZOS)
    yield "crop_center_90pct", image.crop((w//20, h//20, w-w//20, h-h//20))
    yield "brightness_105pct", ImageEnhance.Brightness(image).enhance(1.05)


def benchmark(args, model):
    from skimage.metrics import structural_similarity

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for index, path in enumerate(args.images):
        image = read_image(path)
        original = np.asarray(image, dtype=np.float32)
        for length in args.lengths:
            identity = f"{Path(path).name}/{length}/{args.seed}"
            payload = "".join(f"{byte:08b}" for byte in hashlib.shake_256(identity.encode()).digest((length+7)//8))[:length]
            start = perf_counter()
            marked = encode(image, payload, args.key, model, steps=args.steps, epsilon=args.epsilon)
            encode_s = perf_counter() - start
            stem = f"{index}-{Path(path).stem}-{length}"
            png = out / f"{stem}.png"
            marked.save(png)
            reopened = read_image(png)
            start = perf_counter()
            recovered = decode(reopened, args.key, length, model)
            decode_s = perf_counter() - start
            outcomes = {
                "cover": decode(image, args.key, length, model),
                "memory": decode(marked, args.key, length, model),
                "png": recovered,
                "wrong_key": decode(reopened, args.key + "-wrong", length, model),
            }
            for label, transformed in transforms(reopened):
                outcomes[label] = decode(transformed, args.key, length, model)
            result = {
                label: {"bits": value, "errors": sum(a != b for a, b in zip(payload, value))}
                for label, value in outcomes.items()
            }
            modified = np.asarray(reopened, dtype=np.float32)
            difference = np.abs(modified - original)
            Image.fromarray((difference * 24).clip(0, 255).astype(np.uint8)).save(out / f"{stem}-diff24x.png")
            mse = float(np.mean(difference**2))
            records.append(dict(
                image=Path(path).name, dimensions=image.size, target=payload, encoded_file=png.name,
                encode_s=encode_s, decode_s=decode_s, max_delta=float(difference.max()),
                mean_delta=float(difference.mean()), psnr_db=10 * math.log10(255**2 / mse) if mse else None,
                ssim=float(structural_similarity(original, modified, channel_axis=-1, data_range=255)),
                recovery=result,
            ))
            print(stem, result["png"]["errors"], flush=True)
    report = dict(
        model=URL, checkpoint_sha256=SHA256, torch_version=torch.__version__, device=args.device, threads=args.threads,
        steps=args.steps, epsilon=args.epsilon, seed=args.seed, records=records,
    )
    (out / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--threads", default=4, type=int)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("encode", "decode", "benchmark"):
        sub = commands.add_parser(command)
        sub.add_argument("--key", required=True, help="Experimental key only")
        if command in ("encode", "benchmark"):
            sub.add_argument("--output", required=True)
            sub.add_argument("--steps", default=100, type=int)
            sub.add_argument("--epsilon", default=8, type=int, help="Max RGB channel delta in 8-bit levels")
        if command in ("encode", "decode"):
            sub.add_argument("--image", required=True)
        if command == "encode":
            sub.add_argument("--bits", required=True)
        if command == "decode":
            sub.add_argument("--length", required=True, type=int)
        if command == "benchmark":
            sub.add_argument("--images", nargs="+", required=True)
            sub.add_argument("--lengths", nargs="+", type=int, default=[16, 32])
            sub.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        torch.set_num_threads(args.threads)
        model = load_model(args.device)
        if args.command == "benchmark":
            benchmark(args, model)
        elif args.command == "decode":
            print(decode(read_image(args.image), args.key, args.length, model))
        else:
            image = read_image(args.image)
            marked = encode(image, args.bits, args.key, model, steps=args.steps, epsilon=args.epsilon)
            if decode(marked, args.key, len(args.bits), model) != args.bits:
                parser.exit(2, "Encoding budget exhausted before exact recovery. No output written.\n")
            marked.save(args.output, format="PNG")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Ghostframe: {exc}\n")


if __name__ == "__main__":
    main()
