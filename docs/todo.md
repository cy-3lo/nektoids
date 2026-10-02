# To do

What is left before the jam build ships, in the order it unblocks the rest. The PR that does an
item removes it; what was done is in git and in [`decisions.md`](decisions.md). Sections keep
their numbers, which the decision log cites. Ideas for after the jam go in [`ideas.md`](ideas.md).

## 0. What the player sees first, and how they move around (D-028)

- [ ] A passkey for each level: a word typed on the map opens that level at once, so a player
      who comes back does not win the ones before it again. Words of our own, not song titles
      (French law protects an original title, CPI L112-4). Nothing is stored, so this is not
      saving; it amends D-035 ("a level opens once the one before it is won"): a decision first.
      - Where does the player learn a level's word: on the banner after a win, on the map?
      - No text input exists yet. Does a phone's keyboard come up for a pygbag canvas?
      - Matched in upper case, ASCII only? One word per level, or per chapter?

## 2. The levels themselves

- [ ] Tutorial 2, aggression (crossed: charges the light). Visit the light.
- [ ] Tutorial 3, ÷2 on one side (orbits). Its objective is to be chosen: stay within a ring
      round the light for T s, or circle it N times.
- [ ] The real level: to design, with a winner pinned with margin (D-004).

## 5. Ship

- [ ] `DEV_VIEW = False` for the build that is uploaded.
- [ ] `pygbag --build --archive game`, upload to itch.io.
- [ ] Check in Chrome and in Safari. Safari has never been checked: the keys (Cmd+Y opens its
      History window), the fonts, the canvas.

## 6. Small things

- [ ] Click-to-inspect: draw the swimmer's steering vector (brief §1).
- [ ] F2's W (waveform) clashes with the editor's Wire (D-021).
- [ ] `draw.py` calls `scene._wire_start()`, a private method.
- [ ] `eye_rates` timed natively only; measure it under WASM (D-019).
- [ ] The names: itch.io search, Google and TMview (classes 9 and 41) to check by hand (D-006).

## 7. The editor's hand: a ring of icons round a cell, for a finger as for a mouse

From Camille's notes (`ebc4abb`), then a design for touch screens.

- [ ] Tap an empty cell: a ring of icons round it, in its six directions, offers the parts the
      level hands out; tap one and it is placed. Tap a placed part: the ring offers turn left,
      turn right and wire (D-025's buttons, brought to the cell). Replaces the Add tool and
      changes D-025 and D-031: a decision first.
      - More than six kinds: the free board hands out all seven. A second ring, a "more" slot?
      - Could the six slots round an eye or a thruster be its six facings (D-009), one tap to
        point it rather than turns of 60°? Then where do Wire and Delete go?
      - The ring covers the six neighbours, which may hold parts; at the zone's or the
        screen's edge it is cut off.
- [ ] Wire is the default: a tap on a part opens its ring with Wire chosen, so a tap on a second
      part wires the two, either way round (D-026). While wiring, the parts that cannot take
      the wire are dimmed or red.
      - Only the parts whose kinds refuse, or also the ones no free path reaches?
- [ ] Drag a part to move it (D-011), with no Move tool; drag it off the body or onto the
      palette to delete it.
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
column and the full-screen map.

- [ ] One row style for every drawer: icon, name, (i), then a count, a key, a lock or a tick.
- [ ] An activity bar down the left edge, one icon per drawer, named when the mouse rests on it;
      the open one lighter, an accent bar on its edge. One drawer open at a time, pushing the
      board aside; folded by its icon again or the arrow on its edge.
      - Top, editor: Parts (puzzle-piece; also the parts' encyclopedia, a row opening into its
        entry), Tools (screwdriver-wrench), Files (floppy-disk), Sense (stethoscope), Navigate
        (compass). Top, sim: Objectives (list-check), Inside (magnifying-glass), Score (trophy),
        Navigate.
      - Foot, both: Settings (gear), Chapters (map; not "Map"), then the accented switch: Run
        (play) in the editor, back to the editor (diagram-project) in the sim.
      - Chapters replaces the full-screen map. Settings: fast forward's speed, key hints,
        tooltips' delay, Fear's tutorial again; Sound and Music once there is sound. No palette.
      - The sim's controls (play, a step, fast forward, the timeline) in a bar under the arena.
- [ ] Environments as tabs over the content: Editor and Sim (a Builder later, no tab until then).
      Switched by a tab, or by the accented switch.
- [ ] The circuit, one drawing for Sense (editor) and Inside (sim): parts shaded by their rate,
      beads on the wires, no numbers, a level meter by each eye and thruster in accent 1, the
      colour of their faces. A swap button on the drawer exchanges the drawer's content and the
      main screen: in the editor, circuit big and the probe's map small, or the level big with
      the probe; in the sim, the arena big and the circuit small, or the other way round.
- [ ] The probe: the swimmer put anywhere on the level and turned; the circuit is the board as
      it would run there; nothing run, nothing scored. A Board / Circuit switch over the editor.
- [ ] This session's winning boards kept in memory, one for each point of the score; a click
      puts one back on the board, the board left going to Undo. Files can wait: not needed yet.
- [ ] Fear's tutorial rewritten for the bar: it lights drawers and icons, no more the menu and
      the palette (D-039).

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
