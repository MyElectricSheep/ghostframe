"""Build and verify the showcase fixtures for the recommended experimental PNG profiles.

Every step runs the public CLI in a fresh process: encode, then decode at 1 and 4 threads,
then the negative controls (the unmarked cover and a wrong passphrase must both exit 1).
Writes the marked PNG, the cover PNG, an amplified difference image and fixtures-v2.json.

    python -m tools.make_showcase           # benchmarks/embedding-showcase (Grace Hopper)
    python -m tools.make_showcase --demo    # demo-photos/fixtures (three demo covers x three modes)
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


# Demo-site fixtures: three held-out covers, one message per mode each.
DEMO_OUT = ROOT / "demo-photos" / "fixtures"
DEMO = {
    "coffee-beans": [
        dict(stem="classic", profile="legacy-v1", cap=8, message="Beans at six."),
        dict(stem="subtle", profile="sw-l2-c10x8b16p48", cap=2,
             message="The roaster on Via Lucca is ours. Order the dark blend and pay in cash."),
        dict(stem="long", profile="sw-l8-c10x8b40p64", cap=8,
             message=("Courier, your contact runs the coffee stall by the east gate of the market. "
                      "Order a double roast, no sugar, and leave a folded newspaper on the counter. "
                      "If she asks about the rain in Vienna, say it stopped on Tuesday. She will pass "
                      "you a paper bag. Do not open it until you are across the river.")),
    ],
    "milky-way": [
        dict(stem="classic", profile="legacy-v1", cap=8, message="Eyes on Orion"),
        dict(stem="subtle", profile="sw-l2-c10x8b16p48", cap=2,
             message="Signal from the fence line at 02:00. Two flashes mean the road is clear."),
        dict(stem="long", profile="sw-l8-c10x8b40p64", cap=8,
             message=("Night team: the drop is at the last fence post on the ridge, under the flat "
                      "stone. Arrive after moonset and use no torches. If the sky is clear, wait for "
                      "the satellite to pass overhead, then move. If you see headlights on the "
                      "road, abort and return at the same hour tomorrow. Burn this after reading.")),
    ],
    "antonello-portrait-of-a-man": [
        dict(stem="classic", profile="legacy-v1", cap=8, message="Trust no one."),
        dict(stem="subtle", profile="sw-l2-c10x8b16p48", cap=2,
             message="The man in the red cap knows the code. Meet him in Room 4 at closing time."),
        dict(stem="long", profile="sw-l8-c10x8b40p64", cap=8,
             message=("Agent, the portrait is the key. The gallery guard on the night shift is one of "
                      "ours; tell him you admire the red cap and he will let you stay past closing. "
                      "Behind the frame you will find a list of names. Photograph it, put everything "
                      "back exactly as it was, and leave by the river door before midnight.")),
    ],
}


def build(cover_path, fixtures, out_dir, original, manifest, source):
    from ghostframe_png.cli import LEGACY
    from ghostframe_png.core import PROFILES, load_cover
    capacity = lambda name: LEGACY[name]["capacity"] if name in LEGACY else PROFILES[name].capacity
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        good, bad = tmp / "pass.txt", tmp / "wrong.txt"
        good.write_bytes(PASSPHRASE)
        bad.write_bytes(PASSPHRASE + b"!")
        cover = load_cover(cover_path)
        if not original.exists():
            Image.fromarray(cover).save(original)
        for fx in fixtures:
            message = fx["message"].encode()
            assert len(message) <= capacity(fx["profile"]), (fx["stem"], len(message))
            marked = out_dir / f"{fx['stem']}.png"
            if not marked.exists():
                (tmp / "msg").write_bytes(message)
                run = cli("encode", cover_path, marked, "--profile", fx["profile"],
                          "--message-file", tmp / "msg", "--passphrase-file", good)
                assert run.returncode == 0, run.stderr.decode()
            pixels = np.asarray(Image.open(marked).convert("RGB"), dtype=np.int16)
            delta = np.abs(pixels - cover.astype(np.int16))
            assert delta.max() <= fx["cap"], delta.max()
            diff = out_dir / f"{fx['stem']}-difference.png"
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
            legacy = fx["profile"].startswith("legacy")
            entries.append(dict(
                carrier="ghostframe-png", profile=fx["profile"],
                status="legacy default" if legacy else "recommended experimental",
                original=original.name, encoded=marked.name, difference=diff.name,
                amplification=AMPLIFY // fx["cap"], cap=fx["cap"], max_rgb_delta=int(delta.max()),
                changed_channel_fraction=round(float((delta > 0).mean()), 4),
                recovered_message=fx["message"], payload_bytes=len(message),
                profile_capacity=capacity(fx["profile"]), source=source,
                original_authenticates=False, checks=checks,
                sha256={p.name: sha256(p) for p in (original, marked, diff)}))
            print(out_dir.name, fx["stem"], "verified", checks, flush=True)
    manifest.write_text(json.dumps(entries, indent=2) + "\n")


def main():
    if sys.argv[1:] == ["--demo"]:
        for name, fixtures in DEMO.items():
            out_dir = DEMO_OUT / name
            build(ROOT / "demo-photos" / f"{name}.jpg", fixtures, out_dir, out_dir / "original.png",
                  out_dir / "fixtures.json", f"../../{name}.jpg")
    else:
        build(COVER, FIXTURES, OUT, OUT / "grace-hopper-original.png", OUT / "fixtures-v2.json",
              "../../examples/grace_hopper.jpg")


if __name__ == "__main__":
    main()
