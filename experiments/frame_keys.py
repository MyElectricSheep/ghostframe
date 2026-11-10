"""Password derivation and public benchmark fixture."""
import hashlib

PASSWORD = b"ghostframe public benchmark fixture"


def derive(password, salt):
    return hashlib.scrypt(password, salt=salt, n=2**17, r=8, p=1, maxmem=256*1024**2, dklen=32)
