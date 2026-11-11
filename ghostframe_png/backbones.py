"""Alternative frozen feature extractors for the PNG carrier (experimental, benchmark only).

SqueezeNet 1.1 stays on its original code path (`ghostframe.embedding`) so the existing profiles
keep their exact numerics and identities. Every other backbone is an ImageNet torchvision
checkpoint pinned by SHA-256, read the same way: resize the tile to 224 × 224, ImageNet
normalization, the convolutional feature map, global mean pooling, then L2 normalization.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torchvision.models as tvm

SIZE = 224
DATA_DIR = Path(__file__).with_name("data")


@dataclass(frozen=True)
class Backbone:
    name: str
    url: str
    sha256: str
    dim: int
    build: str            # torchvision constructor name
    calibration_pin: str  # SHA-256 of data/<name>-tile-mean-v1.npy ("" until built)

    @property
    def calibration(self):
        return DATA_DIR / f"{self.name}-tile-mean-v1.npy"


BACKBONES = {b.name: b for b in (
    Backbone("resnet18", "https://download.pytorch.org/models/resnet18-f37072fd.pth",
             "f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec", 512, "resnet18",
             "fff0194df875be0ed38341b9aaa208b47bcc2037a64f9ee512aeaab597304004"),
    Backbone("mobilenet_v3_small", "https://download.pytorch.org/models/mobilenet_v3_small-047dcff4.pth",
             "047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f", 576, "mobilenet_v3_small",
             "455b044c303ccabbe732f2a5883017f616ea144c6f6801e373d97fd6aa3054d8"),
    Backbone("efficientnet_b0", "https://download.pytorch.org/models/efficientnet_b0_rwightman-7f5810bc.pth",
             "7f5810bc96def8f7552d5b7e68d53c4786f81167d28291b21c0d90e1fca14934", 1280, "efficientnet_b0",
             "219c988787abc195a5d45f0f5894f79c337a10462f68938669be1ea7027a57f8"),
    Backbone("convnext_tiny", "https://download.pytorch.org/models/convnext_tiny-983f1562.pth",
             "983f1562536e84ff750a1576fb08e54de751dbf2e17c0d8a4a13704341fdcd3d", 768, "convnext_tiny",
             "453966fab3054bbc9246c317999a78bfa997962bfecf4f708a831db8f912931e"),
)}


class Features(torch.nn.Module):
    """Frozen trunk returning the pre-pooling feature map."""

    def __init__(self, backbone, trunk):
        super().__init__()
        self.backbone = backbone
        self.trunk = trunk
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406])[None, :, None, None])
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225])[None, :, None, None])

    def ghostframe_embed(self, image):
        resized = F.interpolate(image, (SIZE, SIZE), mode="bilinear", align_corners=False, antialias=True)
        return F.normalize(self.trunk((resized - self.mean) / self.std).mean(dim=(-1, -2)), dim=-1)


def _trunk(name, model):
    if name == "resnet18":
        return torch.nn.Sequential(*list(model.children())[:-2])
    return model.features


def _weights(backbone):
    from ghostframe import load_checkpoint

    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / backbone.url.rsplit("/", 1)[-1]
    if not backbone.sha256:  # first fetch: verify torchvision's hash prefix, then pin the full digest here
        if not checkpoint.exists():
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            prefix = backbone.url.rsplit("-", 1)[-1].split(".")[0]
            torch.hub.download_url_to_file(backbone.url, str(checkpoint), hash_prefix=prefix)
        raise RuntimeError(f"Pin {backbone.name}: sha256 {hashlib.sha256(checkpoint.read_bytes()).hexdigest()}")
    return load_checkpoint(backbone.url, backbone.sha256)


_loaded = {}


def load(name):
    if name not in _loaded:
        backbone = BACKBONES[name]
        model = getattr(tvm, backbone.build)()
        model.load_state_dict(_weights(backbone))
        _loaded[name] = Features(backbone, _trunk(name, model)).eval().requires_grad_(False)
    return _loaded[name]


def calibration_mean(backbone):
    path = backbone.calibration
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != backbone.calibration_pin:
        raise RuntimeError(f"Unexpected calibration digest for {path}: {digest}")
    mean = torch.from_numpy(np.load(path, allow_pickle=False).astype(np.float32))
    return mean / mean.norm(), digest
