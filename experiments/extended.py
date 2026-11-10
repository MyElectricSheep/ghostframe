"""Embedded margins, independent covers, capacity, and repetition-code pilot."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps
from skimage import data
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import torch

from experiments.crop_robustness import box, HELD_OUT, TRAIN
from experiments.encoder_screen import build
from ghostframe import DIM, encode, pixels, projections, read_image, scores, tensor, transforms

OUT = Path("benchmarks/extended")
FRESH = ("astronaut", "coffee", "rocket", "chelsea")
FRESH_CROPS = {"center91": (.91,.5,.5), "offset89": (.89,.17,.63), "offset93": (.93,.78,.27)}


def save(path, value):
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    pending.replace(path)


def target_for(label, length):
    return "".join(f"{byte:08b}" for byte in hashlib.shake_256(label.encode()).digest((length+7)//8))[:length]


def measure(model, image, key, target, carriers=None):
    if carriers is None:
        carriers = projections(key, len(target), dimension=getattr(model, "embedding_dim", DIM))
    with torch.inference_mode():
        values = scores(model, tensor(image, "cpu"), carriers)[0].tolist()
    recovered = "".join("1" if value > 0 else "0" for value in values)
    margins = [value if bit == "1" else -value for bit, value in zip(target, values)]
    return dict(recovered=recovered, margins=margins, errors=sum(a != b for a,b in zip(target,recovered)))


def fresh_covers():
    return {name: Image.fromarray(getattr(data, name)()).convert("RGB") for name in FRESH}


def run_trial(model, image, name, bits, key, epsilon, mode, label, *, carriers=None, extra_views=(), delta_stride=1):
    coords = [box(image.size, spec) for spec in TRAIN] if mode == "crop_aware" else ()
    started = perf_counter()
    marked = encode(image, bits, key, model, epsilon=epsilon, crops=coords,
                    carriers=carriers, extra_views=extra_views, delta_stride=delta_stride)
    seconds = perf_counter() - started
    # Round-trip through an actual PNG, keeping this sweep compact.
    with io.BytesIO() as buffer:
        marked.save(buffer, format="PNG")
        buffer.seek(0)
        with Image.open(buffer) as png:
            marked = png.convert("RGB")
    crops = {k: marked.crop(box(marked.size, spec)) for k,spec in FRESH_CROPS.items()}
    channel = dict(transforms(marked))
    # Synthetic thumbnail/re-encode pipeline, without any platform-specific claim.
    thumbnail = ImageOps.contain(marked, (320, 320), Image.Resampling.LANCZOS)
    channel["thumbnail_jpeg85"] = dict(transforms(thumbnail))["jpeg85_420"]
    cases = {"png": marked, **crops, **channel}
    original, marked_pixels = np.asarray(image), np.asarray(marked)
    delta = int(np.abs(marked_pixels.astype(np.int16)-original).max())
    assert delta <= epsilon
    return dict(cover=name, target=bits, key=key, epsilon=epsilon, mode=mode, label=label,
                seconds=seconds, max_delta=delta,
                psnr=float(peak_signal_noise_ratio(original, marked_pixels)) if delta else None,
                ssim=float(structural_similarity(original, marked_pixels, channel_axis=-1)),
                cases={k:measure(model, view, key, bits, carriers) for k,view in cases.items()})


def historical(models):
    runs = []
    locations = (("squeezenet", "crop-robustness", "results.json"), ("resnet18", "encoder-screen", "payloads.json"))
    for name, folder, filename in locations:
        root = Path("benchmarks") / folder
        for row in json.loads((root/filename).read_text())["records"]:
            if row["trial"] != 0:
                continue
            marked = read_image(root / row["file"])
            cases = {"png":marked, **{label:marked.crop(box(marked.size,spec)) for label,spec in HELD_OUT.items()}}
            readings = {label:measure(models[name], view, row["key"], row["target"]) for label,view in cases.items()}
            for label, result in readings.items():
                recorded = row["recovered"][label]
                if isinstance(recorded, dict):
                    recorded = recorded["bits"]
                assert result["recovered"] == recorded, (row["file"],label)
            runs.append(dict(model=name, cover=row["cover"], mode=row.get("method",row.get("mode")),
                             target=row["target"], cases=readings))
    save(OUT/"historical-margins.json", runs)


def validate(models):
    results = []
    for name, image in fresh_covers().items():
        for length in (16,32):
            for model_name, model in models.items():
                for mode in ("baseline", "crop_aware") if length == 16 else ("baseline",):
                    bits = target_for(f"validation/{name}/{length}",length)
                    row = run_trial(model,image,name,bits,"fresh-key-v1",2,mode,model_name)
                    results.append(row)
                    save(OUT/"fresh-validation.json",results)
                    print("fresh",name,length,model_name,mode,flush=True)


def capacity(model):
    results = []
    for name,image in fresh_covers().items():
        for epsilon in (2,8):
            for length in (16,32,64,128,256,384,512):
                bits = target_for(f"capacity/{name}/{length}",length)
                results.append(run_trial(model,image,name,bits,"capacity-key-v1",epsilon,"baseline","raw"))
                save(OUT/"capacity.json",results)
                print("capacity",name,epsilon,length,flush=True)
            bits = target_for(f"capacity/{name}/32",32)
            row = run_trial(model,image,name,bits*3,"capacity-key-v1",epsilon,"baseline","repeat3")
            for condition in row["cases"].values():
                received = condition["recovered"]
                corrected = "".join("1" if sum(received[i+j*32]=="1" for j in range(3))>=2 else "0"
                                    for i in range(32))
                condition["message_errors"] = sum(a!=b for a,b in zip(bits,corrected))
            results.append(row)
            save(OUT/"capacity.json",results)


def jpeg80_view(image):
    with io.BytesIO() as buffer:
        pixels(image).save(buffer, format="JPEG", quality=80, subsampling=2)
        buffer.seek(0)
        with Image.open(buffer) as jpeg:
            compressed = tensor(jpeg.convert("RGB"), image.device)
    # Forward through real JPEG, approximate its backward pass with identity.
    return compressed + (image - image.detach())


def alternatives(model):
    results = []
    key = "capacity-key-v1"
    for name, image in fresh_covers().items():
        for length in (32, 128, 384):
            bits = target_for(f"capacity/{name}/{length}", length)
            q, r = torch.linalg.qr(projections(key, length).T)
            # Fix QR sign ambiguity so the keyed directions are reproducible.
            directions = (q * r.diagonal().sign()).T.contiguous()
            row = run_trial(model, image, name, bits, key, 2, "baseline", "orthogonal", carriers=directions)
            results.append(row)
            save(OUT/"alternatives.json", results)
        for length in (16, 32):
            bits = target_for(f"capacity/{name}/{length}", length)
            row = run_trial(model, image, name, bits, key, 2, "baseline", "jpeg_aware", extra_views=(jpeg80_view,))
            results.append(row)
            save(OUT/"alternatives.json", results)
        print("alternatives", name, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=["validation","capacity","alternatives"])
    args = parser.parse_args()
    torch.set_num_threads(4)
    OUT.mkdir(parents=True,exist_ok=True)
    if args.suite == "validation":
        models = {name:build(name) for name in ("squeezenet","resnet18")}
        historical(models)
        validate(models)
    elif args.suite == "capacity":
        capacity(build("squeezenet"))
    else:
        alternatives(build("squeezenet"))


if __name__=="__main__":
    main()
