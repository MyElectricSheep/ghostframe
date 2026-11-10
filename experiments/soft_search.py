"""Matched hard and confidence-assisted CLI search benchmark."""
import json
from pathlib import Path
from time import perf_counter

from PIL import Image

from experiments.carrier_controls import source_image
from experiments.final_sweep import jpeg, resize
from experiments.jpeg_capacity import MESSAGE, seal
from experiments.jpeg_carrier import embed
from experiments.message_cli import recover_message
from experiments.tiled import PASSWORD

OUT = Path("benchmarks/soft-search")
COVERS = ("grass", "astronaut", "coffee", "coins", "colorwheel", "retina")


def trial(image, soft, **options):
    start = perf_counter()
    try:
        success = recover_message(image, PASSWORD, soft=soft, **options) == MESSAGE
    except ValueError:
        success = False
    return dict(authenticated=success, seconds=perf_counter()-start)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for cover in COVERS:
        clean = source_image(cover)
        marked = embed(clean, seal(MESSAGE, PASSWORD), 3, 3)
        q95, q70 = jpeg(marked,95), jpeg(marked,70)
        cases = {}
        for label, image, options in (
            ("67_resize", jpeg(resize(q95,67),70), {"wide_resize":True}),
            ("73_resize_from_jpeg70", jpeg(resize(q70,73),70), {"wide_resize":True}),
            ("73_box_known_size", jpeg(resize(q95,73,Image.Resampling.BOX),70)
             .resize(clean.size,Image.Resampling.LANCZOS), {}),
            ("clean_control", jpeg(clean,70), {}),
        ):
            cases[label] = {mode:trial(image,mode=="soft",**options) for mode in ("hard","soft")}
        records.append(dict(cover=cover,cases=cases))
        pending = OUT/"results.tmp"
        pending.write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
        pending.replace(OUT/"results.json")
        print(cover,{k:(v["hard"]["authenticated"],v["soft"]["authenticated"]) for k,v in cases.items()},flush=True)


if __name__=="__main__":
    main()
