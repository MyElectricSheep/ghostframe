# Security and framing

Ghostframe is experimental. Encryption protects the contents of an authenticated frame under the passphrase and cryptographic assumptions. Steganography concerns hiding the existence of a payload. A subtle image change is insufficient evidence of undetectability. The raw-bit command emits unauthenticated guesses and is for research.

## Wire layouts

All offsets start at zero. Each authenticated frame begins with one version byte, a random 16-byte salt and a random 12-byte nonce. Each frame uses a separate fixed profile string and version as associated data. Scrypt derives 32 key bytes with N=131072, r=8, p=1, and a 256 MiB implementation memory ceiling. AES-256-GCM uses a full 16-byte tag. No key is stored in the image.

| Profile | Authenticated plaintext | Ciphertext bytes | Tag bytes | Parity bytes | Total |
|---|---|---:|---:|---:|---:|
| v1 neural | Two-byte big-endian length and 13-byte padded message | 15 | 16 | 0 | 60 |
| v2 neural-ecc | Exactly one message byte | 1 | 16 | 14 | 60 |
| v3 luminance | One-byte length and 26-byte padded message | 27 | 16 | 24 | 96 |

The fixed salt, nonce, tag and version consume 45 bytes before plaintext framing and parity. The v2 one-byte message therefore requires 46 bytes before parity. Reed–Solomon can correct up to seven unknown byte errors in v2 or twelve in v3, or a mix of errors and erasures within the parity budget. Corruption outside the budget is still subject to authentication, which rejects invalid candidates.

## Threat assessment

- **Offline password guesses.** Carrier extraction is public in the authenticated modes, and an adversary can test a passphrase against the tag. Scrypt increases work per guess. A weak password still gives weak protection. Public benchmark passphrases are for examples.
- **Detection and known covers.** The previous protocol-aware detector flagged all 14 marked luminance covers and none of their matched clean controls before and after JPEG in the pilot. Someone with an exact clean source can difference the pixels directly. No broad detector resistance or indistinguishability claim follows from the RGB bound. The neural branch has no formal steganalysis assurance.
- **Fingerprinting.** The public grid, projection schedule, carrier profile, and deterministic model preprocessing can identify the protocol. Wrong-model controls demonstrate rejection on six fixtures across two CPU thread settings. That is a compatibility result, not proof of resistance to identification or attack.
- **Metadata and disclosure.** Passwords and plaintext are never intentionally placed in image metadata. The CLI reserializes image pixels, but this is not a metadata audit or a full anonymization tool. Input and output photos may expose people or locations. Passphrase files, source message files, recovered stdout, shell redirects, and marked-image copies need their own handling.
- **Integrity and availability.** AES-GCM rejects wrong passwords and failed corrections. A modified, resampled, recompressed or removed carrier may be unrecoverable. The decoder needs the expected frame profile and, for neural decoding, the exact checkpoint and preprocessing. Neither frame supplies sender identity, replay protection, or deniability.
- **Deployment.** No hosted dead drop is used. A public service would introduce a separate access and retention model. This implementation validates offline short messages within the stated capacities.

[Scrypt RFC 7914](https://www.rfc-editor.org/rfc/rfc7914) · [NIST AES-GCM specification](https://csrc.nist.gov/pubs/sp/800/38/d/final)
