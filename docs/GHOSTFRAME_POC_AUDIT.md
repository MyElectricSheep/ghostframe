# Ghostframe proof-of-concept audit

The offline command-line proof of concept was verified on a Linux CPU host. All 26 tests passed with the project's pinned versions of PyTorch, torchvision, NumPy, Pillow, scikit-image, cryptography and reedsolo. The JPEG candidate remains an experiment. The design prompt describes a proposed showcase.

## Claims checked

| Claim | Audit result |
|---|---|
| A frozen model can read a short authenticated message from an encoded PNG | A fresh 13-byte neural encode on the included portrait was recovered in a separate CLI process. The archived full-message PNG also decoded correctly. Comparing the archived image against its actual source measured a maximum change of 8 per RGB channel. |
| A neural example can meet the two-level cap | The separate one-byte neural ECC PNG decoded successfully. Comparing it to its flower source measured a maximum change of 2 per channel. The full-message neural profile uses a different budget. |
| Decoder needs the expected model and passphrase | Six archived neural files authenticated with the pinned model and public fixture password. All six rejected the wrong password, and all six rejected the alternate ResNet-18 checkpoint, on the tested host. |
| The default luminance CLI handles PNG and JPEG | Fresh encodes of the same 25-byte message recovered byte-for-byte in separate processes. The PNG had maximum delta 2. The JPEG 95 file had maximum delta 55 versus the source after serialization in this example. This delta includes JPEG compression. |
| Authentication gates output | The same luminance CLI rejected the clean source and a wrong passphrase, returned a nonzero exit status, and emitted zero plaintext bytes in both cases. |
| JPEG-aware encoding improves recovery at strong JPEG compression | The paired repeat produced 15/18 recoveries at JPEG 35 versus 8/18 for the baseline. This replicated the original seven-message gain, which was 16/18 versus 9/18. The repeat used the same nine covers with newly sealed frames, and all 144 marked outputs respected the pre-compression two-level cap. |
| The candidate is uniformly more robust | Recovery depends on channel and frame. Original JPEG 38 totals tied at 10/18, but two recoveries were gained and two lost. On the repeat, WebP 75 fell from 8/18 to 7/18. |

## Paired JPEG results

Each count uses two messages per cover, with the same sealed frame across encoder variants. The second round uses the same covers, not a second independent image set. The original and repeat use Pillow 13.0.0 for the holdout. The separate regression suite and CLI checks use the pinned Pillow 12.3.0.

| Channel | Original baseline | Original candidate | Repeat baseline | Repeat candidate |
|---|---:|---:|---:|---:|
| PNG | 18/18 | 18/18 | 18/18 | 18/18 |
| JPEG 70 | 18/18 | 18/18 | 18/18 | 18/18 |
| JPEG 50 | 12/18 | 14/18 | 13/18 | 14/18 |
| JPEG 40 | 16/18 | 18/18 | 16/18 | 18/18 |
| JPEG 38 | 10/18 | 10/18 | 10/18 | 13/18 |
| JPEG 35 | 9/18 | 16/18 | 8/18 | 15/18 |
| JPEG 95, then JPEG 50 | 12/18 | 14/18 | 13/18 | 14/18 |
| 75% resize, then JPEG 70 | 16/18 | 16/18 | 16/18 | 16/18 |
| WebP 75 | 8/18 | 8/18 | 8/18 | 7/18 |

## Showcase wording

Label each fixture with its carrier, payload bytes and measured cap. Use the uncompressed marked PNG to compute the amplified encoder difference. A comparison with a recompressed JPEG is a separate measurement. Display recorded recovery outcomes for that particular file and transform. Aggregate rates do not predict a single fixture's outcome.

The JPEG candidate uses block brightness and the neural mode uses embeddings. An authenticated result validates the frame and passphrase, and does not establish sender identity. Visual subtlety does not establish resistance to detection. The resize row uses known original dimensions. No current run verifies native screenshots, actual messaging services, general cross-platform recovery, or browser execution. The default CLI uses the original encoder. Work on the showcase interface was outside this audit.

## Reproduce

From the Ghostframe source root after installing its pinned dependencies and tiled extra:

```bash
OMP_NUM_THREADS=2 python -m unittest discover -s tests -v
python -m experiments.goal_validation --worker 4
```

See the prior authenticated holdout report for the exact input filenames and runner invocation. Use the runner's output option to preserve the archived results. Random salts and nonces make recovery counts vary between runs.
