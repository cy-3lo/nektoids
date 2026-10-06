# Chapter 0's tutorials, for editing

Each level's cards, in order, as its file holds them (`game/nektoids/levels/data/0-tutorials/`).
Edit the text here; Claude carries it back to the files. In a card's text, `<br>` starts a new
paragraph; the game wraps the lines itself. What a card highlights or waits for may be changed
too, in words: Claude turns it into the file's terms.

Open: the tab and the drawer on screen while the card shows. Highlighted: what the card
draws in accent1, the only highlight (no sparks, D-336); a highlighted card lets through only
what it waits for, and one with none lets all through. Waits for: what moves it on. A cell
is (q, r) on the board: (0, 0) its centre, (1, 0) ahead, (-1, 0) behind.

## 0.1 Wiring

- Spec: Get into the ring ahead.
- Hint 1, the idea: A Source pushes all the time.
- Opens on: the Run
- Ghosts: a wire from (0, 0) to (-1, 0)

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | This is your tiny swimmer.<br>Your goal is to wire its control board to make it reach the ring ahead. | — | Next, or any key or click |
| 2 | Run, Diagnostic | Objectives are what the level asks. Here, get into the ring before the 10 s are out. | Run: Objectives | Next, or any key or click |
| 3 | Run, Diagnostic | The window has two tabs: Run plays the level and the Editor builds the control board.<br>Click the Editor tab or button, or press Tab. | Editor tab; Editor button | the Editor opens |
| 4 | Editor, Parts | The nav bar opens the drawers: Tools, Parts, Files, Diagnostic, Navigator. At its foot: Hints, Settings, Chapters, and Run. | the nav bar | Next, or any key or click |
| 5 | Editor, Parts | A Source sends beads all the time; a thruster pushes as hard as beads come in.<br>Click the Source, then the Thruster to wire them. | the Source, cell (0, 0); the Thruster, cell (-1, 0) | a wire from the Source, cell (0, 0) to the Thruster, cell (-1, 0) |
| 6 | Editor, Parts | Click the Run tab or button, or press Tab. | — | the Run opens |
| 7 | Run, Diagnostic | Press Play, or Space: the swimmer goes straight into the ring. | — | the run is won |
| 8 | Run, Diagnostic | You won! You reached the objectives.<br>If you are stuck, try clicking Hints. | Hints icon | any key or click closes it |

## 0.2 Turning

- Spec: Go round the obstacle into the ring behind it.
- Hint 1, the idea: Off the centre, a push turns.
- Opens on: the Editor, Tools open
- Ghosts: thruster on (0, 1) pointing E

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Editor, Tools | This thruster pushes through the body's centre: the swimmer slides, without turning. Off the centre, a push turns it.<br>Click the thruster, then Turn left on the Wheel, or press L: it turns by 60 degrees. | the Thruster, cell (0, 1); Wheel: Turn left | the Thruster, cell (0, 1) points E |
| 2 | Editor, Tools | Click the Run tab or button, or press Tab. | — | the Run opens |
| 3 | Run, Diagnostic | Press Play, or Space: the push turns the swimmer round the obstacle. | — | the run is won |

## 0.3 Eyes

- Spec: Swim to the light and touch it.
- Hint 1, the idea: The eye drives what it is wired to.
- Opens on: the Editor, Parts open
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Editor, Parts | An eye sends beads as fast as it sees light: more from a light near it and in front of it.<br>Here the light is straight ahead. | Parts drawer; Parts: Eye row | Next, or any key or click |
| 2 | Editor, Parts | Put an eye and a thruster on the board, both pointing forward, and wire the eye to the thruster. Then run it. | — | any key or click closes it |

## 0.4 Half

- Spec: Stay in the ring for 3 s.
- Hint 1, the idea: Slower stays longer.
- Opens on: the Editor, Parts open
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Editor, Parts | The Halve sends half the beads that come in, the Double twice as many. No wire carries more than a Source sends. | Parts drawer; Parts: Halve row; Parts: Double row | Next, or any key or click |
| 2 | Editor, Parts | At full push the swimmer crosses the ring in 2 s: too fast to stay 3 s in it. | — | any key or click closes it |

## 0.5 Minus

- Spec: Stay 3 s in the ring round the light, without touching it.
- Hint 1, the idea: The light takes the push away.
- Opens on: the Editor, Parts open
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Editor, Parts | The Diff sends the difference of its two inputs.<br>A Source less an eye: a full push in the dark, none once the eye sees all the light it can. | Parts drawer; Parts: Diff row | any key or click closes it |

## 0.6 Diagnostic

- Spec: Swim to the light and touch it.
- Hint 1, the idea: Where does the eye look?
- Opens on: the Editor, Parts open
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Editor, Parts | This swimmer comes with an eye wired to a thruster, yet it does not move. Open Diagnostic by choosing the stethoscope, or pressing D. | Diagnostic (stethoscope) drawer | Diagnostic (stethoscope) opens |
| 2 | Editor, Diagnostic | The main screen shows your board. The map shows your swimmer and the light.<br>Drag it round the light and turn it with the mouse wheel: when does its eye see the light? | — | any key or click closes it |
