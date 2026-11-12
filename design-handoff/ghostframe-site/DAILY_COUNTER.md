# Ghostframe: daily encode counter (9a)

Reference: `Ghostframe v3.dc.html`, section `#tool` ("Use your own photo"), at the top right. The chosen option is 9a in `Daily Limit Options.dc.html`.

## Placement
- On the right of the section header row, level with the h2 and intro text. Below it sits the existing "Prototype · server responses are simulated" tag (drop the tag in production if it no longer applies).
- The right column has `margin-left:auto`, so it stays flush right even when the header row wraps (760–1050 px). Its items align right.
- Below 760 px the column sits under the intro text with everything aligned left (`margin-left:0`, `align-items:flex-start`).

## Content
- Line 1, IBM Plex Mono 13px: "**{left}** / {limit} encodes left today". The number is weight 600; the rest is 500.
- A meter: 170 × 4px, radius 2, track `#e0dad3`. Fill width = left / limit and animates over 300ms (no animation under reduced motion).
- Line 2, Inter 11.5px, `#625c57`: "Shared by everyone · resets midnight UTC".

## States
| State | Condition | Number and line 1 colour | Meter fill | Line 2 |
|---|---|---|---|---|
| Normal | left > 10 | ink `rgba(18,16,14,0.96)` | blue `#3f648c` | Shared by everyone · resets midnight UTC |
| Low | 1–10 left | ink | ink | same |
| Closed | left = 0 | red `#9f3b3b` | red | Closed until midnight UTC |

- When it reaches 0, the existing "Encoding is closed for today" banner and the disabled Encode button take over. Don't add another message.
- The counter is a `role="status"` live region with `aria-live="polite"`, so changes are announced without moving focus.
- Only hiding a message counts against the limit. Reading never changes it.

## Data (backend)
- The counter needs a source: e.g. `GET /api/quota` → `{ "left": 38, "limit": 50, "resets_at": "2026-11-13T00:00:00Z" }`. Use the real limit from the server; don't hard-code 50.
- Fetch it when the section first scrolls into view. Refetch after each encode is accepted or refused, and whenever the tab becomes visible again.
- If the encode endpoint answers "site limit reached", set the count to 0 at once, even if the last fetch said otherwise.
- If the quota request fails, hide the counter. Don't show a guess.
- The number is the **site-wide** limit, shared by everyone. If a per-visitor limit is hit, keep using the existing "visitor limit" result. Don't change the counter's wording to "you".
- Confirm the reset time (midnight UTC) matches the server. Line 2 and the closed banner both state it.
