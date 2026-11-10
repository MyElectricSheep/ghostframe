"""Measure the JPEG carrier with a larger authenticated frame."""
import json

import numpy as np
from PIL import Image, ImageOps
from skimage import data
from skimage.metrics import peak_signal_noise_ratio

from experiments.jpeg_carrier import OUT as JPEG_OUT, embed, extract
from experiments.robustness import OUT, transcode
from experiments.frame_keys import PASSWORD, derive
from experiments.jpeg_frame import AAD, FRAME_BYTES, MESSAGE, MESSAGE_BYTES, PARITY_BYTES, VERSION, seal, unseal

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    covers = json.loads((JPEG_OUT/"results.json").read_text())
    records = []
    for row in covers:
        if (row["spacing"],row["repetitions"]) != (3,3):
            continue
        name = row["cover"]
        original = Image.fromarray(getattr(data,name)()).convert("RGB")
        image = ImageOps.contain(original,(512,512),Image.Resampling.LANCZOS)
        codeword = seal(MESSAGE,PASSWORD)
        try:
            marked = embed(image,codeword,3,3)
        except ValueError:
            records.append(dict(cover=name,dimensions=image.size,eligible=False))
            continue
        before,after = np.asarray(image),np.asarray(marked)
        delta = int(np.abs(after.astype(np.int16)-before).max())
        assert delta <= 2
        cases = {}
        for label, view in [
            ("png",transcode(marked,"PNG")),
            ("jpeg70",transcode(marked,"JPEG",quality=70,subsampling=2)),
            ("jpeg50",transcode(marked,"JPEG",quality=50,subsampling=2)),
        ]:
            received = extract(view,3,3,FRAME_BYTES)
            try:
                recovered = unseal(received,PASSWORD)
            except ValueError:
                recovered = None
            cases[label] = dict(authenticated=recovered==MESSAGE,
                                byte_errors=sum(a!=b for a,b in zip(codeword,received,strict=True)))
        records.append(dict(cover=name, dimensions=image.size, eligible=True,
                            psnr=float(peak_signal_noise_ratio(before,after)),
                            max_delta=delta,cases=cases))
        print(name,cases,flush=True)
    (OUT/"capacity.json").write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
