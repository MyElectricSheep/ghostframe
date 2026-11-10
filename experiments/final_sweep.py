"""Fresh covers, resize diagnosis, confidence erasures, and detection controls."""
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from skimage import data

from experiments.alignment_search import grid_phases, search_crop
from experiments.jpeg_capacity import FRAME_BYTES, MESSAGE, PARITY_BYTES, seal, unseal
from experiments.jpeg_carrier import OUT as JPEG_OUT, embed, positions
from experiments.message_cli import recover_message
from experiments.robustness import COPIES, SPACING, detection_score, transcode
from experiments.tiled import PASSWORD

OUT = Path("benchmarks/final-sweep")
FRESH = ("coins", "clock", "colorwheel", "retina")


def resize(image, percent, method=Image.Resampling.LANCZOS):
    return image.resize(tuple(n*percent//100 for n in image.size), method)


def authenticated(received, erasures=()):
    try:
        return unseal(received, PASSWORD, erasures=erasures) == MESSAGE
    except ValueError:
        return False


def decode_oracle(image, size, target):
    restored = image.resize(size,Image.Resampling.LANCZOS) if image.size != size else image
    y,x = positions(size,COPIES,FRAME_BYTES*8)
    scores = grid_phases(restored)[y[:,0,0]//8,x[:,0,0]//8].reshape(COPIES,-1).sum(axis=0)
    received = np.packbits(scores<0).tobytes()
    ranks = np.argsort(np.abs(scores).reshape(-1,8).min(axis=1),kind="stable")
    hard = authenticated(received)
    successful_erasures = None
    if not hard:
        for count in (4,8,12,16,20,24):
            erased = ranks[:count].tolist()
            if authenticated(received,erased):
                successful_erasures = count
                break
    return dict(hard=hard, soft=hard or successful_erasures is not None,
                erasures_used=successful_erasures,
                byte_errors=sum(a!=b for a,b in zip(target,received,strict=True)))


def wide(image):
    start = perf_counter()
    try:
        valid = recover_message(image,PASSWORD,wide_resize=True)==MESSAGE
    except ValueError:
        valid = False
    return dict(authenticated=valid,seconds=perf_counter()-start)


def jpeg(image,quality):
    return transcode(image,"JPEG",quality=quality,subsampling=2)


def combine(marked, original_size):
    width,height=original_size
    crop=marked.crop((13,21,width-17,height-9))
    received=jpeg(resize(crop,75),70)
    restored=received.resize(crop.size,Image.Resampling.LANCZOS)
    return search_crop(restored,original_size,bits=FRAME_BYTES*8,
                       parity_bytes=PARITY_BYTES,verify=authenticated)["authenticated"]


def boundary_score(image):
    gray=np.asarray(image.convert("L"),dtype=np.float32)
    horizontal=np.abs(np.diff(gray,axis=1))
    vertical=np.abs(np.diff(gray,axis=0))
    edges=(horizontal[:,7::8].mean()+vertical[7::8,:].mean())/2
    return float(edges / max((horizontal.mean()+vertical.mean())/2,1e-6))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=json.loads((JPEG_OUT/"results.json").read_text())
    names=[r["cover"] for r in source if (r["spacing"],r["repetitions"])==(3,3)]
    rows=[]
    for name in (*names,*FRESH):
        original=Image.fromarray(getattr(data,name)()).convert("RGB")
        cover=ImageOps.contain(original,(512,512),Image.Resampling.LANCZOS)
        codeword=seal(MESSAGE,PASSWORD)
        marked=embed(cover,codeword,SPACING,COPIES)
        q95,q70=jpeg(marked,95),jpeg(marked,70)
        variants={
            "jpeg70": q70,
            "67_lanczos": jpeg(resize(q95,67),70),
            "73_lanczos": jpeg(resize(q95,73),70),
            "73_from_jpeg70": jpeg(resize(q70,73),70),
            "73_bilinear": jpeg(resize(q95,73,Image.Resampling.BILINEAR),70),
            "73_bicubic": jpeg(resize(q95,73,Image.Resampling.BICUBIC),70),
            "73_box": jpeg(resize(q95,73,Image.Resampling.BOX),70),
            "brightness": ImageEnhance.Brightness(q95).enhance(1.05),
        }
        cases={label:decode_oracle(view,marked.size,codeword) for label,view in variants.items()}
        for label in ("67_lanczos","73_lanczos","73_from_jpeg70"):
            cases[label]["wide"]=wide(variants[label])
        cases["crop_resize_jpeg_oracle"]=dict(authenticated=combine(q95,marked.size))
        clean_jpeg=jpeg(cover,70)
        detection={
            "png_protocol":[detection_score(cover),detection_score(marked)],
            "jpeg_protocol":[detection_score(clean_jpeg),detection_score(q70)],
            "png_edges":[boundary_score(cover),boundary_score(marked)],
            "jpeg_edges":[boundary_score(clean_jpeg),boundary_score(q70)],
        }
        row=dict(cover=name,fresh=name in FRESH,dimensions=marked.size,cases=cases,detection=detection)
        rows.append(row)
        temp=OUT/"results.tmp"
        temp.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")
        temp.replace(OUT/"results.json")
        print(name,{k:(v.get("hard"),v.get("soft"),v.get("wide",{}).get("authenticated")) for k,v in cases.items()},flush=True)


if __name__=="__main__":
    main()
