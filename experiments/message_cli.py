"""Local commands for the experimental 26-byte luminance profile."""
import argparse
from getpass import getpass
import io
import os
from pathlib import Path
import sys

import numpy as np
from tempfile import NamedTemporaryFile

from PIL import Image

from experiments.alignment_search import confidence_erasures, grid_phases, search_crop, search_exposure, search_resize
from experiments.jpeg_capacity import FRAME_BYTES, PARITY_BYTES, seal, unseal
from experiments.jpeg_carrier import BLOCK, embed, extract, positions
from experiments.robustness import COPIES, SPACING
from ghostframe import MAX_PIXELS, load_model, read_image


def recover_message(image, password, *, original_size=None, crop_size=None, try_resize=False,
                    wide_resize=False, try_exposure=False, soft=False):
    if crop_size is not None:
        if original_size is None:
            raise ValueError("Crop size requires original dimensions")
        if (min(crop_size) < 16 or crop_size[0] * crop_size[1] > MAX_PIXELS
                or any(crop > original for crop, original in zip(crop_size, original_size, strict=True))):
            raise ValueError("Crop dimensions must fit within the original and the four-megapixel limit")
    try:
        return unseal(extract(image, SPACING, COPIES, FRAME_BYTES), password)
    except ValueError:
        pass
    recovered = None

    def verify(received, erasures):
        nonlocal recovered
        try:
            recovered = unseal(received, password, erasures=erasures)
        except ValueError:
            return False
        return True

    bits = FRAME_BYTES * 8
    if soft:
        try:
            y, x = positions(image.size, COPIES, bits)
        except ValueError:
            pass
        else:
            scores = grid_phases(image)[y[:, 0, 0] // BLOCK, x[:, 0, 0] // BLOCK]
            scores = scores.reshape(COPIES, bits).sum(axis=0)
            received = np.packbits(scores < 0).tobytes()
            for erasures in confidence_erasures(scores, [], PARITY_BYTES):
                if verify(received, erasures):
                    return recovered

    settings = dict(bits=bits, parity_bytes=PARITY_BYTES, verify=verify, soft=soft)
    if original_size is not None:
        crop = image.resize(crop_size, Image.Resampling.LANCZOS) if crop_size is not None else image
        search_crop(crop, original_size, **settings)
    elif try_resize or wide_resize:
        search_resize(image, wide=wide_resize, **settings)
    elif try_exposure:
        search_exposure(image, **settings)
    if recovered is None:
        raise ValueError("No authenticated message recovered")
    return recovered


def neural_recover(image, password, model, *, ecc=False):
    from experiments import tiled, tiled_ecc

    frame = int(tiled.read_tiles(image, model), 2).to_bytes(tiled.FRAME_BYTES, "big")
    return tiled_ecc.decode_frame(frame, password)[0] if ecc else tiled.open_frame(frame, password)


def neural_encode_file(image, message, password, output, model, *, ecc=False, progress=None):
    from reedsolo import RSCodec
    from experiments import tiled, tiled_ecc

    if output.suffix.lower() != ".png":
        raise ValueError("The neural message carrier requires PNG output")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    if ecc:
        frame = RSCodec(tiled_ecc.PARITY_BYTES).encode(tiled_ecc.seal(message, password))
    else:
        frame = tiled.seal(message, password)
    marked = tiled.embed_tiles(image, tiled.bit_string(frame), model, 2 if ecc else 8, progress=progress)
    publish_encoded(marked, output, lambda reopened: neural_recover(reopened, password, model, ecc=ecc) == message)


def encode_file(image, message, password, output):
    suffix = output.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Output must end in .png, .jpg or .jpeg")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    marked = embed(image, seal(message, password), SPACING, COPIES)
    publish_encoded(marked, output, lambda reopened: recover_message(reopened, password) == message)


def publish_encoded(marked, output, verify):
    suffix = output.suffix.lower()
    # Serialize pixels only. The marked image inherits the cover's info dict, and
    # Pillow would otherwise copy its ICC profile into the output file.
    marked = Image.fromarray(np.asarray(marked.convert("RGB")))
    with io.BytesIO() as buffer:
        if suffix == ".png":
            marked.save(buffer, format="PNG")
        else:
            marked.save(buffer, format="JPEG", quality=95, subsampling=2)
        encoded = buffer.getvalue()
    with Image.open(io.BytesIO(encoded)) as reopened:
        if not verify(reopened):
            raise ValueError("Serialized output failed its authentication check")
    with NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(encoded)
            temporary.close()
            os.link(temporary_path, output)
        finally:
            temporary_path.unlink()


def read_password(path):
    if path is None:
        if not sys.stdin.isatty():
            raise ValueError("Use --passphrase-file for non-interactive input")
        password = getpass("Passphrase: ").encode("utf-8")
    else:
        password = path.read_bytes().rstrip(b"\r\n")
    if not password:
        raise ValueError("Passphrase cannot be empty")
    return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    encoder = modes.add_parser("encode")
    encoder.add_argument("input", type=Path)
    encoder.add_argument("output", type=Path)
    encoder.add_argument("--message-file", type=Path, required=True)
    decoder = modes.add_parser("decode")
    decoder.add_argument("input", type=Path)
    geometry = decoder.add_mutually_exclusive_group()
    geometry.add_argument("--original-size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"))
    geometry.add_argument("--try-resize", action="store_true")
    geometry.add_argument("--wide-resize", action="store_true")
    geometry.add_argument("--try-exposure", action="store_true")
    decoder.add_argument("--crop-size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"),
                         help="Crop dimensions before resizing, with --original-size")
    decoder.add_argument("--soft", action="store_true", help="Retry low-confidence bytes as erasures")
    for mode in (encoder, decoder):
        mode.add_argument("--passphrase-file", type=Path)
        mode.add_argument("--carrier", choices=("luminance", "neural", "neural-ecc"), default="luminance")
    args = parser.parse_args()
    if args.mode == "decode" and args.crop_size is not None and args.original_size is None:
        parser.error("--crop-size requires --original-size")
    try:
        password = read_password(args.passphrase_file)
        image = read_image(args.input)
        if args.carrier != "luminance":
            import torch

            if args.mode == "decode" and any((args.original_size, args.crop_size, args.try_resize,
                                               args.wide_resize, args.try_exposure, args.soft)):
                raise ValueError("Neural decoding expects preserved PNG pixels")
            torch.set_num_threads(4)
            model = load_model("cpu")
            ecc = args.carrier == "neural-ecc"
            if args.mode == "encode":
                neural_encode_file(image, args.message_file.read_bytes(), password, args.output, model, ecc=ecc)
            else:
                sys.stdout.buffer.write(neural_recover(image, password, model, ecc=ecc))
        elif args.mode == "encode":
            encode_file(image, args.message_file.read_bytes(), password, args.output)
        else:
            message = recover_message(image, password, original_size=args.original_size, crop_size=args.crop_size,
                                      try_resize=args.try_resize, wide_resize=args.wide_resize,
                                      try_exposure=args.try_exposure, soft=args.soft)
            sys.stdout.buffer.write(message)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Ghostframe: {exc}\n")


if __name__ == "__main__":
    main()
