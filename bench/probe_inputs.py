"""Phase-1 probes of the legacy entry points. Prints one line per finding."""
import hashlib, io, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from reedsolo import RSCodec
from ghostframe import read_image, load_model, embedding, tensor

def probe(label, fn):
    try:
        print(f"{label}: {fn()}")
    except Exception as exc:
        print(f"{label}: {type(exc).__name__}: {exc}")

tmp = Path(tempfile.mkdtemp())
def save(img, name, **kw):
    p = tmp / name; img.save(p, **kw); return p

# 1. Image modes through read_image
rgba = Image.new("RGBA", (64, 64), (200, 10, 10, 0))
probe("RGBA fully transparent -> RGB", lambda: read_image(save(rgba, "a.png")).getpixel((0, 0)))
i16 = Image.fromarray(np.full((64, 64), 40000, np.uint16))
p16 = save(i16, "i16.png")
probe("16-bit gray PNG mode/pixel", lambda: (Image.open(p16).mode, read_image(p16).getpixel((0, 0))))
rgb48 = tmp / "rgb48.png"
probe("P mode", lambda: read_image(save(Image.new("P", (64, 64)), "p.png")).mode)
probe("CMYK JPEG", lambda: read_image(save(Image.new("CMYK", (64, 64), (0, 0, 0, 255)), "c.jpg")).getpixel((0, 0)))
# 2. Truncated PNG
good = save(Image.fromarray(np.random.default_rng(0).integers(0, 255, (128, 128, 3), np.uint8)), "g.png")
(tmp / "t.png").write_bytes(good.read_bytes()[:3000])
probe("truncated PNG", lambda: read_image(tmp / "t.png").size)
# 3. Metadata carried into marked PNG (legacy neural_encode path uses image.copy())
src = read_image("examples/flower.jpg")
buf = io.BytesIO(); src.copy().save(buf, format="PNG")
probe("flower.jpg ICC carried into PNG", lambda: "icc_profile" in Image.open(io.BytesIO(buf.getvalue())).info)
ex = Image.new("RGB", (64, 64)); exif = Image.Exif(); exif[0x010F] = "SecretCamera"; exif[0x0132] = "2026:01:01"
j = save(ex, "e.jpg", exif=exif.tobytes())
buf = io.BytesIO(); read_image(j).copy().save(buf, format="PNG")
probe("EXIF carried into PNG", lambda: b"SecretCamera" in buf.getvalue())
# 4. Batch vs single embedding numerics, and thread dependence
torch.set_num_threads(4)
model = load_model("cpu")
before = hashlib.sha256(b"".join(p.detach().numpy().tobytes() for p in model.parameters())).hexdigest()
img = read_image("examples/grace_hopper.jpg")
tiles = torch.cat([tensor(img.crop((x, 0, x + 51, 75)), "cpu") for x in range(0, 408, 51)])
with torch.inference_mode():
    batch = embedding(model, tiles)
    single = torch.cat([embedding(model, t[None]) for t in tiles])
    torch.set_num_threads(1)
    single1 = torch.cat([embedding(model, t[None]) for t in tiles])
probe("max |batch-single| embedding", lambda: float((batch - single).abs().max()))
probe("max |4thr-1thr| embedding", lambda: float((single - single1).abs().max()))
torch.set_num_threads(4)
# 5. Model mutation through an encode
from experiments.neural_png_capacity import roundtrip
probe("161-byte roundtrip (35 steps)", lambda: {k: v for k, v in roundtrip(model, img, "grid_wide_ecc", 8, 35).items() if k in ("authenticated", "bit_errors")})
after = hashlib.sha256(b"".join(p.detach().numpy().tobytes() for p in model.parameters())).hexdigest()
probe("weights unchanged after encode", lambda: before == after)
# 6. Reed-Solomon block boundary: a frame longer than 255-nsym
probe("RS(32) codeword length for 300-byte frame", lambda: len(RSCodec(32).encode(bytes(300))))
