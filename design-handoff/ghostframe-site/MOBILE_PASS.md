# Ghostframe: mobile pass (below 760 px)

Reference: `Ghostframe v3.dc.html`. The layouts below are active when `window.innerWidth < 760` (`narrow` in the prototype). At 760 px and wider, nothing changes. `Mobile Options.dc.html` shows the chosen options as 8a, 8f and 8h, next to the ones that were rejected.

## 1. Header: burger and full-screen menu (8a)
- Hide the row of nav links. Logo, "Ghostframe" and the "engineering experiment" pill stay. Add a 44 × 44 burger button at the right (`aria-expanded`, `aria-controls="gf-menu"`, label "Open menu" / "Close menu"). While open, the icon becomes an X.
- The open menu fills the screen below the sticky header (`#gf-menu`, background `#f6f4f1`). It fades in and moves 8px down over 220ms; under reduced motion it appears instantly.
- Links in page order, each a row with a mono number in blue, a 24px/700 title and a 13.5px grey description:
  01 Try it (Spot the difference in three photos) → `#try`
  02 How it works (Five steps, each animated) → `#how`
  03 Hide a message (In your own photo) → `#tool`, Hide tab
  04 Read a message (From a PNG you were sent) → `#tool`, Read tab
  05 Limits and evidence (What it can’t do, and the numbers) → `#limits`
- Under the links: "Ghostframe is an engineering experiment by Ben Paget." (links to https://electricsheep.id).
- Tapping a link closes the menu, then navigates. Lock body scroll while the menu is open. Escape closes it and returns focus to the burger. Close it automatically when the window gets wider than 760.

## 2. Try it: summary line, view switch and bottom sheet (8f)
- Hide the left control column (cover / mode / view lists and mode tooltips).
- Above the image stage: one full-width button (min-height 56) with the current photo's thumbnail (40 × 40), "{Photo} · {Mode}" (14.5/600), "up to {max} B · ≤ {cap}/255" in mono 11px and "Change" in blue on the right. It opens the sheet.
- Directly under the image stage: a three-part segmented control, Compare · Difference · Model (`role="radiogroup"`, each option at least 44px high, the selected one white with a light shadow). Each option's accessible name is the full label (Original vs encoded / Amplified difference / What the model sees).
- Bottom sheet (`role="dialog"`, "Photo and mode"): fixed to the bottom, top corners 18px, max-height 88vh, scrolls inside. It slides up over 280ms over a scrim of `rgba(18,16,14,0.38)`; tapping the scrim closes it. Contents:
  - "01 · photo": three thumbnail buttons in a row (54px-high image + label).
  - "02 · mode · how much the message can hold, and how much the pixels may change": a radio list, one row per mode with a radio dot, the label, "up to {max} B · ≤ {cap}/255" on the right and the full mode tooltip text below. This replaces the hover tooltip on phones.
  - A full-width "Show this photo" button that closes the sheet.
- A choice made in the sheet updates the stage at once. Focus moves into the sheet when it opens and back to the summary button when it closes.

## 3. How it works: swipe cards (8h)
- Hide the animation figure and the vertical step list. Technical detail stays and loses its 46px left indent.
- Show a horizontal scroll-snap row (`scroll-snap-type:x mandatory`), full-bleed, with 16px side padding. Card width is `min(340px, 100vw − 56px)` and the gap is 12px, so the next card peeks in.
- Each card: a dark frame with the step label and timer, an animation area (4:3) and below it "{sender|recipient} · 0N / 05", the title (16.5/700) and the description (14/1.5). The active card has a blue-tinted border.
- Only the active card runs the real step animation and its Replay button. Inactive cards show their step number and "Plays when this card is in view".
- The active step is driven by scroll position: when a card snaps into place, its animation starts. Under the row, numbered dots 01–05 (40 × 40, the active one blue) scroll to their card and play it.
- So the last cards can snap to the start, add a trailing spacer after the last card, `calc(100% − cardWidth − 44px)`. Also treat a scroll position at the very end as step 05.
- Under the dots: "Swipe for the next step. Illustration. The message, grid sizes and pixel cap are real; the numbers inside the model are simplified."
- Autoplay on first view, as on desktop. With reduced motion, show the final frame with no animation.
