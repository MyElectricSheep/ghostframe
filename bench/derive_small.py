"""Post-hoc exploratory split: the holdout covers downscaled to 640 pixels wide.

Added after the preregistered holdout run, to test whether the 1280-pixel holdout covers are
easier than the 300-640-pixel screening covers. It is labelled exploratory everywhere; no
profile is selected or changed on it.

    python -m bench.derive_small   # writes data/covers/holdout640/ and bench/manifest-holdout640-v1.json
"""
import hashlib
import json

from PIL import Image

from bench.run import ROOT, covers
from ghostframe_png.core import load_cover

WIDTH = 640


def main():
    out_dir = ROOT / "data" / "covers" / "holdout640"
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for entry, path in covers("holdout"):
        image = Image.fromarray(load_cover(path))
        height = round(image.height * WIDTH / image.width)
        target = out_dir / f"{entry['id']}.png"
        image.resize((WIDTH, height), Image.Resampling.LANCZOS).save(target)
        entries.append(dict(id=entry["id"], split="holdout640", file=f"holdout640/{entry['id']}.png",
                            derived_from=entry["sha256"], transform=f"load_cover, LANCZOS to {WIDTH} px wide",
                            sha256=hashlib.sha256(target.read_bytes()).hexdigest(), size=[WIDTH, height]))
    manifest = dict(version=1, covers_dir="data/covers", exploratory=True, covers=entries)
    (ROOT / "bench" / "manifest-holdout640-v1.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(len(entries), "covers")


if __name__ == "__main__":
    main()
