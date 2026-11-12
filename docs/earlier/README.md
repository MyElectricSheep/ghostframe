# Earlier experiments

Before the `ghostframe-png` profiles, the project went through several carriers. They are kept
here with their reports and commands because the main results build on them, and because the
negative results matter as much as the positive ones. None of this is needed to use
`ghostframe-png`.

| Line of work | What it found | Report |
|---|---|---|
| Raw-bit channel (`ghostframe` CLI) | 16 and 32 raw bits survive a lossless PNG; crops break them. No authentication: any image yields bits. | [EXPERIMENTS.md](EXPERIMENTS.md), [CROP_ROBUSTNESS.md](CROP_ROBUSTNESS.md), [ENCODER_SCREEN.md](ENCODER_SCREEN.md), [EXTENDED.md](EXTENDED.md) |
| Tiled neural frame | A 13-byte authenticated frame in a 6×5 grid of tiles, PNG only. This became the `legacy-v1` profile. | [TILED.md](TILED.md), [TILED_ECC.md](TILED_ECC.md), [NEURAL_PNG_CAPACITY.md](NEURAL_PNG_CAPACITY.md) |
| Luminance carrier (not neural) | A conventional 8×8 block-brightness carrier that survives JPEG and some resizes and crops. Kept as a baseline. | [JPEG_CARRIER.md](JPEG_CARRIER.md), [ROBUSTNESS.md](ROBUSTNESS.md), [ALIGNMENT_SEARCH.md](ALIGNMENT_SEARCH.md), [MESSAGE_CLI.md](MESSAGE_CLI.md), [WIDE_RESIZE.md](WIDE_RESIZE.md), [SOFT_SEARCH.md](SOFT_SEARCH.md), [COMPOUND_SEARCH.md](COMPOUND_SEARCH.md), [JPEG_WINDOW_PILOT.md](JPEG_WINDOW_PILOT.md), [JPEG_ROUNDTRIP_SEARCH.md](JPEG_ROUNDTRIP_SEARCH.md), [JPEG_AUTHENTICATED_HOLDOUT.md](JPEG_AUTHENTICATED_HOLDOUT.md) |
| Other ideas | Smooth and transform-aware perturbations, a keyed lattice, multiscale loss, a TrustMark comparison. | [CREATIVE_EXPERIMENTS.md](CREATIVE_EXPERIMENTS.md), [GOAL_STATUS.md](GOAL_STATUS.md) |
| Summaries | The consolidated report, the first audit, the architecture of that stage and a dated log. | [FULL_REPORT.md](FULL_REPORT.md), [GHOSTFRAME_POC_AUDIT.md](GHOSTFRAME_POC_AUDIT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PROGRESS.md](PROGRESS.md) |

The commands below are the ones the earlier README carried. Run them from the repository root.

## Raw-bit channel (`ghostframe`)

### Reproduce on Linux x86-64 CPU

Use Python 3.12. Run these commands from this directory.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install 'torch==2.7.1+cpu' 'torchvision==0.22.1+cpu' --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
python -m pip install -e .
ghostframe encode --image examples/grace_hopper.jpg --bits 1010110011010010 --key test-key --output encoded.png
ghostframe decode --image encoded.png --key test-key --length 16
ghostframe benchmark --images examples/grace_hopper.jpg examples/china.jpg examples/flower.jpg --key test-key --output benchmarks/reproduced
ghostframe benchmark --images examples/china-sky.png --key test-key --output benchmarks/reproduced-low-detail
for budget in 2 4; do
  ghostframe benchmark --images examples/grace_hopper.jpg examples/china.jpg examples/flower.jpg examples/china-sky.png --key test-key --epsilon "$budget" --output "benchmarks/reproduced-epsilon-$budget"
done
python -m unittest discover -s tests -v
```

The first call downloads and verifies a 4.7 MiB checkpoint. Later runs use the verified local cache. The decoder uses the marked image, key, bit length, and this version's checkpoint and preprocessing. PNG preserves the 8-bit pixels the optimizer sees. Inputs are EXIF-oriented RGB PNG or JPEG, limited to 4 megapixels. CUDA and MPS are experimental.

### Channel design

The entire image is resized to 224 × 224 with antialiased bilinear interpolation and normalized with ImageNet RGB statistics. The final convolutional features are spatially averaged and L2-normalized. HMAC-SHA256 and SHAKE256 generate a stable set of unit-length sign vectors from the key. Each projection sign contributes one bit. Adam optimizes pixels within an 8-level per-channel bound by default. A straight-through estimator evaluates the margin on quantized RGB values while providing a gradient to the continuous pixels. The decoder does a single independent forward pass.

The raw channel returns bits even for untouched covers, corruption, or a wrong key. It has no detection or authentication signal. Use dummy payloads and dummy keys. The example key can appear in shell history. Visual fidelity metrics cannot establish secrecy against steganalysis. The protocol carries no framing, encryption, or ECC. The decoder needs the length supplied separately.

## Reproduce the crop comparison

Run from this directory after installing the dependencies.

```sh
python -m experiments.crop_robustness
```

The experiment runs the original optimizer and a crop-aware variant on paired 16- and 32-bit payloads. It saves PNGs and a per-case JSON report under `benchmarks/crop-robustness/`. See [crop robustness results](CROP_ROBUSTNESS.md) for the split, metrics and limitations.

## Reproduce the encoder screen

```sh
python -m experiments.encoder_screen
```

This experiment downloads and verifies the pretrained MobileNetV3 Small and ResNet-18 checkpoints on first use, then compares their crop stability against SqueezeNet 1.1. It writes the natural-image screen, paired payload results, and marked PNGs under `benchmarks/encoder-screen/`. See [encoder screening results](ENCODER_SCREEN.md).

## Reproduce the extended experiments

```sh
python -m experiments.extended validation
python -m experiments.extended capacity
python -m experiments.extended alternatives
```

The scripts use sample images bundled with scikit-image 0.25.2. Signed projection margins, decoded strings and fidelity metrics are in `benchmarks/extended/`. See [extended results](EXTENDED.md).

## Reproduce the tiled carrier experiment

```sh
python -m pip install -e '.[tiled]'
python -m experiments.tiled
```

The tiled experiment embeds a fixed-size authenticated frame into a 6×5 grid. It saves the marked PNGs and measures exact authenticated recovery after separate image transformations. Each run draws fresh salt and nonce bytes, so the exact ciphertext and error counts can vary. The main Ghostframe CLI uses the original raw-bit protocol. See [tiled results](TILED.md).

## Reproduce the tiled error-correction experiment

```sh
python -m pip install -e '.[tiled]'
python -m experiments.tiled_ecc
```

The experiment keeps the 480-bit tile grid and reserves 14 bytes for Reed–Solomon parity. It benchmarks a fixed one-byte authenticated message at the two-level RGB budget. See [the experiment report](TILED_ECC.md).

## Reproduce the JPEG carrier experiment

```sh
python -m pip install -e '.[tiled]'
python -m experiments.tiled_ecc  # Generates the matched control if absent.
python -m experiments.jpeg_carrier
python -m experiments.jpeg_stress
python -m experiments.jpeg_stress --spacing 3
```

The JPEG carrier is a separate research experiment using luminance modulation and the same authenticated Reed–Solomon frame as the tiled experiment. See [JPEG carrier results](JPEG_CARRIER.md).

## Reproduce geometry, codec and capacity follow-ups

```sh
python -m experiments.robustness
python -m experiments.jpeg_capacity
```

The follow-ups use the completed JPEG carrier benchmark as their source. See [the robustness report](ROBUSTNESS.md).

## Reproduce the bounded alignment search

```sh
python -m experiments.alignment_search
```

This follow-up uses the completed JPEG carrier benchmark as input and tests off-center crops with supplied original dimensions, and resizes without original dimensions. See [the alignment report](ALIGNMENT_SEARCH.md).

## Encode and decode a local message

From the repository root, after installing the tiled extra:

```sh
printf '%s' 'Meet at the station at 6.' > message.txt
python -m experiments.message_cli encode examples/china.jpg marked.jpg --message-file message.txt
python -m experiments.message_cli decode marked.jpg
```

The command prompts for a passphrase. In a non-interactive environment, supply `--passphrase-file PATH` to each command. Decode writes exactly the authenticated message bytes to stdout, so you can redirect them into a file. Use `--original-size WIDTH HEIGHT` to search for a crop offset or `--try-resize` to test the listed scale factors. See [the command and benchmark notes](MESSAGE_CLI.md).

For intermediate resize factors, run `python -m experiments.message_cli decode marked.jpg --wide-resize`.
The wider mode tests every integer percentage from 50% to 95%, plus 62.5%, and can take longer. See [the wide resize benchmark](WIDE_RESIZE.md).

## Final experiment sweep

See [the consolidated research report](FULL_REPORT.md) for the neural and conventional carrier results, held-out images, compound edits, detection and reproduction commands. The local message CLI also accepts `--try-exposure` for bounded uniform brightness recovery. Choose one recovery mode per decode.

For damaged frames, add `--soft` to the message decoder, optionally with a recovery mode such as `--wide-resize`. See [confidence-assisted decoding](SOFT_SEARCH.md) for its measured benefit and limits.

If an image was cropped and then resized, supply both the original dimensions and the crop dimensions before resizing. The decoder searches for the crop offset.

```sh
python -m experiments.message_cli decode received.jpg --original-size 512 512 --crop-size 482 482 --soft
```

See [compound JPEG recovery](COMPOUND_SEARCH.md) for the tested edits and limits.

## Authenticate a message in neural embeddings

From the repository root, after installing `.[tiled]`:

```sh
printf '%s' 'Meet at dawn.' > message.txt
python -m experiments.message_cli encode examples/grace_hopper.jpg marked.png \
  --carrier neural --message-file message.txt
python -m experiments.message_cli decode marked.png --carrier neural
```

Use `--carrier neural` for up to 13 bytes with a maximum change of eight levels per RGB channel, or `--carrier neural-ecc` for one byte with Reed–Solomon parity and a maximum change of two levels per channel. The original SqueezeNet checkpoint is fetched and verified on first use. The neural modes expect preserved PNG pixels and can refuse an encode if the saved file does not authenticate. The separate luminance mode remains the default for the conventional carrier.

See [objective verification](GOAL_STATUS.md), [architecture](ARCHITECTURE.md), and [security and framing](../THREAT_MODEL.md). The code and results for the optional pretrained-watermark comparator are available via `python -m pip install -e '.[learned]'` and `python -m experiments.learned_baseline`. That comparator downloads verified model assets separately.
