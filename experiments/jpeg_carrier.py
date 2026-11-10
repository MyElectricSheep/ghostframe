"""Compare an aligned luminance carrier with the tiled embedding benchmark."""
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps
from reedsolo import RSCodec
from skimage import data
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from experiments.luminance import BLOCK, EPSILON, block_order, embed, extract, luminance, positions
from experiments.tiled import FRAME_BYTES, PASSWORD
from experiments.tiled_ecc import (
    COVERS, MESSAGE, PARITY_BYTES, OUT as ECC_OUT, decode_frame, seal,
)
from ghostframe import transforms

OUT = Path("benchmarks/jpeg-carrier")
BITS = FRAME_BYTES * 8
FRESH = ("rocket", "chelsea", "gravel", "moon")
SETTINGS = ((2, 1), (2, 3), (3, 3))


def evaluate(image, codeword, spacing, repetitions):
    try:
        received = extract(image, spacing, repetitions)
    except ValueError:
        return dict(decodable=False, raw=False, corrected=False)
    result = dict(decodable=True, received=received.hex(),
                  byte_errors=sum(a != b for a, b in zip(codeword, received)),
                  bit_errors=sum((a ^ b).bit_count() for a, b in zip(codeword, received)))
    for correct, label in ((False, "raw"), (True, "corrected")):
        try:
            message, _ = decode_frame(received, PASSWORD, correct=correct)
            result[label] = message == MESSAGE
        except ValueError:
            result[label] = False
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    control = {r["cover"]: r for r in json.loads((ECC_OUT/"results.json").read_text())}
    results = []
    for name in (*COVERS, *FRESH):
        original = Image.fromarray(getattr(data, name)()).convert("RGB")
        image = ImageOps.contain(original, (512, 512), Image.Resampling.LANCZOS)
        codeword = (bytes.fromhex(control[name]["codeword"]) if name in control
                    else bytes(RSCodec(PARITY_BYTES).encode(seal(MESSAGE, PASSWORD))))
        for spacing, repetitions in SETTINGS:
            start = perf_counter()
            marked = embed(image, codeword, spacing, repetitions)
            seconds = perf_counter() - start
            with io.BytesIO() as buffer:
                marked.save(buffer, format="PNG")
                buffer.seek(0)
                with Image.open(buffer) as png:
                    reopened = png.convert("RGB")
            before, after = np.asarray(image), np.asarray(reopened)
            delta = int(np.abs(before.astype(np.int16) - after).max())
            assert delta <= EPSILON
            cases = {label: evaluate(view, codeword, spacing, repetitions)
                     for label, view in [("png", reopened), *transforms(reopened)]}
            row = dict(cover=name, spacing=spacing, repetitions=repetitions,
                       dimensions=image.size, codeword=codeword.hex(),
                       seconds=seconds, max_delta=delta,
                       psnr=float(peak_signal_noise_ratio(before, after)),
                       ssim=float(structural_similarity(before, after, channel_axis=-1)),
                       cases=cases)
            results.append(row)
            if spacing == 2 and repetitions == 3:
                reopened.save(OUT/f"{name}.png")
            pending = OUT/"results.tmp"
            pending.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
            pending.replace(OUT/"results.json")
            print(name,spacing,repetitions,{k:v.get("byte_errors") for k,v in cases.items()},flush=True)


if __name__ == "__main__":
    main()
