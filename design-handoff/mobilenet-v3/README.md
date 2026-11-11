# Design handoff: Ghostframe demo on the MobileNetV3 engine

Subtle and Long now use the MobileNetV3-Small profiles. Long grows from 302 B to 494 B, and
encodes are about 1.6× faster. Classic is unchanged. Evidence is in [docs/BENCHMARK.md](../../docs/BENCHMARK.md#backbone-comparison-mobilenetv3-small).

| File | For | What it is |
|---|---|---|
| [CLAUDE_DESIGN_PROMPT.md](CLAUDE_DESIGN_PROMPT.md) | Claude Design | Updates `Ghostframe v3.dc.html` to the new engine: data constants, copy (before → after), retuned embedding colour scale, checks |
| [CLAUDE_CODE_PROMPT.md](CLAUDE_CODE_PROMPT.md) | Claude Code | Builds the real site from the design: engine facts, architecture, the one engine change (progress callback), milestones, acceptance checks |
| [design-data.json](design-data.json) | both | Every number the page shows, in the shapes the page script uses. Generated, do not hand-edit |
| `reference/Ghostframe v3.dc.html`, `reference/support.js` | both | Snapshot of the design **before** this update (2026-11-11), read from the Claude Design project |

Fixtures and embedding data live where the design already imports them from:
- `demo-photos/fixtures/<photo>/{subtle,long}.png` and `*-difference.png`, regenerated with the
  new profiles, plus `fixtures.json`;
- `demo-photos/fixtures/EMBEDDINGS.md` and `embeddings/*.json`.

## Regenerate

```sh
# after deleting demo-photos/fixtures/*/{subtle,long}*.png
python -m tools.make_showcase --demo     # encode + verify the fixtures (fresh salt: new bytes)
python -m tools.dump_embeddings          # per-tile embeddings and scores
python -m tools.embeddings_md            # demo-photos/fixtures/EMBEDDINGS.md
python -m tools.design_data              # design-handoff/mobilenet-v3/design-data.json
```

`design-data.json` reads the benchmark records in `bench/results/`. These include
`holdout-mobilenet`, `stress-mobilenet`, `holdout640-mobilenet` and the `detect-*.json` files.
