# Architecture

Ghostframe is a local research application with two independent carriers and three authenticated frame profiles. The recipient supplies the image, passphrase and carrier mode. The neural profiles also require the pinned SqueezeNet 1.1 checkpoint. No profile requires the original image, saved features, network service, or external payload database after dependency and checkpoint setup.

| CLI carrier | Encoder and decoder | User bytes | Embedded bytes |
|---|---|---:|---:|
| neural | Thirty tiles with sixteen keyed projection decisions per tile. Frozen SqueezeNet 1.1. | 0–13 | 60 |
| neural-ecc | Same tile grid with Reed–Solomon correction before authentication. | exactly 1 | 60 |
| luminance | Three replicas distributed over aligned 8×8 block means. Reed–Solomon correction before authentication. | 0–26 | 96 |

The neural modes use the exact existing v1 and v2 benchmark frames and preserve marked pixels in PNG. Their per-tile projection keys are public protocol constants. The original raw-bit command accepts an explicit projection key and has no message authentication. The conventional luminance branch is independently selectable, with no inference in the carrier itself.

The message CLI seals a frame, marks pixels, serializes the intended output, and independently extracts and authenticates the frame from that serialized output before creating a file. It refuses to overwrite existing files. Luminance has bounded resize, crop, compound crop/resize and exposure recovery. Optional confidence erasures spend part of the parity budget. The neural mode only supports the preserved-image workflow.

The installed raw-bit command is `ghostframe`. The authenticated command is `python -m experiments.message_cli` from the extracted repository root. Setup and test commands are in README.md. See [security and framing](../THREAT_MODEL.md), [benchmark evidence](FULL_REPORT.md), and [goal verification](GOAL_STATUS.md).
