"""Exercise the larger message profile on saved JPEGs."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from PIL import Image, ImageOps
from skimage import data

from experiments.jpeg_capacity import MESSAGE
from experiments.jpeg_carrier import OUT as JPEG_OUT
from experiments.message_cli import encode_file, recover_message
from experiments.robustness import COPIES, SPACING
from experiments.tiled import PASSWORD
from ghostframe import read_image

OUT = Path("benchmarks/message-cli")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    covers = json.loads((JPEG_OUT/"results.json").read_text())
    records = []
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        for row in covers:
            if (row["spacing"], row["repetitions"]) != (SPACING, COPIES):
                continue
            name = row["cover"]
            cover = Image.fromarray(getattr(data,name)()).convert("RGB")
            cover = ImageOps.contain(cover,(512,512),Image.Resampling.LANCZOS)
            path = temp/f"{name}.jpg"
            encode_file(cover, MESSAGE, PASSWORD, path)
            marked = read_image(path)
            width, height = marked.size
            cases = {}
            variants = [
                ("jpeg95", marked, {}),
                ("off_center_crop_jpeg70", marked.crop((13,21,width-17,height-9)),
                 {"original_size": marked.size}),
                ("resize75_jpeg70", marked.resize((width*3//4,height*3//4),Image.Resampling.LANCZOS),
                 {"try_resize": True}),
            ]
            for label, view, options in variants:
                if label != "jpeg95":
                    changed = temp/f"{name}-{label}.jpg"
                    view.save(changed,format="JPEG",quality=70,subsampling=2)
                    view = read_image(changed)
                start = perf_counter()
                try:
                    recovered = recover_message(view, PASSWORD, **options)
                except ValueError:
                    recovered = None
                cases[label] = dict(authenticated=recovered==MESSAGE, seconds=perf_counter()-start)
            records.append(dict(cover=name, dimensions=marked.size, cases=cases))
            print(name,cases,flush=True)
    (OUT/"results.json").write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
