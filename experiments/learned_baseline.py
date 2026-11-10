"""Optional pretrained TrustMark comparator on the neural holdout covers."""
import hashlib
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import torch

from experiments.carrier_controls import source_image
from experiments.extended import FRESH_CROPS
from experiments.crop_robustness import box
from ghostframe import transforms

OUT = Path("benchmarks/goal-validation")


def main():
    import trustmark
    from trustmark import TrustMark

    torch.set_num_threads(4)
    model = TrustMark(model_type="C", device="cpu", loadRemover=False, verbose=False)
    expected = {
        "trustmark_C.yaml": "cf38887be05093c23c874ba999d38a70e1fbd2c67b18d388a64bc6446be661d2",
        "decoder_C.ckpt": "ede8305d71b569a3a1c11cf51a76a7729a7ec2bc00e74b9a5d617458763b3a42",
        "encoder_C.ckpt": "2eeeaf02178976f04d0996280466a22e53418fee8d7c063990b1a039aec0a50b",
    }
    for name, digest in expected.items():
        path = Path(trustmark.__file__).parent / "models" / name
        with path.open("rb") as asset:
            if hashlib.file_digest(asset, "sha256").hexdigest() != digest:
                raise RuntimeError(f"Unexpected TrustMark asset checksum: {name}")
    baseline = json.loads(Path("benchmarks/final-sweep/neural-holdout.json").read_text())
    records = []
    for trial in baseline:
        if trial["epsilon"] != 2:
            continue
        target = trial["target"]
        cover = source_image(trial["cover"])
        clean = np.asarray(cover, dtype=np.int16)
        padded = target.ljust(model.schemaCapacity(), "0")
        started = perf_counter()
        marked = model.encode(cover, padded, MODE="binary")
        seconds = perf_counter() - started
        residual = np.asarray(marked, dtype=np.int16) - clean
        for limit in (2, 8, None):
            delta = np.clip(residual, -limit, limit) if limit is not None else residual
            modified = (clean + delta).astype(np.uint8)
            with io.BytesIO() as buffer:
                Image.fromarray(modified).save(buffer, format="PNG")
                buffer.seek(0)
                with Image.open(buffer) as decoded:
                    image = decoded.convert("RGB")
            cases = {"png": image, **{label: image.crop(box(image.size, spec))
                                     for label, spec in FRESH_CROPS.items()}}
            cases.update({label: view for label, view in transforms(image) if label == "jpeg70_420"})
            outcomes = {}
            for label, view in cases.items():
                start = perf_counter()
                decoded, detected, _ = model.decode(view, MODE="binary")
                outcomes[label] = dict(exact=bool(detected and decoded[:len(target)] == target),
                                       detected=bool(detected), seconds=perf_counter() - start)
            records.append(dict(cover=trial["cover"], length=len(target), limit=limit,
                                max_delta=int(np.abs(delta).max()), mean_delta=float(np.abs(delta).mean()),
                                psnr=float(peak_signal_noise_ratio(clean.astype(np.uint8), modified)),
                                ssim=float(structural_similarity(clean.astype(np.uint8), modified, channel_axis=-1)),
                                seconds=seconds, cases=outcomes))
        print(trial["cover"], len(target), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "trustmark-checkpoints.json").write_text(json.dumps(expected, indent=2) + "\n")
    (OUT / "trustmark.json").write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
