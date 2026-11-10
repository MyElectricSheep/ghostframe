"""Screen pretrained features, then test the best alternative on matched payloads."""
import hashlib
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np
from skimage.metrics import peak_signal_noise_ratio
import torch
from torch import nn
from torchvision.models import mobilenet_v3_small, resnet18

from experiments.crop_robustness import BUDGET, COVERS, HELD_OUT, STEPS, TRAIN, box
from ghostframe import DIM, decode, embedding, encode, load_checkpoint, load_model, projections, read_image, tensor, transforms

MOBILE = ("mobilenet_v3_small-047dcff4.pth", "047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f")
RESNET = ("resnet18-f37072fd.pth", "f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec")
OUTPUT = Path("benchmarks/encoder-screen")


def build(name):
    if name == "squeezenet":
        return load_model("cpu")
    if name == "mobilenet":
        model = mobilenet_v3_small()
        filename, digest = MOBILE
    else:
        model = resnet18()
        filename, digest = RESNET
    model.load_state_dict(load_checkpoint(f"https://download.pytorch.org/models/{filename}", digest))
    if name == "mobilenet":
        features = model.features
        features.embedding_dim = 576
    else:
        features = nn.Sequential(*list(model.children())[:-2])
    return features.eval().requires_grad_(False)


def screen(name, model, covers):
    dimension = getattr(model, "embedding_dim", DIM)
    carriers = torch.cat([projections(f"screen-{i}", 128, dimension=dimension) for i in range(32)])
    results = []
    with torch.inference_mode():
        for cover, image in covers.items():
            original = embedding(model, tensor(image, "cpu"))[0]
            clean = original @ carriers.T
            cases = {label: image.crop(box(image.size, spec)) for label, spec in HELD_OUT.items()}
            for label, crop in cases.items():
                changed = embedding(model, tensor(crop, "cpu"))[0]
                flipped = ((clean > 0) != (changed @ carriers.T > 0)).sum().item()
                results.append(dict(model=name, cover=cover, crop=label, flipped=flipped,
                                    probes=len(carriers), cosine=float(original @ changed)))
    return results


def embed_trial(model, cover, image, length, mode):
    key = "ghostframe-crop-eval-0"
    digest = hashlib.sha256(f"{cover}/{length}/0".encode()).digest()
    bits = "".join(f"{byte:08b}" for byte in digest)[:length]
    crops = [box(image.size, spec) for spec in TRAIN] if mode == "crop_aware" else ()
    start = perf_counter()
    marked = encode(image, bits, key, model, epsilon=BUDGET, steps=STEPS, crops=crops)
    elapsed = perf_counter() - start
    path = OUTPUT / f"{Path(cover).stem}-{length}-{mode}.png"
    marked.save(path)
    marked = read_image(path)
    cases = {"png": marked}
    cases.update({name: marked.crop(box(marked.size, spec)) for name, spec in HELD_OUT.items()})
    cases.update({name: value for name, value in transforms(marked) if name == "jpeg70_420"})
    recovered = {label: decode(case, key, length, model) for label, case in cases.items()}
    errors = {label: sum(a != b for a, b in zip(bits, result)) for label, result in recovered.items()}
    before, after = np.asarray(image), np.asarray(marked)
    max_delta = int(np.abs(after.astype(np.int16) - before).max())
    return dict(cover=cover, length=length, trial=0, key=key, mode=mode, target=bits,
                recovered=recovered, errors=errors, seconds=elapsed, file=path.name,
                max_delta=max_delta, psnr=float(peak_signal_noise_ratio(before, after)) if max_delta else None)


def save(name, value):
    path = OUTPUT / name
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    torch.set_num_threads(4)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    covers = {cover: read_image(Path("examples") / cover) for cover in COVERS}
    models = {name: build(name) for name in ("squeezenet", "mobilenet", "resnet18")}
    records = [row for name, model in models.items() for row in screen(name, model, covers)]
    rates = {name: mean(row["flipped"] / row["probes"] for row in records if row["model"] == name)
             for name in models}
    winner = min(("mobilenet", "resnet18"), key=rates.__getitem__)
    save("screen.json", dict(flip_rates=rates, selected=winner, records=records))
    print(rates, winner, flush=True)
    paired = []
    for cover, image in covers.items():
        for length in (16, 32):
            for mode in ("baseline", "crop_aware"):
                row = embed_trial(models[winner], cover, image, length, mode)
                paired.append(row)
                save("payloads.json", dict(model=winner, budget=BUDGET, records=paired))
                print(cover, length, mode, row["errors"], flush=True)


if __name__ == "__main__":
    main()
