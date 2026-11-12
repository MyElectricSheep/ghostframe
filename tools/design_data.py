"""Export every number the demo design shows, in the shapes its page script uses.

    python -m tools.dump_embeddings && python -m tools.design_data
    # writes site/data/design-data.json

Sources: the demo fixtures (`demo-photos/fixtures/`), their embedding export, and the raw
benchmark records under `bench/results/`. Nothing here is typed in by hand except labels.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "demo-photos" / "fixtures"
RESULTS = ROOT / "bench" / "results"
OUT = ROOT / "site" / "data" / "design-data.json"

PHOTOS = {"antonello": ("antonello-portrait-of-a-man", "antonello_da_messina_portrai"),
          "coffee": ("coffee-beans", "coffee_beans"),
          "milky": ("milky-way", "milky_way")}
MODES = {
    "classic": dict(label="Classic", profile="legacy-v1", backbone="SqueezeNet 1.1", dim=512, cap=8, amp=24,
                    grid=[6, 5], bits_per_tile=16, status="verified", run="holdout-legacy",
                    summary_profile="legacy-v1-13B", ev_unit="held-out photos"),
    "subtle": dict(label="Subtle", profile="bb-mobilenet_v3_small-l2-b16p48", backbone="MobileNetV3-Small",
                   dim=576, cap=2, amp=96, grid=[10, 8], bits_per_tile=16, status="experimental",
                   run="holdout-mobilenet"),
    "long": dict(label="Long", profile="bb-mobilenet_v3_small-l8-b64p112", backbone="MobileNetV3-Small",
                 dim=576, cap=8, amp=24, grid=[10, 8], bits_per_tile=64, status="experimental",
                 run="holdout-mobilenet"),
}


def jsonl(path):
    return [json.loads(line) for line in path.open()]


def summary(run, profile):
    return next(r for r in json.loads((RESULTS / run / "summary.json").read_text()) if r["profile"] == profile)


def per_cover(run, profile, cover):
    """Held-out frames of one profile on one cover: read back, wrong bytes, SSIM, encode time."""
    decoded = {r["message"]: r for r in jsonl(RESULTS / run / "decode.jsonl")}
    rows = [e for e in jsonl(RESULTS / run / "encode.jsonl") if e["profile"] == profile and e["cover"] == cover]
    ok = sum(decoded.get(e["message"], {}).get("ok", False) for e in rows)
    wrong = [decoded[e["message"]].get("corrected_symbols") or 0 for e in rows if e["message"] in decoded]
    return dict(read_back=ok, frames=len(rows), max_wrong_bytes=max(wrong, default=0),
                min_ssim=round(min(e["ssim"] for e in rows), 3),
                max_encode_s=round(max(e["encode_s"] for e in rows)))


def main():
    out = dict(generated_by="python -m tools.design_data", modes={}, photos={}, fix={}, sum={}, heat={}, raw={},
               res={}, stress={}, small640={}, detect={})
    for key, mode in MODES.items():
        run = mode["run"]
        s = summary(run, mode.get("summary_profile", mode["profile"]))
        m = {k: v for k, v in mode.items() if k not in ("run", "summary_profile", "ev_unit")}
        m.update(bytes=s["payload"], ev=f"{s['success']} / {s['trials']}",
                 evUnit=mode.get("ev_unit", "held-out trials"), psnr=f"{s['median_psnr']:.1f} dB",
                 ssim=f"{s['median_ssim']:.3f}", median_encode_s=round(s["median_encode_s"]))
        out["modes"][key] = m
    for key, (folder, cover) in PHOTOS.items():
        entries = {e["encoded"].split(".")[0]: e for e in json.loads((FIXTURES / folder / "fixtures.json").read_text())}
        out["fix"][key] = {"dir": folder, **{mode: [e["recovered_message"], e["payload_bytes"],
                                                    e["changed_channel_fraction"]] for mode, e in entries.items()}}
        out["fix"][key]["encode_s_cli"] = {mode: e.get("encode_s_cli") for mode, e in entries.items()}
        record = json.loads((FIXTURES / "embeddings" / f"{folder}.json").read_text())["modes"]
        out["sum"][key], out["heat"][key] = {}, {}
        for mode, d in record.items():
            cos, shift = np.array(d["tile_cosine"]), np.array(d["tile_shift"])
            out["sum"][key][mode] = [d["cols"] * d["rows"], int(np.size(d["scores_marked"])),
                                     round(float(np.median(cos)), 3), round(float(cos.min()), 3),
                                     round(float(np.median(shift)), 3), int(sum(d["bits_flipped_per_tile"]))]
            out["heat"][key][mode] = np.round(cos.reshape(d["rows"], d["cols"]), 2).tolist()
        first = lambda mode, which: [round(v, 4) for v in record[mode][which][0][:12]]
        out["raw"][key] = dict(u10=first("subtle", "embeddings_original"), subtle=first("subtle", "embeddings_marked"),
                               long=first("long", "embeddings_marked"), u6=first("classic", "embeddings_original"),
                               classic=first("classic", "embeddings_marked"))
        out["res"][key] = {mode: per_cover(MODES[mode]["run"], MODES[mode]["profile"], cover)
                           for mode in ("subtle", "long")}
    for mode in ("subtle", "long"):
        s = summary("stress-mobilenet", MODES[mode]["profile"])
        out["stress"][mode] = dict(encoded=s["success"], of=s["trials"], failures=s["failures"])
        small = RESULTS / "holdout640-mobilenet" / "summary.json"
        if small.exists():
            s = summary("holdout640-mobilenet", MODES[mode]["profile"])
            out["small640"][mode] = dict(read_back=s["success"], of=s["trials"], failures=s["failures"],
                                         median_encode_s=round(s["median_encode_s"]))
        detect = RESULTS / f"detect-{MODES[mode]['profile']}.json"
        if detect.exists():
            d = json.loads(detect.read_text())
            out["detect"][mode] = dict(auc=d["auc"], pairs=d["pairs"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
