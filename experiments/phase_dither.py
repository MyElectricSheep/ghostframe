"""Compare fixed and key-shifted luminance lattices at the same RGB cap."""
import hashlib
import hmac
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from skimage.metrics import peak_signal_noise_ratio

from experiments.carrier_controls import source_image
from experiments.final_sweep import FRESH, boundary_score, jpeg
from experiments.jpeg_capacity import FRAME_BYTES, MESSAGE, seal, unseal
from experiments.jpeg_carrier import OUT as JPEG_OUT, embed, extract
from experiments.robustness import detection_score
from experiments.tiled import PASSWORD

OUT = Path("benchmarks/phase-dither")
KEY = bytes(range(32))  # Public test fixture only.


def phase_offsets(key, count):
    seed = hmac.digest(key, b"ghostframe/experimental-phase-dither", "sha256")
    values = np.frombuffer(hashlib.shake_256(seed).digest(count * 2), dtype=">u2")
    return values.astype(np.float64) / 32768


def decode_case(image, phase, codeword):
    received = extract(image, 3, 3, FRAME_BYTES, phase=phase)
    try:
        success = unseal(received, PASSWORD) == MESSAGE
    except ValueError:
        success = False
    return dict(authenticated=success, byte_errors=sum(
        actual != expected for actual, expected in zip(received, codeword, strict=True)
    ))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prior = json.loads((JPEG_OUT / "results.json").read_text())
    names = [row["cover"] for row in prior if (row["spacing"], row["repetitions"]) == (3, 3)]
    phase = phase_offsets(KEY, FRAME_BYTES * 8 * 3)
    wrong = phase_offsets(KEY[::-1], len(phase))
    records = []
    for name in (*names, *FRESH):
        cover = source_image(name)
        codeword = seal(MESSAGE, PASSWORD)
        original = np.asarray(cover)
        clean_jpeg = jpeg(cover, 70)
        for label, offsets in (("fixed", None), ("dither", phase)):
            start = perf_counter()
            marked = embed(cover, codeword, 3, 3, phase=offsets)
            seconds = perf_counter() - start
            pixels = np.asarray(marked)
            assert np.abs(pixels.astype(np.int16) - original).max() <= 2
            q70 = jpeg(marked, 70)
            cases = {key: decode_case(view, offsets, codeword)
                     for key, view in (("png", marked), ("jpeg70", q70), ("jpeg50", jpeg(marked, 50)))}
            detection = {"png_protocol": [detection_score(cover), detection_score(marked)],
                         "jpeg_protocol": [detection_score(clean_jpeg), detection_score(q70)],
                         "png_edges": [boundary_score(cover), boundary_score(marked)],
                         "jpeg_edges": [boundary_score(clean_jpeg), boundary_score(q70)]}
            records.append(dict(cover=name, mode=label, cases=cases, detection=detection,
                                wrong_phase=decode_case(marked, wrong, codeword)["authenticated"],
                                psnr=float(peak_signal_noise_ratio(original, pixels)), seconds=seconds))
        pending = OUT / "results.tmp"
        pending.write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")
        pending.replace(OUT / "results.json")
        print(name, flush=True)


if __name__ == "__main__":
    main()
