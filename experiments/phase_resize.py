"""Check geometry recovery for the keyed-phase lattice."""
import json

from experiments.alignment_search import search_resize
from experiments.carrier_controls import source_image
from experiments.final_sweep import authenticated, jpeg, resize
from experiments.jpeg_capacity import FRAME_BYTES, MESSAGE, PARITY_BYTES, seal
from experiments.jpeg_carrier import embed
from experiments.phase_dither import KEY, OUT, phase_offsets
from experiments.tiled import PASSWORD


def main():
    prior = json.loads((OUT / "results.json").read_text())
    phase = phase_offsets(KEY, FRAME_BYTES * 8 * 3)
    records = []
    for row in prior:
        if row["mode"] != "fixed":
            continue
        cover = source_image(row["cover"])
        codeword = seal(MESSAGE, PASSWORD)
        cases = {}
        for label, offsets in (("fixed", None), ("dither", phase)):
            marked = embed(cover, codeword, 3, 3, phase=offsets)
            received = jpeg(resize(jpeg(marked, 95), 75), 70)
            cases[label] = search_resize(received, bits=FRAME_BYTES * 8, parity_bytes=PARITY_BYTES,
                                         verify=authenticated, phase=offsets)
        records.append(dict(cover=row["cover"], cases=cases))
        print(row["cover"], {key: value["authenticated"] for key, value in cases.items()}, flush=True)
    (OUT / "resize.json").write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
