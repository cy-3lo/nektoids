# To do

What is left before the jam build ships, in the order it unblocks the rest. Tick an item in the
PR that does it. Ideas for after the jam go in [`ideas.md`](ideas.md), decisions in
[`decisions.md`](decisions.md).

## 0. What the player sees first, and how they move around (D-028)

- [ ] Open on Tutorial 1's board under a title card ("Nektoids — wire the eyes to the
      thrusters, then Run"), gone at the first click; a Map button from the start.
- [ ] A screen router in `main.py`: map, level (edit and run), sandbox, end screen. A pure state
      machine, tested headless; F2, F3 and F4 stay developer tools behind `DEV_VIEW`.
- [ ] The map: one route, light (three tutorials, then the real level), and the sandbox.
      Levels open one after the other.
- [ ] An explanation for each part (sensor, operator, actuator): clicked, it opens a small box
      next to it that says what it does; another click or any key closes it. To settle: which
      click opens it, since a click on a part already wires, moves, turns or deletes it (in the
      menu, a click on its row that does not pick it up; on the board, the Add tool, or a ?).

## 1. Levels as data, in an open plane (D-028)

- [ ] A level as plain data, with `to_dict` and `from_dict` like a board (D-024): title, spec,
      the swimmer's start, the items placed in the plane (lights, obstacles), the board (zone,
      stock, locked parts), the objectives, the time limit.
- [ ] No walls: `contact.confine` loses its clamp; rays and the light map go as far as the view
      shows; the view frames the items. The tests that lean on walls change
      (`test_a_source_on_both_thrusters_drives_the_body_onto_the_wall_and_holds_it_there`).
- [ ] A Run button in the editor: it runs the current level; back in the editor the board is as
      it was; a win opens the next level.

## 2. The levels themselves

- [ ] Tutorial 1, fear (uncrossed: flees the light). Its countable objective is to be chosen:
      end in the dark, or never come within d of the light.
- [ ] Tutorial 2, aggression (crossed: charges the light). Visit the light.
- [ ] Tutorial 3, ÷2 on one side (orbits). Its objective is to be chosen: stay within a ring
      round the light for T s, or circle it N times.
- [ ] The real level, "Two lights, four obstacles": check it is still winnable in the open
      plane, and pin a winner with margin (D-004), as `test_determinism.py` does now.

## 3. Body size grows with complexity (brief §1: thrust budget, not node budget)

- [ ] `complexity(graph) -> int` in `graph/`: what counts (parts, wires, crossings) is a
      decision to write.
- [ ] The radius from the complexity in `sim/`. V ∝ 1/R and Ω ∝ 1/R² are already there
      (D-022): a bigger body loses its turning first.

## 4. The score (D-028)

- [ ] Each level scored on the time to win and the number of parts. The session's runs drawn as
      points in that plane, with their Pareto front. Nothing kept between sessions.

## 5. Ship

- [ ] The end screen: "If you liked this and want to support development, reach out", with a
      contact link (brief §3).
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
