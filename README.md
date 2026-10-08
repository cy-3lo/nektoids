# Nektoids

*A game by Cy-3LO.*

You don't control the swimmer. You wire its control board, press run, and watch.

A small Zachtronics-style puzzle game about sensorimotor control. A swimmer sits in a plane of
lights and obstacles. On its control board you place eyes, which read the light, and thrusters,
which push the body. You wire them through a handful of nodes: ×2, ÷2, sum, difference and a
constant source. Signals travel as beads, so a stronger signal is a faster stream of beads, and
there is no slider to tune. Press run: the simulation is deterministic, so the same board always
swims the same way. A level is won by meeting its goals in time. Its score counts the parts used
and the time taken.

The levels come in five chapters: tutorials, Braitenberg's vehicles (fear, aggression, love),
obstacles and shadows, many lights, and levels made by players. A level editor builds new
levels, and a level is shared as a few lines of text, with the board that wins it.

## Play

In a browser, on itch.io: [cy-3lo.itch.io/nektoids](https://cy-3lo.itch.io/nektoids).

Or natively, with Python 3.11 or newer:

```bash
git clone https://github.com/cy-3lo/nektoids
cd nektoids
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python game/main.py
```

## Develop

```bash
pip install -r requirements-dev.txt
python -m pytest -q                # tests, determinism included
ruff format . && ruff check .      # formatting and lint
pygbag game                        # browser build, served on http://localhost:8000
```

`pygbag --build --archive game` produces `game/build/web.zip`, which uploads to itch.io as an
HTML5 project. CI runs the tests on every pull request, and on every push to `main` it also
builds that zip.

The code lives in `game/nektoids/`: `sim/` is the physics, `graph/` the control board and its
nodes, `levels/` the levels as data, and `editor/` everything drawn on screen. The physics and
the board never import pygame, and the tests never do.

## The `docs/` folder

- [`brief.md`](docs/brief.md): the design brief, the principles the game is built on.
- [`decisions.md`](docs/decisions.md): every design decision, numbered and dated, in order. It is
  append-only: a later decision amends an earlier one and says so.
- [`todo.md`](docs/todo.md): what is left to build.
- [`tutorials.md`](docs/tutorials.md): the tutorials' cards, in one place for editing.
- [`walkthrough.md`](docs/walkthrough.md): a guided tour of the code, in the order it runs.

## Credits

Nektoids is a game by Cy-3LO, released under the GNU General Public License v3.0
([`LICENSE`](LICENSE)).

Icons: [Font Awesome Free](https://fontawesome.com) 6.7.2 Solid by Fonticons, Inc., under the
SIL Open Font License 1.1, bundled unmodified with its licence in `game/nektoids/assets/fontawesome/`.
