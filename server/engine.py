"""The real encoder and decoder behind the demo site, with both models kept loaded.

Short (`classic`) is the legacy-v1 frame read by SqueezeNet 1.1; Subtle and Long are the
MobileNetV3-Small profiles. Profile names are part of the cryptographic identity, so they are
used exactly as registered.
"""
import io
import threading

import numpy as np
from PIL import Image

MODES = {
    "classic": dict(profile="legacy-v1", capacity=13, cap=8),
    "subtle": dict(profile="bb-mobilenet_v3_small-l2-b16p48", capacity=79, cap=2),
    "long": dict(profile="bb-mobilenet_v3_small-l8-b64p112", capacity=494, cap=8),
}
ORDER = ("classic", "subtle", "long")
AMPLIFY = 192  # difference images map the cap to 192/255, as the demo fixtures do


class Refused(Exception):
    """The encoder could not make a file that reads back; nothing was produced."""


class Engine:
    def __init__(self, threads=4):
        self.threads = threads
        self.models = {}
        self.ready = threading.Event()
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            if self.ready.is_set():
                return
            import torch
            from ghostframe import load_model
            from ghostframe_png import backbones

            torch.set_num_threads(self.threads)
            self.models = {"squeezenet1_1": load_model("cpu"), "mobilenet_v3_small": backbones.load("mobilenet_v3_small")}
            self.ready.set()

    def _model(self, mode):
        from ghostframe_png.core import PROFILES

        self.load()
        backbone = "squeezenet1_1" if mode == "classic" else PROFILES[MODES[mode]["profile"]].backbone
        return self.models[backbone]

    def encode(self, cover, message, passphrase, mode, progress=None):
        """Return the exact PNG bytes of a marked cover (HxWx3 uint8, sRGB). Raises Refused."""
        model = self._model(mode)
        if mode == "classic":
            from experiments.message_cli import neural_encode_bytes

            try:  # in memory: nothing is written to disk
                return neural_encode_bytes(Image.fromarray(cover), message, passphrase, model, progress=progress)
            except ValueError as exc:  # the legacy encoder signals a failed read-back with ValueError
                raise Refused(str(exc)) from exc
        from ghostframe_png import core

        try:
            return core.encode_message(cover, message, passphrase, MODES[mode]["profile"], model, progress=progress)
        except core.CapacityError as exc:
            raise Refused(str(exc)) from exc

    def decode(self, png, passphrase, mode):
        """Authenticated message bytes, or None. `png` is the uploaded file's bytes."""
        model = self._model(mode)
        if mode == "classic":
            from experiments.message_cli import neural_recover
            from ghostframe import read_image

            try:
                return neural_recover(read_image(io.BytesIO(png)), passphrase, model)
            except ValueError:
                return None
        from ghostframe_png import core

        try:
            return core.decode_message(core.load_png(io.BytesIO(png)), passphrase, MODES[mode]["profile"], model)
        except core.DecodeError:
            return None


def difference_png(cover, marked_png, mode):
    """|marked - original| amplified so the cap maps to 192/255, like the fixture difference images."""
    marked = np.asarray(Image.open(io.BytesIO(marked_png)).convert("RGB"), dtype=np.int16)
    delta = np.abs(marked - cover.astype(np.int16))
    image = Image.fromarray(np.clip(delta * (AMPLIFY // MODES[mode]["cap"]), 0, 255).astype(np.uint8))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
