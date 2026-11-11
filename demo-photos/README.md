# Demo photos

Cover photos for the demo website. All three come from the preregistered held-out benchmark set
(`bench/manifest-v1.json`). They are the exact files that were tested, byte for byte (the SHA-256
hashes match the manifest), and they are free to use. The portrait is a painting, so it shows a face without the consent or privacy questions that a modern photo of a living person would raise.

| File | Subject | Source and licence | Credit line |
|---|---|---|---|
| `coffee-beans.jpg` (1280×960) | Roasted coffee beans, close up | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Roasted_coffee_beans.jpg), public domain | "Roasted coffee beans" by MarkSweep, public domain, via Wikimedia Commons |
| `milky-way.jpg` (1280×848) | Milky Way over a wooden fence | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Milky_Way_Night_Sky_(Unsplash).jpg), CC0 | "Milky Way Night Sky" by Guillaume (Unsplash), CC0, via Wikimedia Commons |
| `antonello-portrait-of-a-man.jpg` (1280×1782) | Portrait of a man in a red cap, painted about 1475 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Antonello_da_Messina_-_Portrait_of_a_Man_-_National_Gallery_London.jpg), public domain (the National Gallery, London) | Antonello da Messina, *Portrait of a Man* (about 1475), The National Gallery, London, public domain, via Wikimedia Commons |

Neither licence requires attribution, but crediting the source is good practice.

## Measured results on these exact files

Three independently sealed messages per profile, each read back by a separate decoder process
given only the saved PNG and the passphrase.

| Photo | Subtle: 79 B, ±2 levels | Long: 302 B, ±8 levels | Classic: 13 B, ±8 levels |
|---|---|---|---|
| Coffee beans | 3/3; 0 wrong bytes to correct; SSIM ≥ 0.982; encode ≤ 22 s | 3/3; 0 wrong bytes; SSIM ≥ 0.923 | 1/1 |
| Milky Way | 3/3; ≤ 4 wrong bytes (budget 24); SSIM ≥ 0.989 | 3/3; 0 wrong bytes; SSIM ≥ 0.930 | 1/1 |
| Antonello portrait | 3/3; 0 wrong bytes; SSIM ≥ 0.975; encode ≤ 24 s | 3/3; 0 wrong bytes; SSIM ≥ 0.878 | 1/1 |

SSIM is structural similarity to the original; 1.0 means identical. "Wrong bytes" are the bytes
read back incorrectly before error correction. The raw records are in
`bench/results/holdout-finalists/` and `bench/results/holdout-legacy/`.

These are the original covers, not marked images. To make verified marked fixtures (a readable
message, a difference image and the negative control) for the site, run the same process as
`tools/make_showcase.py` with these covers.
