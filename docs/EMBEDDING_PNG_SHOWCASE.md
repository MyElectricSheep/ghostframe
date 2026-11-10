# Claude Design brief for Ghostframe

Design an open-source proof-of-concept page around a single question. Can a photo carry a message that a frozen image model can read from the numbers it produces?

This brief replaces the earlier two-method showcase brief. Use the embedding-based PNG experiment throughout the main experience. Historical comparisons can be linked from the research notes. Design a responsive, accessible, noncommercial experiment with one primary action, **Try the sample**.

## Main flow

1. **Compare the photos.** Show the original and encoded PNG at identical framing and resolution. Provide a keyboard-accessible A/B toggle or split comparison with a non-drag alternative.
2. **Reveal the pixel changes.** Offer an amplified absolute RGB difference view with the multiplier clearly stated. Keep the normal view available. Label the measured maximum per channel for the selected fixture.
3. **Recover the message.** Run the same frozen SqueezeNet 1.1 model over the same tile layout if a verified backend is available. Otherwise present the recovery as a recorded result. Show the exact recovered message after authentication. Offer the original cover as a negative control. The portrait cover was verified to emit no message.
4. **Explain it.** Use a simple schematic showing message encryption, small changes to photo tiles, the same frozen model reading each tile, and authenticated recovery. Explain an embedding as a list of numbers the model produces for a tile. The optimizer changes pixels so that selected readings of those numbers encode bits. The model weights remain fixed.
5. **Inspect the work.** Link to the open-source code when its URL is known, the reproducible offline CLI workflow, per-image research results and limitations. Keep capacity research below the main demo. The 161-byte experimental fixture is a separate evidence item and contains a binary test pattern. It authenticated on three screening covers and the separately decoded portrait under an eight-level per-channel cap. The main fixture should reveal the readable sentence.

## Verified fixtures

| Fixture | Message | Measured max RGB change | Files in the source tree |
|---|---|---:|---|
| Main neural PNG | Meet at dawn. (13 bytes) | 8/255 per channel | `examples/grace_hopper.jpg` and `benchmarks/goal-validation/neural-demo.png` |
| Neural PNG with error correction | ! (one byte) | 2/255 per channel | `examples/flower.jpg` and `benchmarks/goal-validation/neural-ecc-demo.png` |

Both encoded files authenticated in the audit. Ready-to-use original PNGs, amplified difference images, and the fixture manifest are in `benchmarks/embedding-showcase/`. The published fixture passphrase is `ghostframe public benchmark fixture`. The cover JPG is an input source. The encoded files and the recovery demo use PNG. The benchmark capacity candidates are separate experimental profiles. Label any of their numbers with the tested denominator and pixel budget. Avoid presenting them as the capacity of the existing CLI.

## Visual direction and handoff

Use a photographic contact-sheet layout with room for the image. Keep the headings conversational and measurements precise. Show a single large image stage on narrow screens. Give controls visible focus, support reduced motion, and express authentication status in text. The finished design should include a desktop and mobile flow, the compare and reveal states, recovery success and rejection, the schematic and the evidence section.

Keep this a public engineering experiment. Avoid account flows, pricing, JPEG transform controls, and claims of browser-local encoding, invisibility or guaranteed recovery. The verified implementation is an offline Python CLI. Live browser inference and uploads require separate implementation and validation. Use provided source attribution and distinguish recorded outcomes from interactive computation.
