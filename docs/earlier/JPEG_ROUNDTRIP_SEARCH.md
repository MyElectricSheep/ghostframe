# Ghostframe compressor-in-the-loop benchmark

Butora, Puteaux and Bas inspect how candidate JPEG coefficients behave through a real compressor. This experiment borrows that measurement approach and applies it to Ghostframe's existing block-brightness carrier. It does not implement their robust coefficient selection or guarantee. Chen and Wornell's quantization index modulation provides background for the existing lattice and the phase-diversity controls.

- Butora, Puteaux and Bas, [Errorless Robust JPEG Steganography using Outputs of JPEG Coders](https://arxiv.org/abs/2211.04750).
- Chen and Wornell, [Quantization Index Modulation](https://sia.mit.edu/wp-content/uploads/2015/04/2001-chen-wornell-it.pdf).
- Jia, Fang and Zhang, [MBRS](https://arxiv.org/abs/2108.08211), describes training an encoder and decoder with real and simulated JPEG. That would be a separate experiment from the frozen-embedding PoC. This run did not evaluate it.

## Method

Use the same 11 previously marked PNG fixtures, deterministic block assignments and 768 target bits per fixture as the JPEG window pilot, plus a second seed per fixture that changes both block positions and target bits. The matched baseline uses the same flat spacing-3 rule. Small differences from the earlier pilot can result from floating-point summation order when scoring tied shifts. Every profile uses three replicas and a two-level RGB cap. No clean reference is needed at readout. The resize test gives the decoder the original dimensions and restores them before extraction.

Measure five candidate shift images per fitted JPEG quality. For each block, read the brightness after real Pillow JPEG compression. The independent profile selects shifts one block at a time. Joint profiles rank all 125 possible combinations for the three replicas using worst-case and mean signed confidence, with a small penalty for larger shifts and a clean-recovery constraint. Candidate measurements use a uniform shift choice across selected blocks in each candidate image. The final mixed-shift image is separately compressed and evaluated. This accounts for the possibility that candidate measurements do not exactly predict the final result.

The sparse fit uses JPEG qualities 35, 50, 70 and 85. The dense fit uses every fifth quality from 35 to 95. The low-quality grid adds 37, 39, 41, 43 and 45 to the dense fit. Double compression and resize were absent from all fits. The finer grid was chosen after the first screening run. The second seed reuses the same covers.

## Results

Each cell counts bit errors out of 16,896 across both seed runs. Zero errors means exact raw bits before error correction.

| Profile | PNG | Q70 | Q60 | Q50 | Q42 | Q40 | Q38 | Q35 | Q95 then Q50 | 75% resize then Q70 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 0 | 40 | 75 | 70 | 168 | 274 | 211 | 367 | 80 | 161 |
| Mixed spacing | 0 | 49 | 112 | 75 | 195 | 144 | 267 | 480 | 110 | 144 |
| Mixed phase | 0 | 55 | 71 | 92 | 164 | 253 | 231 | 372 | 130 | 143 |
| Actual JPEG, independent | 6 | 17 | 54 | 30 | 146 | 345 | 207 | 65 | 37 | 141 |
| Actual JPEG, joint sparse | 0 | 14 | 48 | 13 | 171 | 354 | 276 | 30 | 40 | 144 |
| Actual JPEG, joint dense | 0 | 14 | 19 | 13 | 132 | 65 | 253 | 41 | 20 | 133 |
| Actual JPEG, joint low-quality grid | 0 | 17 | 21 | 18 | 41 | 71 | 258 | 50 | 21 | 117 |
| Actual JPEG, joint with spacing and phase diversity | 0 | 13 | 48 | 16 | 256 | 257 | 386 | 48 | 51 | 182 |

Dense joint selection had exact raw recovery on 22/22 PNG cases, 19/22 at JPEG 50, 8/22 at JPEG 40 and 11/22 at JPEG 35. The matched baseline had 22/22, 15/22, 0/22 and 2/22. The denser low-quality grid helped at quality 42, which was absent from the fit, and after resize, but regressed at quality 38. The sparse fit had the fewest errors at quality 35 and regressed at quality 40. No variant dominated across all channels.

The experiment leaves the CLI and neural carrier unchanged. The fixtures had already been marked and the two seeds are not independent image sets. Results do not establish authenticated message recovery, blind alignment, detectability or cross-codec portability. The full project test suite could not run successfully because the current environment lacks its dependencies. The standalone benchmark enforced the cap for all 176 profile and fixture runs.

## Reproduce

From the extracted archive root with Python, NumPy and Pillow:

```sh
python -m experiments.jpeg_roundtrip_search
python -m experiments.jpeg_roundtrip_search --seed-suffix /replication --output benchmarks/jpeg-roundtrip-replication.json
```
