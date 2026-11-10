# Wider resize recovery

The local message command now offers `--wide-resize`. The existing fast search tests five scales, while the wider search tests each integer percentage from 50% through 95% plus 62.5%. It enumerates integer source dimensions compatible with floor or nearest rounding, deduplicates those dimensions, and ranks candidates by repeated-block agreement. As before, it tries at most 12 authenticated candidates. It searches uniform scaling with the existing Lanczos restoration and four-megapixel cap.

Run `python -m experiments.wide_resize` from the repository root with the tiled extra installed. The benchmark uses the ten existing covers with fresh 96-byte frames carrying the 25-byte message. Each marked image is encoded at JPEG 95, resized, then recompressed at JPEG 70. Test cases use 67% and 73% floor resizing and 87% nearest rounding. The 49% resize lies outside the search range. A clean image resized to 73% and compressed at the same quality acts as the negative control. No original dimensions are supplied. Timings include the direct decode attempt and the selected search.

## Results

| File condition | Fast search | Wide search | Median fast time | Median wide time |
|---|---:|---:|---:|---:|
| 67pct_floor | 0/10 | 8/10 | 0.23 s | 4.55 s |
| 73pct_floor | 0/10 | 10/10 | 0.28 s | 5.21 s |
| 87pct_nearest | 0/10 | 10/10 | 0.42 s | 7.31 s |
| 49pct_unlisted | 0/10 | 0/10 | 0.10 s | 1.44 s |
| clean_73pct | 0/10 | 0/10 | 0.27 s | 4.89 s |

The fast search remains available for common scales. The 67% grass and astronaut cases failed despite including the actual scale in the search. This benchmark does not isolate whether the ranking or the damaged payload caused those failures. An exploratory JPEG 70 → resize 73% → JPEG 70 demo also failed, so the main JPEG 95 → resize → JPEG 70 results do not generalize to that chain. The included successful demo follows the benchmark chain and independently decodes to the 25-byte message.

From the repository root, run the following command and enter the public test passphrase `ghostframe public benchmark fixture`.

```sh
python -m experiments.message_cli decode benchmarks/wide-resize/demo-resized-73.jpg --wide-resize
```
