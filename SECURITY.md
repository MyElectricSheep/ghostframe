# Security

Ghostframe is research code. Its cryptography (scrypt from Python's `hashlib`, which uses
OpenSSL, and AES-256-GCM from the `cryptography` package) has not been audited, and the marked images are easy to detect. Please do not rely on
it to protect anything that matters. The design and its limits are in
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

The pinned torch 2.7.1 has published security advisories. None of them is reachable here: the
model checkpoints are pinned by SHA-256 and loaded with `weights_only=True`.

If you find a flaw, for example a way to read or forge a message without the passphrase, or a
crash on a crafted input, please report it privately through GitHub's
[private vulnerability reporting](https://github.com/MyElectricSheep/ghostframe/security/advisories/new)
rather than in a public issue. I will reply as soon as I can, and credit you if you wish.
