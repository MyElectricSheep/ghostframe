"""Matched speed reference and neural cover-selection control."""
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageOps
from skimage import data
import torch

from experiments.alignment_search import block_phases, grid_phases
from experiments.final_sweep import FRESH, jpeg, resize, wide
from experiments.jpeg_capacity import MESSAGE, seal
from experiments.jpeg_carrier import OUT as JPEG_OUT, block_order, embed
from experiments.tiled import PASSWORD
from ghostframe import decode, load_model

OUT = Path("benchmarks/final-sweep")


def source_image(name):
    return ImageOps.contain(Image.fromarray(getattr(data,name)()).convert("RGB"),
                            (512,512),Image.Resampling.LANCZOS)


def speed():
    records=[]
    for name in ("camera","coffee","rocket"):
        cover=source_image(name)
        marked=embed(cover,seal(MESSAGE,PASSWORD),3,3)
        received=jpeg(resize(jpeg(marked,95),73),70)
        phases=block_phases(cover)[::8,::8]
        np.testing.assert_allclose(phases,grid_phases(cover),atol=1e-8)
        block_order.cache_clear()
        with patch("experiments.alignment_search.grid_phases",
                   side_effect=lambda image: block_phases(image)[::8,::8]):
            reference=wide(received)
        block_order.cache_clear()
        optimized=wide(received)
        records.append(dict(cover=name,reference=reference,optimized=optimized))
    return records


def cover_selection():
    torch.set_num_threads(4)
    model=load_model("cpu")
    names=[r["cover"] for r in json.loads((JPEG_OUT/"results.json").read_text())
           if (r["spacing"],r["repetitions"])==(3,3)]
    rows=[]
    for name in (*names,*FRESH):
        image=source_image(name)
        for trial in range(8):
            key=f"cover-selection-control-{trial}"
            clean=decode(image,key,16,model)
            changed=decode(jpeg(image,70),key,16,model)
            rows.append(dict(cover=name,trial=trial,clean=clean,jpeg70=changed))
    return rows


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name, function in (("speed",speed),("cover-selection",cover_selection)):
        rows=function()
        (OUT/f"{name}.json").write_text(json.dumps(rows,indent=2)+"\n")
        print(name,len(rows),flush=True)


if __name__=="__main__":
    main()
