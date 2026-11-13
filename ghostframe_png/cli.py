"""ghostframe-png: authenticated messages in frozen-model embeddings of PNG tiles.

Exit status: 0 success, 1 no authenticated message, 2 invalid input or usage,
3 message too large or encoding budget exhausted (no output is written).
"""
import argparse
from getpass import getpass
import os
from pathlib import Path
import sys

LEGACY = {
    "legacy-v1": dict(capacity=13, epsilon=8, ecc=False, notes="Original 6x5 neural CLI frame (message_cli --carrier neural)"),
    "legacy-v2": dict(capacity=1, epsilon=2, ecc=True, notes="Original one-byte RS frame (message_cli --carrier neural-ecc)"),
}


def read_passphrase(path):
    if path is None:
        if not sys.stdin.isatty():
            raise ValueError("Use --passphrase-file for non-interactive input")
        passphrase = getpass("Passphrase: ").encode("utf-8")
    else:
        passphrase = Path(path).read_bytes().rstrip(b"\r\n")
    if not passphrase:
        raise ValueError("Passphrase cannot be empty")
    return passphrase


def read_message(path, limit):
    stream = sys.stdin.buffer if path == "-" else open(path, "rb")
    with stream:
        data = stream.read(limit + 1)
    return data


def list_profiles():
    from ghostframe_png.core import PROFILES

    print(f"{'profile':32s} {'bytes':>5s} {'cap':>4s}  status        notes")
    for name, profile in PROFILES.items():
        status = "experimental" if profile.experimental else "default"
        print(f"{name:32s} {profile.capacity:5d} {profile.epsilon:4d}  {status:12s}  {profile.notes}")
    for name, info in LEGACY.items():
        print(f"{name:32s} {info['capacity']:5d} {info['epsilon']:4d}  {'legacy':12s}  {info['notes']}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ghostframe-png", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threads", type=int, default=min(4, os.cpu_count() or 1))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("profiles", help="list profiles, capacities and RGB caps")
    encoder = commands.add_parser("encode", help="mark a PNG/JPEG cover and write a new PNG")
    encoder.add_argument("cover", type=Path)
    encoder.add_argument("output", type=Path)
    encoder.add_argument("--message-file", required=True, help="file with the exact message bytes, or - for stdin")
    decoder = commands.add_parser("decode", help="write the authenticated message bytes to stdout")
    decoder.add_argument("image", type=Path)
    for command in (encoder, decoder):
        command.add_argument("--profile", required=True)
        command.add_argument("--passphrase-file", type=Path)
    args = parser.parse_args(argv)
    if args.command == "profiles":
        list_profiles()
        return 0

    from ghostframe_png import core

    if args.profile not in core.PROFILES and args.profile not in LEGACY:
        parser.exit(2, f"ghostframe-png: unknown profile {args.profile!r}; see 'ghostframe-png profiles'\n")
    if args.threads < 1:
        parser.exit(2, "ghostframe-png: --threads must be positive\n")
    if args.profile in LEGACY:
        try:
            from experiments import tiled
            from experiments.message_cli import neural_encode_file, neural_recover
        except ModuleNotFoundError as exc:
            if not (exc.name or "").startswith("experiments"):
                raise
            parser.exit(2, "ghostframe-png: legacy profiles need a clone of the repository (they use its "
                           "experiments/ folder, which is not installed); run from the repository root\n")
    try:
        passphrase = read_passphrase(args.passphrase_file)
        if args.command == "encode":
            core.check_output(args.output)  # Fail before the expensive optimization.
            limit = LEGACY[args.profile]["capacity"] if args.profile in LEGACY else core.PROFILES[args.profile].capacity
            message = read_message(args.message_file, limit)
            if len(message) > limit:
                raise core.CapacityError(f"Message exceeds {limit} bytes for {args.profile}")
        import torch
        from ghostframe import load_model

        torch.set_num_threads(args.threads)
        backbone = "squeezenet1_1" if args.profile in LEGACY else core.PROFILES[args.profile].backbone
        if backbone == "squeezenet1_1":
            model = load_model("cpu")
        else:
            from ghostframe_png import backbones

            model = backbones.load(backbone)
        if args.profile in LEGACY:
            from ghostframe import read_image

            ecc = LEGACY[args.profile]["ecc"]
            if args.command == "decode":
                core.load_png(args.image)  # Same input contract as the new profiles.
            try:
                image = read_image(args.cover if args.command == "encode" else args.image)
                tiled.tile_boxes(image.size)
            except ValueError as exc:  # e.g. too small: an input error (2), not a failed authentication (1)
                raise core.InputError(str(exc)) from exc
            if args.command == "encode":
                neural_encode_file(image, message, passphrase, args.output, model, ecc=ecc)
            else:
                sys.stdout.buffer.write(neural_recover(image, passphrase, model, ecc=ecc))
            return 0
        profile = core.PROFILES[args.profile]
        if args.command == "encode":
            info = {}
            cover = core.load_cover(args.cover, info)
            if "colour_conversion" in info:
                print(f"ghostframe-png: converted colour profile {info['colour_conversion']}", file=sys.stderr)
            data = core.encode_message(cover, message, passphrase, profile, model)
            core.write_new(args.output, data)
        else:
            sys.stdout.buffer.write(core.decode_message(core.load_png(args.image), passphrase, profile, model))
        return 0
    except core.DecodeError as exc:
        print(f"ghostframe-png: {exc}", file=sys.stderr)
        return 1
    except core.CapacityError as exc:
        print(f"ghostframe-png: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:  # Legacy frames raise ValueError on authentication failure.
        legacy_auth = args.command == "decode" and args.profile in LEGACY and not isinstance(exc, core.InputError)
        print(f"ghostframe-png: {exc}", file=sys.stderr)
        return 1 if legacy_auth else 2
    except OSError as exc:
        print(f"ghostframe-png: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
