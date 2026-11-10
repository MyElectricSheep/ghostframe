"""Measure synchronization, codec transfer and a protocol-aware detector."""
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps, features
from reedsolo import RSCodec, ReedSolomonError
from skimage import data

from experiments.jpeg_carrier import (
    BITS, OUT as JPEG_OUT, embed, evaluate, luminance, positions,
)
from experiments.tiled import PASSWORD
from experiments.tiled_ecc import MESSAGE, PARITY_BYTES, authenticate

OUT = Path("benchmarks/robustness")
SPACING, COPIES = 3, 3


def aligned_scores(image, size=None, offset=(0, 0)):
    """Read complete original-grid blocks visible inside a crop."""
    y, x = positions(size or image.size, COPIES)
    x, y = x - offset[0], y - offset[1]
    visible = ((x[:, 0, 0] >= 0) & (x[:, 0, -1] < image.width)
               & (y[:, 0, 0] >= 0) & (y[:, -1, 0] < image.height))
    pixels = np.asarray(image.convert("RGB"))
    mean = luminance(pixels[y[visible], x[visible]]).mean(axis=(-1, -2))
    scores = np.zeros(BITS * COPIES)
    scores[visible] = np.cos(np.pi * mean / SPACING)
    return scores.reshape(COPIES, BITS), visible.reshape(COPIES, BITS)


def candidate(image, size, offset=(0, 0)):
    scores, seen = aligned_scores(image, size, offset)
    missing = (~seen.any(axis=0)).reshape(-1, 8).any(axis=1)
    received = np.packbits(scores.sum(axis=0) < 0).tobytes()
    return received, np.flatnonzero(missing).tolist()


def recover(received, erasures):
    try:
        frame, _, _ = RSCodec(PARITY_BYTES).decode(received, erase_pos=erasures)
        return authenticate(bytes(frame), PASSWORD) == MESSAGE
    except (ReedSolomonError, ValueError):
        return False


def score_candidate(image, size, offset, codeword):
    received, erasures = candidate(image, size, offset)
    return dict(authenticated=recover(received, erasures), erasures=len(erasures),
                byte_errors=sum(a != b for a, b in zip(received, codeword, strict=True)))


def center_search(image):
    """Try bounded symmetric crop hypotheses with no original dimensions."""
    start = perf_counter()
    checked = 0
    for percentage in range(1, 13):
        approximate_x = round(image.width * percentage / (100 - 2*percentage))
        approximate_y = round(image.height * percentage / (100 - 2*percentage))
        for dx in range(max(0, approximate_x-1), approximate_x+2):
            for dy in range(max(0, approximate_y-1), approximate_y+2):
                size = image.width+2*dx, image.height+2*dy
                try:
                    received, erasures = candidate(image, size, (dx, dy))
                except ValueError:
                    continue
                checked += 1
                if recover(received, erasures):
                    return dict(authenticated=True, size=size, offset=(dx,dy),
                                candidates=checked, seconds=perf_counter()-start)
    return dict(authenticated=False, candidates=checked, seconds=perf_counter()-start)


def transcode(image, codec, **kwargs):
    with io.BytesIO() as buffer:
        image.save(buffer, format=codec, **kwargs)
        buffer.seek(0)
        with Image.open(buffer) as decoded:
            return decoded.convert("RGB")


def detection_score(image):
    scores, _ = aligned_scores(image)
    return float(np.abs(scores.mean(axis=0)).mean())


def evaluate_cover(row):
    name = row["cover"]
    original = Image.fromarray(getattr(data, name)()).convert("RGB")
    clean = ImageOps.contain(original, (512, 512), Image.Resampling.LANCZOS)
    codeword = bytes.fromhex(row["codeword"])
    marked = embed(clean, codeword, SPACING, COPIES)
    width, height = marked.size
    dx, dy = width//20, height//20
    center = marked.crop((dx,dy,width-dx,height-dy))
    crop = marked.crop((dx,dy,width-dx//2,height-dy//3))
    resized = marked.resize((width*3//4,height*3//4), Image.Resampling.LANCZOS)
    # Screenshot proxy: capture a scaled display region as a lossless image.
    viewport = Image.new("RGB", (800,600), "#202020")
    viewport.paste(resized,(19,23))
    screenshot = viewport.crop((19,23,19+resized.width,23+resized.height))
    screenshot = transcode(screenshot, "PNG")
    aligned = {
        "center_crop_oracle": score_candidate(center,marked.size,(dx,dy),codeword),
        "asymmetric_crop_oracle": score_candidate(crop,marked.size,(dx,dy),codeword),
        "center_crop_blind": center_search(center),
        "asymmetric_crop_blind": center_search(crop),
        "center_crop_then_jpeg70_oracle": score_candidate(
            transcode(center,"JPEG",quality=70,subsampling=2),marked.size,(dx,dy),codeword),
        "resize_then_restore_size": score_candidate(
            resized.resize(marked.size,Image.Resampling.LANCZOS),marked.size,(0,0),codeword),
        "scaled_screenshot_then_restore_size": score_candidate(
            screenshot.resize(marked.size,Image.Resampling.LANCZOS),marked.size,(0,0),codeword),
    }
    codec_settings = [("jpeg70","JPEG",dict(quality=70,subsampling=2))]
    if features.check("webp"):
        codec_settings.extend((("webp_lossless","WEBP",dict(lossless=True)),
                               ("webp85","WEBP",dict(quality=85))))
    if features.check("avif"):
        codec_settings.append(("avif85","AVIF",dict(quality=85,max_threads=2)))
    codecs = {label:evaluate(transcode(marked,codec,**args),codeword,SPACING,COPIES)
              for label,codec,args in codec_settings}
    clean_jpeg = transcode(clean,"JPEG",quality=70,subsampling=2)
    marked_jpeg = transcode(marked,"JPEG",quality=70,subsampling=2)
    detection = {"png": [detection_score(clean),detection_score(marked)],
                 "jpeg70": [detection_score(clean_jpeg),detection_score(marked_jpeg)]}
    return dict(cover=name, geometry=aligned, codecs=codecs, detection=detection)


def detector_results(records):
    results = {}
    for channel in ("png", "jpeg70"):
        pairs = [row["detection"][channel] for row in records]
        predictions = []
        for index, (clean, marked) in enumerate(pairs):
            training = pairs[:index] + pairs[index+1:]
            threshold = (max(pair[0] for pair in training) + min(pair[1] for pair in training)) / 2
            predictions.append(dict(cover=records[index]["cover"], threshold=threshold,
                                    clean_flagged=clean >= threshold, marked_flagged=marked >= threshold))
        results[channel] = predictions
    return results


def main():
    rows = json.loads((JPEG_OUT/"results.json").read_text())
    OUT.mkdir(parents=True,exist_ok=True)
    records = []
    for row in rows:
        if (row["spacing"],row["repetitions"]) == (SPACING,COPIES):
            record = evaluate_cover(row)
            records.append(record)
            pending=OUT/"results.tmp"
            pending.write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
            pending.replace(OUT/"results.json")
            print(record["cover"],flush=True)
    (OUT/"detector.json").write_text(json.dumps(detector_results(records), indent=2)+"\n")


if __name__ == "__main__":
    main()
