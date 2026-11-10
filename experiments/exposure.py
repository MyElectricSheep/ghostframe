"""Bounded exposure recovery for the 96-byte luminance profile."""
import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from skimage import data

from experiments.alignment_search import search_exposure
from experiments.final_sweep import FRESH, authenticated, jpeg
from experiments.jpeg_capacity import FRAME_BYTES, MESSAGE, PARITY_BYTES, seal
from experiments.jpeg_carrier import OUT as JPEG_OUT, embed
from experiments.message_cli import recover_message
from experiments.tiled import PASSWORD

OUT = Path("benchmarks/final-sweep")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=json.loads((JPEG_OUT/"results.json").read_text())
    names=[r["cover"] for r in source if (r["spacing"],r["repetitions"])==(3,3)]
    rows=[]
    for name in (*names,*FRESH):
        original=Image.fromarray(getattr(data,name)()).convert("RGB")
        cover=ImageOps.contain(original,(512,512),Image.Resampling.LANCZOS)
        marked=jpeg(embed(cover,seal(MESSAGE,PASSWORD),3,3),95)
        cases={}
        variants={
            "bright_105":ImageEnhance.Brightness(marked).enhance(1.05),
            "dark_93":ImageEnhance.Brightness(marked).enhance(.93),
            "bright_105_jpeg70":jpeg(ImageEnhance.Brightness(marked).enhance(1.05),70),
            "dark_93_jpeg70":jpeg(ImageEnhance.Brightness(marked).enhance(.93),70),
            "clean_bright_105":ImageEnhance.Brightness(cover).enhance(1.05),
        }
        for label, view in variants.items():
            try:
                baseline=recover_message(view,PASSWORD)==MESSAGE
            except ValueError:
                baseline=False
            cases[label]=dict(direct=baseline,search=search_exposure(view, bits=FRAME_BYTES*8,
                                                               parity_bytes=PARITY_BYTES, verify=authenticated))
        rows.append(dict(cover=name,cases=cases))
        temp=OUT/"exposure.tmp"
        temp.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")
        temp.replace(OUT/"exposure.json")
        print(name,{label:v["search"]["authenticated"] for label,v in cases.items()},flush=True)


if __name__=="__main__":
    main()
