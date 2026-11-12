# Confidence-assisted decoding

The local 96-byte message CLI accepts an optional `--soft` flag. It ranks received bytes by the weakest absolute bit score in each byte. When a regular authenticated decode fails, it retries Reed–Solomon with up to six progressively larger sets of low-confidence bytes treated as erasures. Geometry search applies the same method only to the 12 shortlisted candidates and gives their hard decodes priority over their erasure retries. Missing bytes from a crop stay marked as erased and count toward the 24-byte parity budget. All candidate plaintext still requires AES-GCM authentication. The encoder and 96-byte frame format are compatible with previous outputs.

The benchmark reuses six known covers from the previous sweep, including difficult cases, with one fresh randomized codeword per cover. Hard and confidence-assisted decoding receive identical images. The test measures wide scale search at 67% and at 73% after a lower-quality first JPEG, plus box-filtered resize with the original size supplied to an external restoration step. The latter evaluates direct CLI decoding after restoration. The clean negative is a same-size JPEG 70. Run `python -m experiments.soft_search` to reproduce. This sample is a targeted pilot.

A synthetic unit test corrupts 13 bytes with low-confidence decisions. Ordinary correction fails, the erasure retry authenticates, and the same retry with the wrong passphrase returns no authenticated frame.

## Results

| Condition | Hard | Soft | Median hard | Median soft |
|---|---:|---:|---:|---:|
| 67_resize | 3/6 | 4/6 | 3.19 s | 3.42 s |
| 73_resize_from_jpeg70 | 2/6 | 3/6 | 3.28 s | 3.52 s |
| 73_box_known_size | 1/6 | 1/6 | 0.01 s | 0.39 s |
| clean_control | 0/6 | 0/6 | 0.01 s | 0.02 s |

The gains came from two files, one per resize condition. Box filtering remained difficult even after known-size restoration. The unchanged 96-byte format was also verified by decoding the earlier 73% demo from a separate CLI process with the new flag. No population-level recovery estimate follows from six selected covers and one codeword per cover.
