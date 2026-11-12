# Credits

The code is MIT-licensed (see [LICENSE](LICENSE)). The images, fonts and model weights below are
not covered by that licence; each keeps its own.

## Photographs

| File | Source | Licence |
|---|---|---|
| `demo-photos/coffee-beans.jpg` | "Roasted coffee beans" by MarkSweep, [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Roasted_coffee_beans.jpg) | Public domain |
| `demo-photos/milky-way.jpg` | "Milky Way Night Sky" by Guillaume (Unsplash), [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Milky_Way_Night_Sky_(Unsplash).jpg) | CC0 |
| `demo-photos/antonello-portrait-of-a-man.jpg` | Antonello da Messina, *Portrait of a Man* (about 1475), The National Gallery, London, [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Antonello_da_Messina_-_Portrait_of_a_Man_-_National_Gallery_London.jpg) | Public domain |
| `site/public/assets/station-wellington.jpg` | "Wellington Railway Station, NSW Platform" by Abesty, [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Wellington_Railway_Station,_NSW_Platform.jpg), resized to 1920 px | CC0 |
| `examples/*` | Matplotlib and scikit-learn sample images; see [examples/ATTRIBUTION.md](examples/ATTRIBUTION.md) | Public domain and CC BY 2.0 |

The marked PNGs, difference images and thumbnails derived from these photos record Ghostframe's
pixel changes and keep the licence of their source photo. The experiments also load sample images
bundled with scikit-image; see its [data credits](https://scikit-image.org/docs/stable/api/skimage.data.html).

## Fonts (demo site)

- IBM Plex Mono, © IBM Corp., SIL Open Font License 1.1. Two subsets are committed in
  `site/src/fonts/`, next to the licence text (`OFL-IBM-Plex-Mono.txt`).
- Inter, © The Inter Project Authors, SIL Open Font License 1.1, installed from npm
  (`@fontsource/inter`).

## Model weights

The pretrained ImageNet weights for SqueezeNet 1.1, MobileNetV3-Small, ResNet-18,
EfficientNet-B0 and ConvNeXt-Tiny are not included in this repository. They are downloaded on
first use from `download.pytorch.org` and checked against pinned SHA-256 hashes. The torchvision
project publishes them; its code is BSD-3-Clause, it makes no separate licence statement for the
weights, and the ImageNet dataset they were trained on has its own terms.
