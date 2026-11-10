"""Benchmark candidates. New-profile variants are plain Profile specs; legacy ones name their code path."""
from dataclasses import asdict, replace

from ghostframe_png.core import PROFILES, Profile

PASSPHRASE = b"ghostframe public benchmark fixture"  # public fixture only


def variant(base, name, **changes):
    profile = replace(PROFILES[base] if isinstance(base, str) else base, name=name, **changes)
    profile.validate()
    return profile


def spec(profile):
    return {k: v for k, v in asdict(profile).items() if k != "aad_extra"}


def from_spec(data):
    profile = Profile(**data)
    profile.validate()
    return profile


L2 = PROFILES["png-l2-c10x8b12"]
L8 = PROFILES["png-l8-c10x8b24"]

# Legacy encoders, reproduced through their original code.
LEGACY = {
    "legacy-v1-13B": dict(kind="v1", epsilon=8, capacity=13),
    "legacy-v2-1B": dict(kind="v2", epsilon=2, capacity=1),
    "legacy-49B": dict(kind="capacity", profile="grid_light_wide_ecc", epsilon=2, capacity=49, steps=35),
    "legacy-161B": dict(kind="capacity", profile="grid_wide_ecc", epsilon=8, capacity=161, steps=35),
}


def suites():
    s = {}
    # Ablation 1: mean-removed directions, everything else matched (layout, parity, optimizer, cap).
    s["centering-l2"] = [L2, variant(L2, "abl-l2-uncentered", centered=False)]
    s["centering-l8"] = [variant(L8, "abl-l8-c10x8b32", bits=32, parity=48),
                         variant(L8, "abl-l8-c10x8b32-uncentered", bits=32, parity=48, centered=False)]
    # Ablation 2: optimizer target margin at matched layout.
    s["margin-l2"] = [variant(L2, f"abl-l2-m{m}", margin=m) for m in (0.005, 0.02)]
    s["lr-l2"] = [variant(L2, f"abl-l2-lr{lr}", lr=lr) for lr in (0.5, 2.0)]
    # Capacity sweep at the two-level cap.
    s["sweep-l2"] = [
        variant(L2, "sw-l2-c10x8b16p32", bits=16, parity=32),
        variant(L2, "sw-l2-c10x8b16p48", bits=16, parity=48),
        variant(L2, "sw-l2-c10x8b20p48", bits=20, parity=48),
        variant(L2, "sw-l2-c12x10b12p36", cols=12, rows=10, parity=36),
        variant(L2, "sw-l2-c12x10b16p56", cols=12, rows=10, bits=16, parity=56),
        variant(L2, "sw-l2-c8x6b20p32", cols=8, rows=6, bits=20, parity=32),
    ]
    # Capacity sweep at the eight-level cap.
    s["sweep-l8"] = [
        variant(L8, "sw-l8-c10x8b32p48", bits=32, parity=48),
        variant(L8, "sw-l8-c10x8b40p64", bits=40, parity=64),
        variant(L8, "sw-l8-c12x10b32p72", cols=12, rows=10, bits=32, parity=72),
        variant(L8, "sw-l8-c12x10b40p96", cols=12, rows=10, bits=40, parity=96),
        variant(L8, "sw-l8-c14x12b32p96", cols=14, rows=12, bits=32, parity=96),
    ]
    by_name = {p.name: p for suite in s.values() for p in suite}
    s["finalists-tune"] = [by_name[n] for n in (
        "sw-l2-c10x8b20p48", "sw-l2-c12x10b12p36", "sw-l2-c10x8b16p32",
        "sw-l8-c12x10b32p72", "sw-l8-c10x8b40p64")]
    # All three 2-level candidates above failed china; next in capacity order (screen 6/6 each).
    s["finalists-tune-l2b"] = [by_name["sw-l2-c10x8b16p48"], L2, by_name["sw-l2-c8x6b20p32"]]
    return s
