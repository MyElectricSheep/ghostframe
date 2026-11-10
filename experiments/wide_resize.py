"""Compare default and wider resize recovery for the 96-byte profile."""
import json
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageOps
from skimage import data

from experiments.jpeg_capacity import MESSAGE, seal
from experiments.jpeg_carrier import OUT as JPEG_OUT, embed
from experiments.message_cli import recover_message
from experiments.robustness import COPIES, SPACING, transcode
from experiments.tiled import PASSWORD

OUT = Path("benchmarks/wide-resize")
EDITS = (("67pct_floor", 67, False), ("73pct_floor", 73, False),
         ("87pct_nearest", 87, True), ("49pct_unlisted", 49, False))


def run(image, wide):
    start = perf_counter()
    try:
        decoded = recover_message(image, PASSWORD, try_resize=True, wide_resize=wide)
    except ValueError:
        decoded = None
    return dict(authenticated=decoded == MESSAGE, seconds=perf_counter()-start)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    covers = json.loads((JPEG_OUT/"results.json").read_text())
    records = []
    for row in covers:
        if (row["spacing"], row["repetitions"]) != (SPACING, COPIES):
            continue
        name = row["cover"]
        original = Image.fromarray(getattr(data, name)()).convert("RGB")
        cover = ImageOps.contain(original, (512, 512), Image.Resampling.LANCZOS)
        marked = embed(cover, seal(MESSAGE, PASSWORD), SPACING, COPIES)
        marked = transcode(marked, "JPEG", quality=95, subsampling=2)
        cases = {}
        for label, percent, nearest in EDITS:
            size = tuple(round(dimension * percent / 100) if nearest else dimension * percent // 100
                         for dimension in cover.size)
            resized = marked.resize(size, Image.Resampling.LANCZOS)
            received = transcode(resized, "JPEG", quality=70, subsampling=2)
            cases[label] = dict(default=run(received, False), wide=run(received, True))
        control = transcode(cover.resize((cover.width*73//100, cover.height*73//100),
                                         Image.Resampling.LANCZOS), "JPEG", quality=70, subsampling=2)
        cases["clean_73pct"] = dict(default=run(control, False), wide=run(control, True))
        records.append(dict(cover=name, cases=cases))
        pending = OUT/"results.tmp"
        pending.write_text(json.dumps(records, indent=2, allow_nan=False)+"\n")
        pending.replace(OUT/"results.json")
        print(name, {k:v["wide"]["authenticated"] for k,v in cases.items()}, flush=True)


if __name__ == "__main__":
    main()
