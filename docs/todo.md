# To do

What is left before the jam build ships, in the order it unblocks the rest. The PR that does an
item removes it; what was done is in git and in [`decisions.md`](decisions.md). Sections keep
their numbers, which the decision log cites. Ideas for after the jam go in [`ideas.md`](ideas.md).

## 0. What the player sees first, and how they move around (D-028)

- [ ] A passkey for each level: a word typed in Chapters (the map's place since D-054) opens
      that level at once, so a player who comes back does not win the ones before it again. Words of our own, not song titles
      (French law protects an original title, CPI L112-4). Nothing is stored, so this is not
      saving; it amends D-035 ("a level opens once the one before it is won"): a decision first.
      - Where does the player learn a level's word: on the banner after a win, in Chapters?
      - No text input exists yet. Does a phone's keyboard come up for a pygbag canvas?
      - Matched in upper case, ASCII only? One word per level, or per chapter?

## 2. The levels themselves

The chapter is Fear, Aggression, Love, In the shadow (D-074); the first two lead, the others
only hint.

- [ ] Tutorial 3, ÷2 on one side (orbits), the brief's level 3: a level of its own, or Love's
      place? Its objective is to be chosen: stay within a ring round the light for T s, or
      circle it N times.
- [ ] The real level: to design, with a winner pinned with margin (D-004).

## 5. Ship

- [ ] `DEV_VIEW = False` for the build that is uploaded.
- [ ] `pygbag --build --archive game`, upload to itch.io.
- [ ] Check in Chrome and in Safari. Safari has never been checked: the keys (Cmd+Y opens its
      History window), the fonts, the canvas.

## 6. Small things

- [ ] Click-to-inspect: draw the swimmer's steering vector (brief §1).
- [ ] F2's W (waveform) clashes with the editor's Wire (D-021).
- [ ] `eye_rates` timed natively only; measure it under WASM (D-019).
- [ ] The names: itch.io search, Google and TMview (classes 9 and 41) to check by hand (D-006).
- [ ] In headless Chrome the first click after a key press is lost: on Fear's first drag step,
      Skip takes two clicks there. Check it in a real browser (seen 2026-10-02).

## 7. The editor's hand, for a finger as for a mouse

From Camille's notes (`ebc4abb`). The Wheel (D-068, D-069) does the rest: a click on a cell
shows what can be done there, a click on a part arms Wire, a drag moves a part, or draws a
wire with Wire chosen (D-072).

- [ ] Drag a part off the body, or onto Parts, to delete it.
      - How far must a finger move before a tap becomes a drag?
- [ ] Touch: no hover and no keys. The tooltips (D-025) and L, R, Space, Esc and 0 need an
      on-screen form. One gesture stays one undo step (D-027).
      - The canvas is 960 × 640 px: on a phone a 40 px hex is about 16 px wide in portrait and
        24 px in landscape, where a finger wants about 44. Landscape only, larger hexes?
      - Under pygbag, do touches arrive as mouse events or as FINGERDOWN only? Try on a phone
        first.
- [ ] Put a part on a cell a wire crosses, and have the wire route round it, as a wire drawn
      after the part already does. Today `Board.place` refuses ("a wire runs here"). This
      reopens D-007 and D-011 (routes never change on their own), so it needs a decision first.

## 8. An activity bar, drawers and environments (D-051)

Mockups of every drawer, drawn with the game's own palette and renders, are in this session's
artifacts ("Nektoids Activity Bar", round 3). It replaces the menu, the palette, the run view's
column and the full-screen map (gone, D-054).

The rule: in the Editor the main screen shows the board, and the Run preview while Diagnostic
is open (D-069); in the Run it shows the level. Drawers never take the main screen.

- [ ] Sound and Music in Settings, once there is sound (D-054).
- [ ] Parts as the encyclopedia: a row opens into its entry, in the drawer; today the entry
      opens in a box beside it.

## 9. A board as text (its own PR)

- [ ] A board as a short line of ASCII to copy, paste, keep in a text file and open again: the
      board of D-024 packed into bits and spelled out. Its language is a decision first.
      - Letters (base 32, like a licence key) or words from a list (2048 words, 11 bits each)?
      - Length, roughly: six parts and six wires with their paths kept exactly come to under
        200 bits, about 35 letters or 17 words; less if the paths are drawn again in wire order,
        which gives the same routes unless Move or Delete was used (D-024).
      - A check against typing mistakes, Shannon-like: redundant check symbols, so a mistyped
        line is refused (or even corrected) rather than loading another board. A version mark.
      - Copy and paste between the canvas and the page: does pygbag reach the clipboard? Wait
        and see on the web build.
      - The same mechanism as the level passkeys (§0): a word that brings a state back.
