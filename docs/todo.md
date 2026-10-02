# To do

What is left before the jam build ships, in the order it unblocks the rest. Tick an item in the
PR that does it. Ideas for after the jam go in [`ideas.md`](ideas.md), decisions in
[`decisions.md`](decisions.md).

## 0. What the player sees first, and how they move around (D-028)

- [x] Open on Tutorial 1's board under a title card ("Nektoids — wire the eyes to the
      thrusters, then Run"), gone at the first click; a Map button from the start.
- [x] A screen router in `main.py`: map, level (edit and run), sandbox, end screen. A pure state
      machine, tested headless; F2, F3 and F4 stay developer tools behind `DEV_VIEW`.
- [x] The map: one route, light (three tutorials, then the real level), and the sandbox.
      Levels open one after the other.
- [x] An explanation for each part (sensor, operator, actuator): clicked, it opens a small box
      next to it that says what it does; another click or any key closes it. To settle: which
      click opens it, since a click on a part already wires, moves, turns or deletes it (in the
      menu, a click on its row that does not pick it up; on the board, the Add tool, or a ?).
- [x] Each level says what it asks when it opens: its objective in a line or two, before any
      wiring (D-042).
- [x] Make it plain that an eye senses through its flat face (D-020): drawn in its accent,
      and a thruster's back in the other (D-047).
- [ ] A passkey for each level: a word typed on the map opens that level at once, so a player
      who comes back does not win the ones before it again. Words of our own, not song titles
      (French law protects an original title, CPI L112-4). Nothing is stored, so this is not
      saving; it amends D-035 ("a level opens once the one before it is won"): a decision first.
      - Where does the player learn a level's word: on the banner after a win, on the map?
      - No text input exists yet. Does a phone's keyboard come up for a pygbag canvas?
      - Matched in upper case, ASCII only? One word per level, or per chapter?

## 1. Levels as data, in an open plane (D-028)

- [x] A level as plain data, with `to_dict` and `from_dict` like a board (D-024): title, spec,
      the swimmer's start, the items placed in the plane (lights, obstacles), the board (zone,
      stock, locked parts), the objectives, the time limit.
- [x] No walls: `contact.confine` loses its clamp; rays and the light map go as far as the view
      shows; the view frames the items. The tests that lean on walls change
      (`test_a_source_on_both_thrusters_drives_the_body_onto_the_wall_and_holds_it_there`).
- [x] A Run button in the editor: it runs the current level; back in the editor the board is as
      it was; a win opens the next level.

## 2. The levels themselves

- [x] Tutorial 1, fear (uncrossed: flees the light): leave the ring, with a guided tutorial
      (D-038, D-039).
- [ ] The tutorial: in a step that shows a target, only what the step asks for answers: the
      target, the keys that do the same, and Next. Today the rest is dimmed but still live.
- [ ] The tutorial: light each target with a soft spot of light, one per target, instead of
      the rectangle cut in the veil and its outline (`tutorial_draw.py`).
- [ ] The tutorial: a Skip button beside Next ends it, for a player who replays the level.
      - Does Skip end the hints of the later levels too, or only the tutorial?
      - Can a skipped tutorial come back, from the map or a ? button?
- [x] The level after Fear introduces Sum and Diff, with a challenge that needs them. Diff is
      the new operation (thruster inputs already add); Diff(Source, eye) = 1 - e is inhibition.
      Love: stay by the light without touching it (D-040).
- [ ] Tutorial 2, aggression (crossed: charges the light). Visit the light.
- [ ] Tutorial 3, ÷2 on one side (orbits). Its objective is to be chosen: stay within a ring
      round the light for T s, or circle it N times.
- [x] Level 2, "In the shadow": one light, three obstacles, the start in the shadow of one, so
      the eyes see nothing until a drive moves the swimmer out (D-032). Pinned in
      `test_determinism.py`.
- [ ] The real level: to design, with a winner pinned with margin (D-004).

## 3. Complexity is scored, not felt (D-045)

- [x] `complexity(board) -> int` in `graph/board.py`: the number of parts, wires free.
      Every body stays a sphere of radius 1 u, for Stokesian dynamics later.

## 4. The score (D-028)

- [x] Each level scored on the time to win and the number of parts. The session's runs drawn as
      points in that plane, with their Pareto front. Nothing kept between sessions (D-046).

## 5. Ship

- [x] The end screen: "If you liked this and want to support development, reach out", with a
      contact link (brief §3): a comment on the itch.io page (D-035).
- [ ] `DEV_VIEW = False` for the build that is uploaded.
- [ ] `pygbag --build --archive game`, upload to itch.io.
- [ ] Check in Chrome and in Safari. Safari has never been checked: the keys (Cmd+Y opens its
      History window), the fonts, the canvas.

## 6. Small things

- [ ] Click-to-inspect: draw the swimmer's steering vector (brief §1).
- [ ] `main.py`'s docstring still says the Run button "comes with the swimmer's dynamics".
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
