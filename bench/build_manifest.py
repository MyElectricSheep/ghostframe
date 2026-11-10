"""Fetch benchmark covers and write a versioned manifest with hashes and splits.

Splits are by source image. Screening and tuning covers come from packages already
installed with the pinned dependencies; held-out covers are downloaded (Wikimedia
Commons public-domain/CC0 files) and never used for tuning or calibration.
Stress covers are synthetic and generated deterministically here.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COVERS = ROOT / "data" / "covers"
MANIFEST = ROOT / "bench" / "manifest-v1.json"
AGENT = "ghostframe-research/0.1 (benchmark fetch)"

SKIMAGE = Path(__import__("skimage").__file__).parent / "data"
SKIMAGE_LICENSE = "scikit-image bundled sample data; see https://scikit-image.org/docs/stable/api/skimage.data.html"

LOCAL = [
    # (id, split, source path, content, attribution)
    ("astronaut", "screen", SKIMAGE / "astronaut.png", "portrait", "NASA, public domain (scikit-image)"),
    ("chelsea", "screen", SKIMAGE / "chelsea.png", "animal/texture", "Stefan van der Walt, CC0 (scikit-image)"),
    ("coffee", "screen", SKIMAGE / "coffee.png", "object", "Rachel Michetti, CC0 (scikit-image)"),
    ("rocket", "screen", SKIMAGE / "rocket.jpg", "outdoor, JPEG-origin", "SpaceX, CC0 (scikit-image)"),
    ("motorcycle_right", "screen", SKIMAGE / "motorcycle_right.png", "object, legacy capacity screen", "Middlebury stereo (scikit-image)"),
    ("ihc", "screen", SKIMAGE / "ihc.png", "microscopy, legacy capacity screen", "scikit-image"),
    ("hubble", "tune", SKIMAGE / "hubble_deep_field.jpg", "astronomy, low light", "NASA, public domain (scikit-image)"),
    ("retina", "tune", SKIMAGE / "retina.jpg", "medical, dark surround", "scikit-image"),
    ("cell", "tune", SKIMAGE / "cell.png", "grayscale microscopy, legacy capacity screen", "scikit-image"),
    ("grace_hopper", "tune", ROOT / "examples" / "grace_hopper.jpg", "portrait, showcase cover", "examples/ATTRIBUTION.md"),
    ("china", "tune", ROOT / "examples" / "china.jpg", "outdoor", "examples/ATTRIBUTION.md"),
    ("china_sky", "tune", ROOT / "examples" / "china-sky.png", "flat sky, crop of china (same split)", "examples/ATTRIBUTION.md"),
    ("flower", "tune", ROOT / "examples" / "flower.jpg", "close-up, ECC showcase cover", "examples/ATTRIBUTION.md"),
    ("text", "stress", SKIMAGE / "text.png", "line art / text, grayscale", "scikit-image"),
    ("page", "stress", SKIMAGE / "page.png", "scanned page, grayscale", "scikit-image"),
]

# The Kodak suite was planned for the held-out split, but r0k.us now serves a bot
# challenge (HTTP 401) after the first file, so every held-out cover comes from Commons.

COMMONS = [
    ("apple_cake", "File:Apple cake with vanilla ice cream 2.jpg", "food"),
    ("big_mac", "File:Big Mac hamburger.jpg", "food, saturated"),
    ("cardamom_buns", "File:Cardamom buns.jpg", "food"),
    ("fungi_basket", "File:Edible fungi in basket 2012 G1.jpg", "food, texture"),
    ("lark_buns", "File:Lob Жаворонки 95.jpg", "food"),
    ("chocolate_cake", "File:Piece of chocolate cake on a white plate decorated with chocolate sauce.jpg", "food, bright"),
    ("carrots", "File:Preparing and slicing carrots.jpg", "food, saturated"),
    ("coffee_beans", "File:Roasted coffee beans.jpg", "texture, dark"),
    ("city_night", "File:City Night Lights (Unsplash).jpg", "low light"),
    ("milky_way", "File:Milky Way Night Sky (Unsplash).jpg", "low light, noise"),
    ("iss_border_night", "File:City Lights at Night along the France-Italy Border.JPG", "low light, orbital"),
    ("met_portrait", "File:-Vignetted portrait, woman holding a baby- MET DP113912.jpg", "historic portrait"),
    ("liljefors_fox", "File:Bruno Liljefors - Fox in forest landscape 1926.jpg", "painting, texture"),
    ("honthorst", "File:Der Zahnbrecher von Gerard Honthorst (BM 1852,1009.436).jpg", "dark painting"),
    # Second batch, chosen by query (first PD/CC0 JPEG hits, near-duplicates removed).
    ("portrait_of_a_man_said_to_be", 'File:Portrait of a Man, Said to be Christopher Columbus.jpg', "portrait photograph man"),
    ("antonello_da_messina_portrai", 'File:Antonello da Messina - Portrait of a Man - National Gallery London.jpg', "portrait photograph man"),
    ("2009_photo_of_summer_in_the", 'File:2009 - photo of Summer in the city with hollyhock flowers in the street - free download image of Amsterdam city - street photography by Fons Heijnsbroek.jpg', "street photography"),
    ("photo_of_two_young_women_pas", 'File:Photo of two young women passing a construction fence with a writing of Amsterdam street artist Laser 3.14 - free image of street photography Amsterdam by Fons Heijnsbroek.jpg', "street photography"),
    ("utah_dunes_landscape_west_de", 'File:Utah Dunes Landscape - West Desert District.jpg', "mountain landscape snow"),
    ("ky_to_kan_school_mountain_la", 'File:Kyōto Kanō School - Mountain Landscape.jpg', "mountain landscape snow"),
    ("william_adolphe_bouguereau_1", 'File:William-Adolphe Bouguereau (1825-1905) - The Wave (1896).jpg', "beach sea waves"),
    ("waves_in_sea_jpg", 'File:Waves in sea.jpg', "beach sea waves"),
    ("restaurant_amigos_de_acapulc", 'File:Restaurant Amigos de Acapulco (window), Chico.jpg', "architecture building facade"),
    ("boulevard_hotel_neon_sign_mi", 'File:Boulevard Hotel (Neon sign), Miami Beach.jpg', "architecture building facade"),
    ("the_blue_bird_press_photogra", 'File:The Blue Bird press photograph, front.jpg', "bird photograph"),
    ("dog_met_dp233970_jpg", 'File:-Dog- MET DP233970.jpg', "dog photograph"),
    ("photograph_of_buddy_the_dog", 'File:Photograph of Buddy the Dog - DPLA - 590d53609e2fd756d354216a77abb1eb.jpg', "dog photograph"),
    ("fly_insect_macro_jpg", 'File:Fly insect macro.jpg', "insect macro"),
    ("insect_macro_36301512526_jpg", 'File:Insect macro (36301512526).jpg', "insect macro"),
    ("chromis_reef_fish_and_stagho", 'File:Chromis reef fish and staghorn coral underwater scenic.jpg', "underwater fish reef"),
    ("underwater_photo_of_coral_re", 'File:Underwater photo of coral reef.jpg', "underwater fish reef"),
    ("aerial_view_of_farmland_cont", 'File:AERIAL VIEW OF FARMLAND CONTOURS - NARA - 547349.jpg', "aerial photograph farmland"),
    ("aerial_photograph_of_farmlan", 'File:AERIAL PHOTOGRAPH OF FARMLAND WITHIN A 15-MILE RADIUS OF NEW ULM, MINNESOTA, A COUNTY SEAT TRADING CENTER OF 13,000... - NARA - 558414.jpg', "aerial photograph farmland"),
    ("french_marigold_garden_2009", 'File:French marigold garden 2009 G1.jpg', "flowers garden photograph"),
    ("pasillo_de_la_biblioteca_vas", 'File:Pasillo de la Biblioteca Vasconcelos.jpg', "library interior"),
    ("holsteiner_ufer_in_berlin_on", 'File:Holsteiner Ufer in Berlin on 2026-05-13.jpg', "bicycle street"),
    ("orange_fabric_textile_cloth", 'File:Orange fabric textile cloth texture.jpg', "fabric texture"),
    ("ravi_shankar_charcoal_pencil", 'File:Ravi Shankar - charcoal pencil sketch.jpg', "pencil drawing sketch"),
    ("carl_gustav_carus_morning_fo", 'File:Carl Gustav Carus - Morning Fog - WGA04520.jpg', "fog morning"),
    ("train_station_with_train_and", 'File:Train station with train and coal depot by Gustave Le Gray1.jpg', "train station"),
    ("john_frederick_tayler_a_frui", 'File:John Frederick Tayler - A Fruit Stall in a Market - B1975.4.952 - Yale Center for British Art.jpg', "market fruit stall"),
]


def fetch(url, path):
    # curl, because r0k.us answers urllib with 401 but serves curl normally.
    if not path.exists():
        subprocess.run(["curl", "-sfL", "--max-time", "120", "-A", AGENT, "-o", str(path), url], check=True)
    return path


def commons_info(titles):
    """One batched API call (Commons rate-limits per-title lookups)."""
    query = urllib.parse.urlencode(dict(
        action="query", format="json", titles="|".join(titles), prop="imageinfo",
        iiprop="url|sha1|extmetadata", iiurlwidth=1280, iiextmetadatafilter="LicenseShortName|Artist"))
    request = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{query}", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)["query"]
    alias = {item["to"]: item["from"] for item in result.get("normalized", [])}
    info = {}
    for page in result["pages"].values():
        image, meta = page["imageinfo"][0], page["imageinfo"][0]["extmetadata"]
        info[alias.get(page["title"], page["title"])] = (
            image["thumburl"], image["descriptionurl"], meta["LicenseShortName"]["value"], meta.get("Artist", {}).get("value", ""))
    return info


def synthetic():
    rng = np.random.default_rng(20261110)
    yield "flat_gray", np.full((384, 512, 3), 128, np.uint8), "flat mid-gray"
    yield "flat_white", np.full((384, 512, 3), 255, np.uint8), "saturated white"
    yield "flat_black", np.zeros((384, 512, 3), np.uint8), "saturated black"
    bars = np.zeros((384, 512, 3), np.uint8)
    for i, colour in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255), (255, 255, 255), (0, 0, 0)]):
        bars[:, i * 64:(i + 1) * 64] = colour
    yield "colour_bars", bars, "saturated primaries"
    yield "noise_odd", rng.integers(0, 256, (333, 517, 3), np.uint8), "uniform noise, odd dimensions"
    gradient = np.linspace(0, 255, 640)[None, :, None].repeat(160, 0).repeat(3, 2)
    yield "wide_gradient", gradient.round().astype(np.uint8), "4:1 aspect gradient"
    yield "minimum_160x128", rng.integers(96, 160, (128, 160, 3), np.uint8), "smallest size for a 10x8 grid of 16-px tiles"


def main():
    COVERS.mkdir(parents=True, exist_ok=True)
    entries = []
    for cid, split, source, content, attribution in LOCAL:
        path = COVERS / f"{cid}{source.suffix}"
        shutil.copyfile(source, path)
        entries.append(dict(id=cid, split=split, file=path.name, source=str(source.relative_to(source.parents[1])),
                            content=content, attribution=attribution, license=SKIMAGE_LICENSE if "scikit" in attribution else attribution))
    info = commons_info([title for _, title, _ in COMMONS])
    for cid, title, content in COMMONS:
        thumb, page, license_name, artist = info[title]
        time.sleep(1)
        path = fetch(thumb, COVERS / f"{cid}.jpg")
        entries.append(dict(id=cid, split="holdout", file=path.name, source=thumb, page=page, content=content + ", JPEG-origin",
                            attribution=" ".join(artist.replace("<", " <").split())[:200], license=license_name))
    for cid, array, content in synthetic():
        path = COVERS / f"{cid}.png"
        Image.fromarray(array).save(path)
        entries.append(dict(id=cid, split="stress", file=path.name, source="bench/build_manifest.py synthetic()",
                            content=content, attribution="generated", license="CC0"))
    for entry in entries:
        path = COVERS / entry["file"]
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as image:
            entry["size"] = list(image.size)
            entry["mode"] = image.mode
    MANIFEST.write_text(json.dumps(dict(version=1, covers_dir="data/covers", covers=entries), indent=1, ensure_ascii=False) + "\n")
    counts = {}
    for entry in entries:
        counts[entry["split"]] = counts.get(entry["split"], 0) + 1
    print(counts, file=sys.stderr)


if __name__ == "__main__":
    main()
