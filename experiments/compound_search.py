"""Benchmark the file decoder on crop, resize, and recompression."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from experiments.carrier_controls import source_image
from experiments.final_sweep import FRESH, jpeg, resize
from experiments.jpeg_capacity import MESSAGE, seal
from experiments.jpeg_carrier import OUT as JPEG_OUT, embed
from experiments.message_cli import recover_message
from experiments.tiled import PASSWORD
from ghostframe import read_image

OUT = Path("benchmarks/compound-search")


def trial(image, original_size, crop_size, soft):
    start = perf_counter()
    try:
        recovered = recover_message(image, PASSWORD, original_size=original_size,
                                    crop_size=crop_size, soft=soft)
    except ValueError:
        recovered = None
    return dict(authenticated=recovered == MESSAGE, seconds=perf_counter() - start)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = json.loads((JPEG_OUT / "results.json").read_text())
    names = [row["cover"] for row in rows if (row["spacing"], row["repetitions"]) == (3, 3)]
    results = []
    with TemporaryDirectory() as scratch:
        path = Path(scratch) / "received.jpg"
        for name in (*names, *FRESH):
            cover = source_image(name)
            marked = jpeg(embed(cover, seal(MESSAGE, PASSWORD), 3, 3), 95)
            width, height = cover.size
            box = (13, 21, width - 17, height - 9)
            cropped = marked.crop(box)
            cases = {}
            for label, source, scale in (("crop_resize75", cropped, 75),
                                         ("crop_resize67", cropped, 67),
                                         ("clean_control", cover.crop(box), 75)):
                resize(source, scale).save(path, format="JPEG", quality=70, subsampling=2)
                received = read_image(path)
                cases[label] = {mode: trial(received, cover.size, cropped.size, mode == "soft")
                                for mode in ("hard", "soft")}
            results.append(dict(cover=name, original_size=cover.size, crop_size=cropped.size, cases=cases))
            pending = OUT / "results.tmp"
            pending.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
            pending.replace(OUT / "results.json")
            print(name, {label: [x["authenticated"] for x in modes.values()]
                         for label, modes in cases.items()}, flush=True)


if __name__ == "__main__":
    main()
