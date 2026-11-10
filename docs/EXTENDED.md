# Extended experiments

## Design

- **Margins.** Re-score the existing matched pilot PNGs and held-out crops and verify decoded bit strings against the original logs. A signed margin is the raw keyed projection multiplied by the intended bit sign. A positive value favors the correct bit. Compare the clean margin and the score loss under cropping.
- **Fresh covers.** Use four scikit-image photos absent from prior Ghostframe experiments and three new evaluation crop boxes. Compare SqueezeNet and ResNet-18 at two RGB levels. Test clean-only encoding at 16 and 32 bits, and the more expensive four-crop objective at 16 bits. One deterministic payload and key per cover and size. Fresh here means new to these Ghostframe experiments. Pretraining overlap was not checked.
- **Capacity and error correction.** SqueezeNet clean-only at two and eight levels, 16 to 512 raw bits, plus a 32-bit payload repeated across three disjoint projection blocks. Evaluate majority-vote recovery against the same raw 32-bit payload at the same budget. This measures one simple code, whose overhead is substantial.
- **Alternatives.** Compare keyed QR-orthogonalized directions at 32, 128, and 384 bits with the matched random-direction baseline. Compare clean-only optimization with a JPEG-aware variant at 16 and 32 bits. The JPEG-aware variant runs Pillow's real 4:2:0 quality-80 codec on the forward pass and approximates its gradient with the identity. Test unseen quality levels and a thumbnail/recompression chain.

Every encoding is evaluated after a PNG round-trip. Other checks include three JPEG quality levels, a resize, a crop, brightness adjustment, and an aspect-preserving 320-pixel thumbnail followed by JPEG 85. The thumbnail chain is a synthetic proxy. These results do not establish behavior for a specific messaging app or service.

Image sources. Eileen Collins portrait from NASA, coffee by Rachel Michetti (CC0), the DSCOVR launch by SpaceX, and Chelsea by Stefan van der Walt (CC0). [scikit-image data credits](https://scikit-image.org/docs/stable/api/skimage.data.html)

## Embedded margins

| Encoder | Objective | Median correct PNG margin | Median correct margin of bits lost in crops | Previously correct bits lost in crops |
|---|---|---:|---:|---:|
| squeezenet | baseline | 0.0324 | 0.0264 | 405/955 (42.4%) |
| squeezenet | crop_aware | 0.0275 | 0.0153 | 281/880 (31.9%) |
| resnet18 | baseline | 0.0353 | 0.0323 | 426/955 (44.6%) |
| resnet18 | crop_aware | 0.0348 | 0.0190 | 269/890 (30.2%) |

## Fresh-cover recovery

| Encoder | Objective | Bits | PNG exact | Novel crop exact | JPEG 70 exact | Thumbnail JPEG exact |
|---|---|---:|---:|---:|---:|---:|
| squeezenet | baseline | 16 | 4/4 | 0/12 | 3/4 | 2/4 |
| squeezenet | baseline | 32 | 2/4 | 0/12 | 0/4 | 0/4 |
| squeezenet | crop_aware | 16 | 4/4 | 3/12 | 1/4 | 1/4 |
| resnet18 | baseline | 16 | 4/4 | 0/12 | 3/4 | 1/4 |
| resnet18 | baseline | 32 | 4/4 | 0/12 | 0/4 | 0/4 |
| resnet18 | crop_aware | 16 | 4/4 | 0/12 | 1/4 | 1/4 |

## Capacity sweep

| RGB levels | Raw bits | PNG exact | PNG BER | Novel crop exact | JPEG 70 exact | Thumbnail JPEG exact | Median PSNR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 16 | 4/4 | 0.0% | 0/12 | 1/4 | 1/4 | 42.80 dB |
| 2 | 32 | 3/4 | 1.6% | 0/12 | 0/4 | 0/4 | 42.85 dB |
| 2 | 64 | 1/4 | 8.6% | 0/12 | 0/4 | 0/4 | 42.65 dB |
| 2 | 128 | 0/4 | 23.4% | 0/12 | 0/4 | 0/4 | 42.63 dB |
| 2 | 256 | 0/4 | 34.7% | 0/12 | 0/4 | 0/4 | 42.61 dB |
| 2 | 384 | 0/4 | 35.8% | 0/12 | 0/4 | 0/4 | 42.57 dB |
| 2 | 512 | 0/4 | 40.7% | 0/12 | 0/4 | 0/4 | 42.63 dB |
| 8 | 16 | 4/4 | 0.0% | 0/12 | 4/4 | 2/4 | 35.95 dB |
| 8 | 32 | 4/4 | 0.0% | 0/12 | 4/4 | 2/4 | 34.23 dB |
| 8 | 64 | 4/4 | 0.0% | 0/12 | 1/4 | 0/4 | 34.05 dB |
| 8 | 128 | 3/4 | 0.6% | 0/12 | 0/4 | 0/4 | 33.30 dB |
| 8 | 256 | 0/4 | 12.3% | 0/12 | 0/4 | 0/4 | 32.72 dB |
| 8 | 384 | 0/4 | 19.6% | 0/12 | 0/4 | 0/4 | 32.75 dB |
| 8 | 512 | 0/4 | 28.7% | 0/12 | 0/4 | 0/4 | 32.70 dB |

## Repetition-code pilot

| RGB levels | Encoding | PNG exact | Novel crop exact | JPEG 70 exact | Thumbnail JPEG exact |
|---:|---|---:|---:|---:|---:|
| 2 | raw | 3/4 | 0/12 | 0/4 | 0/4 |
| 2 | repeat3 | 0/4 | 0/12 | 0/4 | 0/4 |
| 8 | raw | 4/4 | 0/12 | 4/4 | 2/4 |
| 8 | repeat3 | 4/4 | 0/12 | 1/4 | 0/4 |

## Alternative objectives and projections

| Variant | Raw bits | PNG exact | Novel crop exact | JPEG 70 exact | Thumbnail JPEG exact |
|---|---:|---:|---:|---:|---:|
| Matched baseline | 32 | 3/4 | 0/12 | 0/4 | 0/4 |
| orthogonal | 32 | 3/4 | 0/12 | 0/4 | 0/4 |
| Matched baseline | 128 | 0/4 | 0/12 | 0/4 | 0/4 |
| orthogonal | 128 | 0/4 | 0/12 | 0/4 | 0/4 |
| Matched baseline | 384 | 0/4 | 0/12 | 0/4 | 0/4 |
| orthogonal | 384 | 0/4 | 0/12 | 0/4 | 0/4 |
| Matched baseline | 16 | 4/4 | 0/12 | 1/4 | 1/4 |
| jpeg_aware | 16 | 4/4 | 0/12 | 3/4 | 1/4 |
| Matched baseline | 32 | 3/4 | 0/12 | 0/4 | 0/4 |
| jpeg_aware | 32 | 3/4 | 0/12 | 1/4 | 0/4 |

## Conclusions and gates

- In the earlier pilot, previously correct bits lost in crops had lower median clean margins than correctly read PNG bits overall. The crop-aware objectives reduced that loss, but roughly 30% of previously correct bits still flipped. On the fresh inputs, SqueezeNet crop-aware recovered three of twelve 16-bit crop cases. ResNet-18 crop-aware recovered none. Clean-only ResNet-18 recovered all four 32-bit PNGs in the validation arm, but its crop and JPEG 70 results at 32 bits were zero.
- At the two-level budget the capacity sweep recovered all four 16-bit PNGs and three of four 32-bit PNGs. At eight levels it reached four of four at 64 bits and three of four at 128 bits. The eight-level 32-bit coffee example shows visible texture. The contact sheet in benchmarks/extended/coffee-fidelity.png shows the source, two-level output, eight-level output, and a 24× difference map in reading order.
- Training through quality-80 JPEG improved transfer to quality 70 on this small matched sample, but it did not improve the tested thumbnail pipeline or crop recovery. The QR and repetition alternatives did not make the channel reliably usable at higher payload sizes. These results cover one simple repetition code, not the space of error-correcting codes.
- A concrete offline format with a 16-byte KDF salt, 12-byte AES-GCM nonce, 16-byte tag, 1-byte version and 2-byte length would need 384 bits for a one-byte message, before error correction. Both tested pixel budgets recovered zero of four 384-bit payloads even on unmodified PNGs. At eight levels the bit error rate was 19.6%. A 128-bit dead-drop identifier was also unreliable across the tested images, before crop or recompression. Encryption, the online service and the product interface remain gated.
- This run tested four fresh covers and one deterministic message per arm and size. The objectives reuse a CPU setup and the earlier crop positions for training. Screenshots, real platform round-trips, another hardware backend and steganalysis remain unverified. The trained watermark and coverless approaches retain the research comparison in RESEARCH.md. They were outside this extended encoder experiment.
