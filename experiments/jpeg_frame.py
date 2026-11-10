"""Shared authenticated JPEG capacity frame."""
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from reedsolo import RSCodec, ReedSolomonError

from experiments.frame_keys import derive

VERSION = b"\x03"
AAD = b"Ghostframe JPEG capacity research v3" + VERSION
FRAME_BYTES = 96
MESSAGE_BYTES = 26
PARITY_BYTES = 24
MESSAGE = b"Meet at the station at 6."


def seal(message, password):
    if len(message) > MESSAGE_BYTES:
        raise ValueError("Message exceeds 26 bytes")
    salt, nonce = os.urandom(16), os.urandom(12)
    plain = bytes([len(message)]) + message.ljust(MESSAGE_BYTES,b"\0")
    data = VERSION + salt + nonce + AESGCM(derive(password,salt)).encrypt(nonce,plain,AAD)
    return bytes(RSCodec(PARITY_BYTES).encode(data))


def unseal(received, password, *, erasures=()):
    if len(received) != FRAME_BYTES:
        raise ValueError("Invalid frame length")
    try:
        data, _, _ = RSCodec(PARITY_BYTES).decode(received, erase_pos=list(erasures))
        if data[:1] != VERSION:
            raise ValueError("Invalid version")
        salt, nonce = bytes(data[1:17]), bytes(data[17:29])
        plain = AESGCM(derive(password,salt)).decrypt(nonce,bytes(data[29:]),AAD)
        if plain[0] > MESSAGE_BYTES:
            raise ValueError("Invalid message length")
        return plain[1:1+plain[0]]
    except (ReedSolomonError, InvalidTag) as exc:
        raise ValueError("Invalid frame") from exc


