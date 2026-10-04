# To do

What is left before the jam build ships, in the order it unblocks the rest. The PR that does an
item removes it; what was done is in git and in [`decisions.md`](decisions.md). Sections keep
their numbers, which the decision log cites. Ideas for after the jam go in [`ideas.md`](ideas.md).

## 2. The levels themselves

The chapter is Fear, Aggression, Love, Orbit, Shadows, Greed, Patience (D-097); Fear opens on an
introduction (D-079), and the first five levels have their hints (D-078).

- [ ] Greed and Patience, the real level, as D-097 designed them, each with its winner pinned
      with margin (D-004).

## 5. Ship

- [ ] `DEV_VIEW = False` for the build that is uploaded.
- [ ] `pygbag --build --archive game`, upload to itch.io.
- [ ] Check in Chrome and in Safari. Safari has never been checked: the keys (Cmd+Y opens its
      History window), the fonts, the canvas.

## 6. Small things

- [ ] `eye_rates` timed natively only; measure it under WASM (D-019).
- [ ] The names: itch.io search, Google and TMview (classes 9 and 41) to check by hand (D-006).
- [ ] In headless Chrome the first click after a key press is lost: on Fear's first drag step,
      Skip takes two clicks there. Check it in a real browser (seen 2026-10-02).

## 7. The editor's hand, for a finger as for a mouse

From Camille's notes (`ebc4abb`). The Wheel (D-068, D-069) does the rest: a click on a cell
shows what can be done there, a click on a part arms Wire, a drag moves a part, or draws a
wire with Wire chosen (D-072).

- [ ] Touch: no hover and no keys. The tooltips (D-025) and L, R, Space, Esc and 0 need an
      on-screen form. One gesture stays one undo step (D-027).
      - Does a phone's keyboard come up for Chapters' passkey field (D-075)? If not, the field
        needs letters of its own on screen.
      - The canvas is 960 × 640 px: on a phone a 40 px hex is about 16 px wide in portrait and
        24 px in landscape, where a finger wants about 44. Landscape only, larger hexes?
      - Under pygbag, do touches arrive as mouse events or as FINGERDOWN only? Try on a phone
        first.
      - How far must a finger move before a tap becomes a drag? Today a press becomes a drag
        once the pointer leaves the part's cell (D-085): enough for a finger on large hexes?

## 8. An activity bar, drawers and environments (D-051)

Mockups of every drawer, drawn with the game's own palette and renders, are in this session's
artifacts ("Nektoids Activity Bar", round 3). It replaces the menu, the palette, the run view's
column and the full-screen map (gone, D-054).

The rule: in the Editor the main screen shows the board, and the Run preview while Diagnostic
is open (D-069); in the Run it shows the level. Drawers never take the main screen.

- [ ] Sound and Music in Settings, once there is sound (D-054).
- [ ] Parts as the encyclopedia: a row opens into its entry, in the drawer; today the entry
      opens in a box beside it.
