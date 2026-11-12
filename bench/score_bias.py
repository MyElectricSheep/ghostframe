"""Natural (unmarked) projection scores: bias from non-negative embeddings."""
import numpy as np, torch
from PIL import Image
from skimage import data
from ghostframe import load_model, embedding, tensor, projections
from experiments.neural_png_capacity import boxes
torch.set_num_threads(4)
m = load_model("cpu")
names = ["astronaut", "chelsea", "coffee", "rocket", "immunohistochemistry", "hubble_deep_field"]
embs = []
with torch.inference_mode():
    for n in names:
        im = Image.fromarray(getattr(data, n)()).convert("RGB") if n != "moto" else None
        embs.extend(embedding(m, tensor(im.crop(b), "cpu")) for b in boxes(im.size, 10, 8))
E = torch.cat(embs)
print("min entry", float(E.min()), "embedding count", len(E))
mu = E.mean(0); mu_hat = mu / mu.norm()
print("cos(mean, each) median", float((E @ mu_hat).median()))
P = projections("probe", 256)
raw = E @ P.T
Pc = P - (P @ mu_hat)[:, None] * mu_hat
Pc = Pc / Pc.norm(dim=1, keepdim=True)
cen = E @ Pc.T
for label, s in (("random", raw), ("mean-removed", cen)):
    bias = s.mean(0).abs()
    print(label, "median |per-direction mean|", float(bias.median()), "median per-direction std", float(s.std(0).median()),
          "frac bits where natural sign agrees >90% of tiles", float(((s > 0).float().mean(0).sub(.5).abs() > .4).float().mean()))
