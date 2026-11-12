# Demo photos

Cover photos for the demo website. All three come from the preregistered held-out benchmark set
(`bench/manifest-v1.json`). They are the exact files that were tested, byte for byte (the SHA-256
hashes match the manifest), and they are free to use. The portrait is a painting, so it shows a face without the consent or privacy questions that a modern photo of a living person would raise.

| File | Subject | Source and licence | Credit line |
|---|---|---|---|
| `coffee-beans.jpg` (1280×960) | Roasted coffee beans, close up | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Roasted_coffee_beans.jpg), public domain | "Roasted coffee beans" by MarkSweep, public domain, via Wikimedia Commons |
| `milky-way.jpg` (1280×848) | Milky Way over a wooden fence | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Milky_Way_Night_Sky_(Unsplash).jpg), CC0 | "Milky Way Night Sky" by Guillaume (Unsplash), CC0, via Wikimedia Commons |
| `antonello-portrait-of-a-man.jpg` (1280×1782) | Portrait of a man in a red cap, painted about 1475 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Antonello_da_Messina_-_Portrait_of_a_Man_-_National_Gallery_London.jpg); the painting is in the public domain, and the faithful photographic reproduction is PD-Art | Antonello da Messina, *Portrait of a Man* (about 1475; National Gallery, London, NG1141). The painting is in the public domain; faithful photographic reproduction via Wikimedia Commons (PD-Art). |

None of these licences requires attribution, but crediting the source is good practice.

## Measured results on these exact files

Three independently sealed messages per profile, each read back by a separate decoder process
given only the saved PNG and the passphrase. Subtle and Long use the MobileNetV3-Small profiles.

| Photo | Subtle: 79 B, ±2 levels | Long: 494 B, ±8 levels | Classic: 13 B, ±8 levels |
|---|---|---|---|
| Coffee beans | 3/3; 0 wrong bytes to correct; SSIM ≥ 0.983; encode ≤ 18 s | 3/3; 0 wrong bytes; SSIM ≥ 0.899; encode ≤ 27 s | 1/1 |
| Milky Way | 3/3; 0 wrong bytes; SSIM ≥ 0.989; encode ≤ 20 s | 3/3; 0 wrong bytes; SSIM ≥ 0.924; encode ≤ 32 s | 1/1 |
| Antonello portrait | 3/3; 0 wrong bytes; SSIM ≥ 0.976; encode ≤ 20 s | 3/3; 0 wrong bytes; SSIM ≥ 0.863; encode ≤ 31 s | 1/1 |

SSIM is structural similarity to the original; 1.0 means identical. "Wrong bytes" are the bytes
read back incorrectly before error correction. The raw records are in
`bench/results/holdout-mobilenet/` and `bench/results/holdout-legacy/`. The earlier SqueezeNet
results for Subtle (`sw-l2-c10x8b16p48`) and Long (`sw-l8-c10x8b40p64`, 302 B) are in
`bench/results/holdout-finalists/`.

These are the original covers, not marked images. To make verified marked fixtures (a readable
message, a difference image and the negative control) for the site, run the same process as
`tools/make_showcase.py` with these covers.

## Verified demo fixtures

`fixtures/<photo>/` holds, for each photo:

- `original.png`: the cover as the engine sees it (sRGB, pixels only). This is the negative control: it carries no message.
- `classic.png`, `subtle.png`, `long.png`: the same photo with a hidden message, one file per mode.
- `*-difference.png`: |marked − original| per channel, amplified so the cap maps to 192/255. That is ×24 for Classic and Long (cap 8) and ×96 for Subtle (cap 2). Label it with the multiplier.
- `fixtures.json`: the exact messages, byte counts, measured maximum change, the checks run and SHA-256 hashes.

Passphrase for all of them: `ghostframe public benchmark fixture`.

| Photo | Classic (13 B, cap 8) | Subtle (≤ 79 B, cap 2) | Long (≤ 494 B, cap 8) |
|---|---|---|---|
| Coffee beans | "Beans at six." | "The roaster on Via Lucca is ours. Order the dark blend and pay in cash." | Courier briefing, 488 B |
| Milky Way | "Eyes on Orion" | "Signal from the fence line at 02:00. Two flashes mean the road is clear." | Night-team orders, 480 B |
| Antonello portrait | "Trust no one." | "The man in the red cap knows the code. Meet him in Room 4 at closing time." | Gallery orders, 493 B |

The full Long texts are in each `fixtures.json`. Every fixture passed four checks with the public CLI, each in a fresh process:

- It decodes to the exact message with 1 and with 4 CPU threads.
- `original.png` exits 1 with no output.
- A wrong passphrase exits 1 with no output.

The saved pixels stay within the cap: the maximum measured change equals the cap in every file.

To check a fixture:

```sh
printf '%s' 'ghostframe public benchmark fixture' > pass.txt
ghostframe-png decode demo-photos/fixtures/milky-way/subtle.png --profile bb-mobilenet_v3_small-l2-b16p48 --passphrase-file pass.txt
ghostframe-png decode demo-photos/fixtures/milky-way/classic.png --profile legacy-v1 --passphrase-file pass.txt
```

The Long profile is `bb-mobilenet_v3_small-l8-b64p112`. Subtle and Long are read by MobileNetV3-Small, Classic by SqueezeNet 1.1. To regenerate the fixtures, delete the PNGs and run `python -m tools.make_showcase --demo`. A fresh salt makes the new files differ byte for byte from these.
