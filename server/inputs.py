"""Input rules from the site copy, checked on the server. Codes match the design's ISSUE keys.

Hide: PNG or JPEG; at most 4 MP; at least 160 x 128; no transparency; no 16-bit/HDR; no CMYK/Lab.
Read: PNG only (a JPEG gets `jpegRead`). Other colour profiles (Display P3) are converted to sRGB.
"""
import io

import numpy as np
from PIL import Image, UnidentifiedImageError

MAX_PIXELS = 4_000_000
MIN_W, MIN_H = 160, 128
MAX_UPLOAD = 40 * 1024 * 1024


class Issue(Exception):
    def __init__(self, code, **details):
        super().__init__(code)
        self.code, self.details = code, details


def _open(data, formats):
    if len(data) > MAX_UPLOAD:
        raise Issue("big")
    try:
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise Issue("type") from exc
    if image.format not in formats:
        raise Issue("jpegRead" if image.format == "JPEG" and "JPEG" not in formats else "type")
    w, h = image.size
    if w * h > MAX_PIXELS:
        raise Issue("big", w=w, h=h)
    if image.mode in ("I", "F", "I;16", "I;16B", "I;16L", "I;16N") or image.mode.startswith("I;16"):
        raise Issue("deep")
    if image.mode in ("CMYK", "LAB"):
        raise Issue("cmyk")
    return image


def _check_alpha(image):
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if "A" in image.getbands() and np.asarray(image.getchannel("A")).min() < 255:
        raise Issue("alpha")


def cover(data):
    """Validated cover for Hide: (HxWx3 uint8 sRGB pixels, colour-conversion note or None)."""
    from ghostframe_png import core

    image = _open(data, ("PNG", "JPEG"))
    image.load()
    _check_alpha(image)
    w, h = image.size
    if w < MIN_W or h < MIN_H:
        raise Issue("small", w=w, h=h)
    info = {}
    try:
        rgb = core.load_cover(io.BytesIO(data), info)
    except core.InputError as exc:
        raise Issue("type", reason=str(exc)) from exc
    if rgb.shape[1] < MIN_W or rgb.shape[0] < MIN_H:  # after EXIF rotation
        raise Issue("small", w=rgb.shape[1], h=rgb.shape[0])
    return rgb, info.get("colour_conversion")


def marked_png(data):
    """Validated upload for Read: must be a PNG within the size rules. Returns the bytes unchanged."""
    image = _open(data, ("PNG",))
    image.load()
    _check_alpha(image)
    return data
