# Tiled error correction

## Design

The tiled experiment recovered 13-byte authenticated messages from 2/4 untouched PNGs at a two-level RGB bound. In this follow-up the 6×5 grid and 16 bits per tile stay the same. The frame carries a one-byte version, 16-byte salt, 12-byte nonce, one encrypted message byte, and a 16-byte AES-GCM tag. The remaining 14 bytes of the 60-byte codeword are Reed–Solomon parity over GF(256). This can correct up to seven unknown byte errors before AES-GCM authentication. The passphrase and model remain the decoder inputs, together with the versioned grid and protocol. The benchmark passphrase is public.

Both decoder arms receive the same actual image and the same extracted 60 bytes. The raw arm authenticates the systematic 46-byte prefix directly. The corrected arm applies Reed–Solomon and then authenticates. This isolates the decoder contribution on a matched channel. It is distinct from comparing the earlier 13-byte protocol on a different sample. A bad tag rejects a corrupted or wrongly corrected frame.

Four covers are fresh to this study (camera, brick, grass and Hubble Deep Field). Astronaut and coffee are carryovers that failed at the lower budget in the original experiment. Covers are fitted inside 512×512 without changing aspect ratio. Each cover receives one codeword with a fresh random salt and nonce. All image arms are evaluated after actual PNG serialization. The report separates fresh and carryover results. This small pilot measures the tested frames, and pretraining overlap was not evaluated.

[Reedsolo implementation and decoder documentation](https://pypi.org/project/reedsolo/) · [scikit-image sample data and credits](https://scikit-image.org/docs/stable/api/skimage.data.html)

## Results

| Cover | Cohort | PNG byte errors | Raw PNG auth | Corrected PNG auth | Brightness raw / corrected | PSNR | SSIM | Encode |
|---|---|---:|---|---|---|---:|---:|---:|
| camera | Fresh | 0 | True | True | True / True | 43.03 dB | 0.973 | 35.90 s |
| brick | Fresh | 0 | True | True | True / True | 43.03 dB | 0.972 | 32.77 s |
| grass | Fresh | 0 | True | True | True / True | 42.84 dB | 0.997 | 44.87 s |
| hubble_deep_field | Fresh | 0 | True | True | True / True | 42.92 dB | 0.977 | 42.87 s |
| astronaut | Carryover | 0 | True | True | True / True | 43.24 dB | 0.976 | 36.59 s |
| coffee | Carryover | 4 | False | True | False / False | 42.95 dB | 0.978 | 54.24 s |

| Transformation | Raw exact | Corrected exact | Byte-error range |
|---|---:|---:|---:|
| png | 5/6 | 6/6 | 0–4 |
| jpeg95_420 | 0/6 | 0/6 | 47–57 |
| jpeg85_420 | 0/6 | 0/6 | 58–60 |
| jpeg70_420 | 0/6 | 0/6 | 58–60 |
| resize_75pct | 0/6 | 0/6 | 52–60 |
| crop_center_90pct | 0/6 | 0/6 | 58–60 |
| brightness_105pct | 5/6 | 5/6 | 0–8 |
| restore_first_three_tiles | 0/6 | 5/6 | 6–10 |

Reed–Solomon recovered the coffee PNG after four erroneous bytes, including three in the authenticated prefix. A fresh Python process independently recovered and authenticated the byte from coffee.png without the cover or the benchmark JSON. The four fresh covers were already exact before correction. Replacing the first three marked tiles with their original pixels was a deliberate control, scored separately from natural transformations. It produced six bad bytes in five cases and ten in the already-damaged coffee case. The corrected arm authenticated the first five.

JPEG 95 already damaged at least 47 of 60 bytes per cover, and the tested resize and crop caused at least 52 and 58 wrong bytes respectively. The parity budget addresses sparse errors on preserved PNGs. The experiment provides no evidence that adding this amount of parity can make the existing carrier robust to recompression or grid shifts. Each cover received one randomized frame. The fixed one-byte protocol, small cover set and public test passphrase make this a research experiment. The logical next test is a JPEG-tolerant carrier evaluated at the same RGB bound and with exact authentication.
