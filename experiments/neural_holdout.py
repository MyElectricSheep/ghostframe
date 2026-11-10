"""Check the original embedding idea on fresh covers alongside the luminance work."""
import hashlib
import json

import torch

from experiments.carrier_controls import source_image
from experiments.extended import run_trial
from experiments.final_sweep import FRESH, OUT
from ghostframe import load_model


def main():
    torch.set_num_threads(4)
    OUT.mkdir(parents=True, exist_ok=True)
    model=load_model("cpu")
    rows=[]
    for name in FRESH:
        image=source_image(name)
        for length in (16,32):
            digest=hashlib.sha256(f"neural-holdout/{name}/{length}".encode()).digest()
            target="".join(f"{byte:08b}" for byte in digest)[:length]
            for epsilon in (2,8):
                row=run_trial(model,image,name,target,"neural-holdout",epsilon,"baseline","squeezenet")
                rows.append(row)
        print(name,flush=True)
    (OUT/"neural-holdout.json").write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
