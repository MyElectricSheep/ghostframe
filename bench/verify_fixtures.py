"""Check the published demo fixtures with the public CLI, each decode in a fresh process.

    python -m bench.verify_fixtures            # hashes, exact message, unmarked cover refused
    python -m bench.verify_fixtures --full     # also a wrong passphrase must be refused

Needs the tiled extra (`pip install -e '.[tiled]'`). Exits 1 if any check fails.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "demo-photos" / "fixtures"
PASSPHRASE = b"ghostframe public benchmark fixture"


def decode(png, profile, passphrase_file):
    started = time.perf_counter()
    run = subprocess.run([sys.executable, "-m", "ghostframe_png.cli", "decode", str(png), "--profile", profile,
                          "--passphrase-file", str(passphrase_file)], capture_output=True, cwd=ROOT)
    return run.returncode, run.stdout, time.perf_counter() - started


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true", help="also check that a wrong passphrase is refused")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        good, wrong = Path(tmp) / "pass.txt", Path(tmp) / "wrong.txt"
        good.write_bytes(PASSPHRASE)
        wrong.write_bytes(b"not the fixture passphrase")
        failures = 0
        print(f"{'fixture':<44} {'bytes':>5}  {'hashes':<6} {'message':<7} {'cover':<7} {'wrong':<7} {'time':>6}")
        for manifest in sorted(FIXTURES.glob("*/fixtures.json")):
            folder = manifest.parent
            for entry in json.loads(manifest.read_text()):
                hashes = all(hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
                             for name, digest in entry["sha256"].items())
                code, out, seconds = decode(folder / entry["encoded"], entry["profile"], good)
                message = code == 0 and out == entry["recovered_message"].encode()
                code, out, _ = decode(folder / entry["original"], entry["profile"], good)
                cover = code == 1 and out == b""
                refused = None
                if args.full:
                    code, out, _ = decode(folder / entry["encoded"], entry["profile"], wrong)
                    refused = code == 1 and out == b""
                checks = [hashes, message, cover] + ([refused] if args.full else [])
                failures += not all(checks)
                mark = lambda ok: "-" if ok is None else ("ok" if ok else "FAIL")
                print(f"{folder.name + '/' + entry['encoded']:<44} {entry['payload_bytes']:>5}  {mark(hashes):<6} "
                      f"{mark(message):<7} {mark(cover):<7} {mark(refused):<7} {seconds:>5.1f}s", flush=True)
    print("all checks passed" if not failures else f"{failures} fixture(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
