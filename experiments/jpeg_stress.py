"""Stress the three-copy luminance carrier across JPEG chains."""
import argparse
import io
import json

from PIL import Image, ImageOps
from skimage import data

from experiments.jpeg_carrier import OUT, embed, evaluate, extract
from experiments.tiled import PASSWORD
from experiments.tiled_ecc import MESSAGE, decode_frame
from ghostframe import read_image

CHAINS = {
    "jpeg_60_420": ((60, 2),),
    "jpeg_50_420": ((50, 2),),
    "jpeg_85_444": ((85, 0),),
    "jpeg_85_then_70_420": ((85, 2), (70, 2)),
    "jpeg_70_then_70_420": ((70, 2), (70, 2)),
}


def encode_jpeg(image, quality, subsampling):
    with io.BytesIO() as buffer:
        image.save(buffer, format="JPEG", quality=quality, subsampling=subsampling)
        return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spacing", type=int, choices=(2, 3), default=2)
    spacing = parser.parse_args().spacing
    results = []
    source = json.loads((OUT/"results.json").read_text())
    if len(source) != 30:
        raise ValueError("Run the complete carrier benchmark before the stress test")
    for row in source:
        if (row["spacing"], row["repetitions"]) != (spacing, 3):
            continue
        cover = row["cover"]
        codeword = bytes.fromhex(row["codeword"])
        if spacing == 2:
            marked = read_image(OUT/f"{cover}.png")
        else:
            original = Image.fromarray(getattr(data, cover)()).convert("RGB")
            image = ImageOps.contain(original, (512, 512), Image.Resampling.LANCZOS)
            marked = embed(image, codeword, spacing, 3)
        outcomes = {}
        for label, chain in CHAINS.items():
            view = marked
            for quality, subsampling in chain:
                jpeg = encode_jpeg(view, quality, subsampling)
                with Image.open(io.BytesIO(jpeg)) as decoded:
                    view = decoded.convert("RGB")
            outcomes[label] = evaluate(view, codeword, spacing, 3)
        results.append(dict(cover=cover, cases=outcomes))
    filename = "stress.json" if spacing == 2 else "stress-spacing3.json"
    (OUT/filename).write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")

    if spacing != 2:
        return

    # A standalone JPEG fixture for the independent decode demonstration.
    for row in source:
        if (row["spacing"], row["repetitions"]) == (2, 3) and row["cases"]["jpeg70_420"]["corrected"]:
            marked = read_image(OUT/f"{row['cover']}.png")
            path = OUT/"demo-quality70.jpg"
            path.write_bytes(encode_jpeg(marked, 70, 2))
            assert decode_frame(extract(read_image(path), 2, 3), PASSWORD)[0] == MESSAGE
            print(path, row["cover"])
            break


if __name__ == "__main__":
    main()
