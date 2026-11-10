# Claude Design brief for Ghostframe

Design an open-source proof-of-concept page around a single question. Can a photo carry a message that a frozen image model can read from the numbers it produces?

This brief replaces the earlier two-method showcase brief. Use the embedding-based PNG experiment throughout the main experience. Historical comparisons can be linked from the research notes. Design a responsive, accessible, noncommercial experiment with one primary action, **Try the sample**.

## Main flow

1. **Compare the photos.** Show the original and encoded PNG at identical framing and resolution. Provide a keyboard-accessible A/B toggle or split comparison with a non-drag alternative.
2. **Reveal the pixel changes.** Offer an amplified absolute RGB difference view with the multiplier clearly stated. Keep the normal view available. Label the measured maximum per channel for the selected fixture.
3. **Recover the message.** Run the same frozen SqueezeNet 1.1 model over the same tile layout if a verified backend is available. Otherwise present the recovery as a recorded result. Show the exact recovered message after authentication. Offer the original cover as a negative control. The portrait cover was verified to emit no message.
4. **Explain it.** Use a simple schematic showing message encryption, small changes to photo tiles, the same frozen model reading each tile, and authenticated recovery. Explain an embedding as a list of numbers the model produces for a tile. The optimizer changes pixels so that selected readings of those numbers encode bits. The model weights remain fixed.
5. **Inspect the work.** Link to the open-source code when its URL is known, the reproducible offline CLI workflow, per-image research results and limitations. Keep capacity research below the main demo. The main fixture should reveal the readable sentence. Two longer fixtures from the experimental `ghostframe-png` profiles can sit in a "How much can it carry?" section below the main demo: a 75-byte sentence under a two-level cap and a 299-byte paragraph under an eight-level cap, on the same portrait. Label each with its profile name, its "experimental" status and the tested denominator: 123/123 held-out trials on 41 photographs 1280 px wide. Do not present them as the CLI default or as a guarantee for any image. The older 161-byte fixture contains a binary test pattern and belongs in the research notes.

## Verified fixtures

| Fixture | Message | Measured max RGB change | Amplified difference | Files in the source tree |
|---|---|---:|---|---|
| Main neural PNG (legacy v1, the entry point) | Meet at dawn. (13 bytes) | 8/255 per channel | `neural-difference.png`, ×24 | `examples/grace_hopper.jpg`, `benchmarks/goal-validation/neural-demo.png` |
| Neural PNG with error correction (legacy v2) | ! (one byte) | 2/255 per channel | `neural-ecc-difference.png`, ×96 | `examples/flower.jpg`, `benchmarks/goal-validation/neural-ecc-demo.png` |
| Experimental two-level profile `sw-l2-c10x8b16p48` | Meet at dawn. The north gate stays open until six. Bring the blue notebook. (75 bytes) | 2/255 per channel | `png-l2-sentence-difference.png`, ×96 | `benchmarks/embedding-showcase/png-l2-sentence.png` |
| Experimental eight-level profile `sw-l8-c10x8b40p64` | A 299-byte paragraph; exact text in `fixtures-v2.json` | 8/255 per channel | `png-l8-paragraph-difference.png`, ×24 | `benchmarks/embedding-showcase/png-l8-paragraph.png` |

Every encoded file authenticated in the audit. The two experimental fixtures were verified with the public CLI in fresh processes. Each decoded to the exact message at one and four CPU threads. Their negative controls exited with "no authenticated message" and printed nothing. The controls were `grace-hopper-original.png`, the unmarked cover, and the marked file under a wrong passphrase. Use the original PNG as the negative control in the UI. `fixtures.json` lists the legacy fixtures. `fixtures-v2.json` lists the experimental ones, with the exact messages, the checks run and SHA-256 hashes. The published fixture passphrase is `ghostframe public benchmark fixture`. The cover JPG is an input source. The encoded files and the recovery demo use PNG.

**Amplified difference.** Each difference image is |encoded − original| per RGB channel, multiplied so that the cap maps to 192/255: ×96 for a two-level cap and ×24 for an eight-level cap, clipped at 255. Show the multiplier next to the image, for example "differences ×24, real maximum 8/255". The blocky texture is the tile grid that the model reads. Nearly every pixel changes by a small amount, about 94 % of channel values in these fixtures. Do not describe the change as limited to a few pixels. To regenerate the images and recheck every fixture, run `python -m tools.make_showcase`. It skips existing PNGs, so delete them first to re-encode with a fresh salt.

**Measured caps and limits to state.** The caps are hard per-channel bounds, checked on the saved files. They are not measurements of perceptibility. On held-out photographs, the eight-level profile's median SSIM was 0.885, against 0.979 for the two-level profile. Show the eight-level fixture at full size in the A/B view and do not call it invisible. The experimental profiles can refuse flat, synthetic or very small images. They have no robustness to JPEG, resizing or cropping. Anyone who has the public reader can detect them. Benchmark numbers are in `docs/BENCHMARK.md`.

## Visual direction and handoff

Use a photographic contact-sheet layout with room for the image. Keep the headings conversational and measurements precise. Show a single large image stage on narrow screens. Give controls visible focus, support reduced motion, and express authentication status in text. The finished design should include a desktop and mobile flow, the compare and reveal states, recovery success and rejection, the schematic and the evidence section.

Keep this a public engineering experiment. Avoid account flows, pricing, JPEG transform controls, and claims of browser-local encoding, invisibility or guaranteed recovery. The verified implementation is an offline Python CLI. Live browser inference and uploads require separate implementation and validation. Use provided source attribution and distinguish recorded outcomes from interactive computation.
