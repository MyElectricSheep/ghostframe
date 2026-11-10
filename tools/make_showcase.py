"""Build and verify the showcase fixtures for the recommended experimental PNG profiles.

Every step runs the public CLI in a fresh process: encode, then decode at 1 and 4 threads,
then the negative controls (the unmarked cover and a wrong passphrase must both exit 1).
Writes the marked PNG, the cover PNG, an amplified difference image and fixtures-v2.json.

    python -m tools.make_showcase
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "embedding-showcase"
PASSPHRASE = b"ghostframe public benchmark fixture"
COVER = ROOT / "examples" / "grace_hopper.jpg"
AMPLIFY = 192  # difference image scale: amplification x cap = 192 for every fixture

FIXTURES = [
    dict(stem="png-l2-sentence", profile="sw-l2-c10x8b16p48", cap=2,
         message="Meet at dawn. The north gate stays open until six. Bring the blue notebook."),
    dict(stem="png-l8-paragraph", profile="sw-l8-c10x8b40p64", cap=8,
         message=("Meet at dawn by the north gate. This longer note was written into the photo by "
                  "changing each colour channel by at most eight levels, then read back by a frozen "
                  "SqueezeNet model from the saved PNG alone. Error correction repaired weak bits and "
                  "the passphrase check confirmed that nothing was altered.")),
]


def cli(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "ghostframe_png.cli", *map(str, args)],
                          input=stdin, capture_output=True, cwd=ROOT)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    from ghostframe_png.core import PROFILES, load_cover
    entries = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        good, bad = tmp / "pass.txt", tmp / "wrong.txt"
        good.write_bytes(PASSPHRASE)
        bad.write_bytes(PASSPHRASE + b"!")
        original = OUT / "grace-hopper-original.png"
        cover = load_cover(COVER)
        if not original.exists():
            Image.fromarray(cover).save(original)
        for fx in FIXTURES:
            message = fx["message"].encode()
            assert len(message) <= PROFILES[fx["profile"]].capacity, (fx["stem"], len(message))
            marked = OUT / f"{fx['stem']}.png"
            if not marked.exists():
                (tmp / "msg").write_bytes(message)
                run = cli("encode", COVER, marked, "--profile", fx["profile"],
                          "--message-file", tmp / "msg", "--passphrase-file", good)
                assert run.returncode == 0, run.stderr.decode()
            pixels = np.asarray(Image.open(marked).convert("RGB"), dtype=np.int16)
            delta = np.abs(pixels - cover.astype(np.int16))
            assert delta.max() <= fx["cap"], delta.max()
            diff = OUT / f"{fx['stem']}-difference.png"
            Image.fromarray(np.clip(delta * (AMPLIFY // fx["cap"]), 0, 255).astype(np.uint8)).save(diff)
            checks = {}
            for threads in (1, 4):
                run = cli("--threads", threads, "decode", marked, "--profile", fx["profile"],
                          "--passphrase-file", good)
                assert run.returncode == 0 and run.stdout == message, (threads, run.returncode, run.stderr)
                checks[f"decode_threads_{threads}"] = "exit 0, exact message"
            for label, image, passfile in (("unmarked_cover", original, good), ("wrong_passphrase", marked, bad)):
                run = cli("decode", image, "--profile", fx["profile"], "--passphrase-file", passfile)
                assert run.returncode == 1 and run.stdout == b"", (label, run.returncode)
                checks[label] = "exit 1, no output"
            entries.append(dict(
                carrier="ghostframe-png", profile=fx["profile"], status="recommended experimental",
                original=original.name, encoded=marked.name, difference=diff.name,
                amplification=AMPLIFY // fx["cap"], cap=fx["cap"], max_rgb_delta=int(delta.max()),
                changed_channel_fraction=round(float((delta > 0).mean()), 4),
                recovered_message=fx["message"], payload_bytes=len(message),
                profile_capacity=PROFILES[fx["profile"]].capacity, source="../../examples/grace_hopper.jpg",
                original_authenticates=False, checks=checks,
                sha256={p.name: sha256(p) for p in (original, marked, diff)}))
            print(fx["stem"], "verified", checks)
    (OUT / "fixtures-v2.json").write_text(json.dumps(entries, indent=2) + "\n")


if __name__ == "__main__":
    main()
