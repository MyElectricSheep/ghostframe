# Local message command

`python -m experiments.message_cli` accepts PNG or JPEG covers up to four megapixels. The input must contain at least 2,304 complete 8×8 blocks. The 96-byte authenticated frame supports messages up to 26 bytes and uses the previously tested spacing-three, three-copy luminance profile. Message files and decoded output are binary-safe. The passphrase is entered interactively or read from the specified file. The encoder checks that the serialized PNG or JPEG decodes and authenticates before creating the output. It refuses to overwrite existing files. JPEG output is encoded at quality 95 with 4:2:0 subsampling. The two-level pixel bound applies before serialization, and PNG preserves it. JPEG compression can change additional pixel values.

Direct decoding is attempted first. Optional crop recovery uses supplied original dimensions and searches integer offsets up to 64 total trimmed pixels per axis. Optional resize recovery tests 50%, 62.5%, 75%, 80%, and 90%. Optional exposure recovery tests whole-percent brightness multipliers from 85% through 115% using --try-exposure. These are separate recovery modes. The decoder only emits bytes after successful AES-GCM authentication. The tool uses the conventional luminance carrier and its signal remains detectable by the earlier protocol-aware detector.

The file benchmark uses the same ten covers as the earlier luminance benchmark, with fresh randomized 96-byte frames carrying the 25-byte message. It writes JPEG 95, then exercises the saved JPEG directly and as input to an off-center crop or 75% resize, each re-encoded at JPEG 70. Crop decoding knows the original dimensions. Resize decoding has only the candidate scale list. These are local codec tests and do not establish real platform behavior.

Run `python -m experiments.message_benchmark` to reproduce the file benchmark.

## Results

| File condition | Authenticated | Median decode |
|---|---:|---:|
| jpeg95 | 10/10 | 0.400 s |
| off_center_crop_jpeg70 | 10/10 | 0.478 s |
| resize75_jpeg70 | 10/10 | 0.670 s |

The separate command-line smoke test encoded a new JPEG from examples/china.jpg and recovered the exact message in a second process. With the wrong passphrase the command exited unsuccessfully and wrote no message bytes. The tested geometry recovery assumes the original dimensions for the asymmetric crop or the applicable scale and rounding convention for a resize. Arbitrary edits and real messaging services remain unverified.
