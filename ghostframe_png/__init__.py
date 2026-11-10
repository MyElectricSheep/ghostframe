"""Authenticated messages in frozen-model embeddings of PNG tiles.

Profiles are explicit and versioned. Every profile is bound into the AES-GCM
associated data, so a frame encoded under one profile never authenticates under
another. See docs/PNG_PROFILES.md for the wire format and measured results.
"""
from ghostframe_png.core import (  # noqa: F401
    PROFILES, CapacityError, DecodeError, InputError, Profile,
    capacity, decode_message, encode_message, load_cover, load_png, read_scores,
)
