# Chapter 0's tutorials, for editing

Each level's cards, in order, as its file holds them (`game/nektoids/levels/data/0-tutorials/`).
Edit the text here; Claude carries it back to the files. In a card's text, `<br>` starts a new
paragraph, and `**Editor**` marks a game's word, drawn in accent1 (D-337); the game wraps the
lines itself. What a card highlights or waits for may be changed too, in words: Claude turns
it into the file's terms.

Open: the tab and the drawer on screen while the card shows. Highlighted: what the card
draws in accent1, pulsing, the only highlight (D-336, D-337), the switch its fill (D-350); a
highlighted card lets through only what it waits for, and one with none lets all through. Waits for: what moves it on. A cell
is (q, r) on the board: (0, 0) its centre, (1, 0) ahead, (-1, 0) behind.

## 0.1 Wiring

- Spec: Get into the ring ahead.
- Opens on: the Run
- Ghosts: a wire from (0, 0) to (-1, 0)

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | This is your tiny **swimmer**.<br>Your goal is to wire its control board to make it reach the ring ahead. | — | Next, or any key or click |
| 2 | Run, Diagnostic | **Objectives** are what the level asks. Here, get into the ring before the 10 s are out. | Run: Objectives | Next, or any key or click |
| 3 | Run, Diagnostic | The window has two tabs: Run plays the level and the **Editor** builds the control board.<br>Click the **Editor** tab or button, or press Tab. | Editor tab; Editor button | the Editor opens |
| 4 | Editor, Parts | The nav bar opens the drawers: **Tools**, **Parts**, **Files**, **Diagnostic**, **Navigator**. At its foot: **Hints**, **Settings**, **Chapters**, and **Run**. | the nav bar | Next, or any key or click |
| 5 | Editor, Parts | A **Source** sends beads all the time; a thruster pushes as hard as beads come in.<br>Click the **Source**, then the **Thruster** to wire them. | the Source, cell (0, 0); the Thruster, cell (-1, 0) | a wire from the Source, cell (0, 0) to the Thruster, cell (-1, 0) |
| 6 | Editor, Parts | Click the **Run** tab or button, or press **Tab**. | Run tab; Run button | the Run opens |
| 7 | Run, Diagnostic | Press **Play**, or Space to play the simulation. | Run: Play | the run is won |
| 8 | Run, Diagnostic | You won! You reached the objectives.<br>If you are stuck, try clicking **Hints**. | Hints icon | any key or click closes it |

## 0.2 Turning

- Spec: Reach the ring by turning round the obstacle.
- Opens on: the Run
- Ghosts: thruster on (-1, 1) pointing E

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | Reach the ring by turning round the obstacle.<br>Press the **Editor** button or tab, or press Tab. | Editor tab; Editor button | the Editor opens |
| 2 | Editor, Parts | Behind the **Source**, the **Thruster** pushes straight ahead. Off the centre, a push turns the swimmer.<br>Move the **Thruster** to the swimmer's right: drag it, or click it, then **Move** on the **Wheel**. | the Thruster, cell (-1, 0); cell (-1, 1); Wheel: Move | the thruster moved to cell (-1, 1) |
| 3 | Editor, Parts | Click the **Run** tab or button, or press **Tab**. | Run tab | the Run opens |
| 4 | Run, Diagnostic | Press **Play**, or Space to play the simulation. | Run: Play | the run is won |

## 0.3 Eyes

- Spec: Swim to the light and touch it.
- Opens on: the Run
- Ghosts: eye on (1, 0) pointing E; thruster on (-1, 0) pointing E; a wire from (1, 0) to (-1, 0)

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | Swim to the light and touch it. To see it, the swimmer needs an **Eye**.<br>Press the **Editor** button or tab, or press Tab. | Editor tab; Editor button | the Editor opens |
| 2 | Editor, Parts | An **Eye** sends beads as fast as it sees light: more from a light near it and in front of it.<br>Here the light is straight ahead. | Parts drawer; Parts: Eye row | Next, or any key or click |
| 3 | Editor, Parts | Put an **Eye** and a **Thruster** on the board, both pointing forward, and wire the **Eye** to the **Thruster**. Then run it. | — | any key or click closes it |

## 0.4 Half

- Spec: Stay in the ring for 3 s.
- Opens on: the Run
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | Stay 3 s in the ring. At full push the swimmer crosses it in 2 s: too fast.<br>Press the **Editor** button or tab, or press Tab. | Editor tab; Editor button | the Editor opens |
| 2 | Editor, Parts | The **Halve** sends half the beads that come in, the **Double** twice as many. No wire carries more than a **Source** sends. | Parts drawer; Parts: Halve row; Parts: Double row | any key or click closes it |

## 0.5 Minus

- Spec: Stay 3 s in the ring round the light, without touching it.
- Opens on: the Run
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | Stop in the ring round the light for 3 s, without touching it.<br>Press the **Editor** button or tab, or press Tab. | Editor tab; Editor button | the Editor opens |
| 2 | Editor, Parts | The **Diff** sends the difference of its two inputs.<br>A **Source** less an eye: a full push in the dark, none once the eye sees all the light it can. | Parts: Diff row | any key or click closes it |

## 0.6 Diagnostic

- Spec: Swim to the light and touch it.
- Opens on: the Run
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Run, Diagnostic | This swimmer comes with an **Eye** wired to a **Thruster**, yet it does not move.<br>Press the **Editor** button or tab, or press Tab. | Editor tab; Editor button | the Editor opens |
| 2 | Editor, Parts | Open **Diagnostic** by choosing the stethoscope, or pressing **D**. | Diagnostic (stethoscope) drawer | Diagnostic (stethoscope) opens |
| 3 | Editor, Diagnostic | The main screen shows your board. The map shows your swimmer and the light.<br>Drag it round the light and turn it with the mouse wheel: when does its eye see the light? | — | any key or click closes it |

## Build your level: the Maker

- Spec: No goal: try any wiring.
- Opens on: the Maker, Objects open
- Ghosts: none

| # | Open | Text | Highlighted | Waits for |
|---|---|---|---|---|
| 1 | Maker, Objects | This is the **Maker**, a new tab: build your own level here.<br>Place lights, obstacles and rings in **Objects**, choose the **Goals**, try it in the **Editor** and the **Run**, and share it from **Files**. | Maker tab | any key or click closes it |
