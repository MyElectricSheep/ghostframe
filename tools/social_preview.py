"""Write docs/img/social-preview.png, the repository's 1280x640 link preview.

    python -m tools.social_preview

Everything in it is real: the painting is demo-photos/fixtures/antonello-portrait-of-a-man/long.png,
and the grid shows that file's pixels around the sitter's left eye, with each pixel's red value in
the original and how far it moved. The logo is drawn from site/public/favicon.svg.
"""
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "demo-photos" / "fixtures" / "antonello-portrait-of-a-man"
OUT = ROOT / "docs" / "img" / "social-preview.png"
W, H = 1280, 640
BG, FG, MUTED, GOLD = (14, 16, 20), (236, 238, 242), (178, 184, 194), (255, 206, 96)
FONTS = Path("/usr/share/fonts/truetype/dejavu")
EYE = (620, 684)  # the sitter's left eye (viewer's right), in source pixels
N, CELL, GX, GY = 8, 58, 520, 150


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def ghost(draw, x, y, px):
    """The favicon's 7x8 pixel ghost, with its one blue eye pixel."""
    svg = (ROOT / "site" / "public" / "favicon.svg").read_text()
    for gx, gy, fill in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="3.90" height="3.90" fill="(#[0-9a-f]+)"', svg):
        c, r = round((float(gx) - 10.5) / 3.9), round((float(gy) - 7.5) / 3.9)
        colour = (63, 100, 140) if fill == "#3f648c" else (246, 244, 241)
        draw.rectangle((x + c * px, y + r * px, x + (c + 1) * px - 1, y + (r + 1) * px - 1), fill=colour)


def main():
    orig = Image.open(FIX / "original.png").convert("RGB")
    marked = Image.open(FIX / "long.png").convert("RGB")
    o_all, m_all = np.asarray(orig).astype(int), np.asarray(marked).astype(int)
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    scale = 600 / orig.height
    px, py = 30, 20
    im.paste(marked.resize((round(orig.width * scale), 600), Image.LANCZOS), (px, py))

    x0, y0 = EYE[0] - N // 2, EYE[1] - N // 2
    o, m = o_all[y0:y0 + N, x0:x0 + N], m_all[y0:y0 + N, x0:x0 + N]
    left, top = px + x0 * scale - 3, py + y0 * scale - 3
    right, bottom = px + (x0 + N) * scale + 3, py + (y0 + N) * scale + 3
    d.rectangle((left, top, right, bottom), outline=FG, width=2)
    d.line((right, top, GX, GY), fill=FG, width=1)
    d.line((right, bottom, GX, GY + N * CELL), fill=FG, width=1)
    im.paste(Image.fromarray(m.astype(np.uint8)).resize((N * CELL, N * CELL), Image.NEAREST), (GX, GY))
    for r in range(N):
        for c in range(N):
            ink = (20, 20, 20) if m[r, c].mean() > 140 else (240, 240, 240)
            delta = m[r, c, 0] - o[r, c, 0]
            d.text((GX + c * CELL + 6, GY + r * CELL + 8), f"{o[r, c, 0]}", fill=ink, font=font("DejaVuSansMono.ttf", 13))
            d.text((GX + c * CELL + 6, GY + r * CELL + 30), f"{delta:+d}", fill=GOLD if delta else ink,
                   font=font("DejaVuSansMono-Bold.ttf", 14))

    headline = font("DejaVuSans-Bold.ttf", 32)
    d.text((GX, 38), "There is a message", fill=FG, font=headline)
    d.text((GX, 80), "hidden in this painting.", fill=FG, font=headline)

    rx = GX + N * CELL + 30
    ghost(d, rx, 478, 5)
    d.text((rx + 52, 478), "Ghostframe", fill=FG, font=font("DejaVuSans-Bold.ttf", 26))
    for i, line in enumerate(["Nudge the pixels, move the", "embedding vectors. A frozen",
                              "model decodes what the eye", "can't see."]):
        d.text((rx, 528 + i * 22), line, fill=MUTED, font=font("DejaVuSans.ttf", 16))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, optimize=True)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
