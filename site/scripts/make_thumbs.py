"""Resized display copies for the cover picker. Never used for decoding.

    .venv/bin/python site/scripts/make_thumbs.py   # writes site/public/thumbs/
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "site" / "public" / "thumbs"
PHOTOS = {"antonello": "antonello-portrait-of-a-man", "coffee": "coffee-beans", "milky": "milky-way"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, stem in PHOTOS.items():
        with Image.open(ROOT / "demo-photos" / f"{stem}.jpg") as image:
            image = image.convert("RGB")
            image.thumbnail((144, 144), Image.LANCZOS)
            image.save(OUT / f"{key}.jpg", quality=85, optimize=True)
        print(OUT / f"{key}.jpg")


if __name__ == "__main__":
    main()
