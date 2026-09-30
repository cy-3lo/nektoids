# Nektoids

*A game by Cy-3LO.*

You don't steer the agents. You wire their sensors to their thrusters, press run, and watch.

A small Zachtronics-style puzzle game about collective behaviour, built by a father and his son.
Design brief: [`docs/brief.md`](docs/brief.md). Decisions: [`docs/decisions.md`](docs/decisions.md).

**New to the code?** [`docs/walkthrough.md`](docs/walkthrough.md) is a guided tour of `graph/` and
`editor/`, written for Camille: what runs when, the invariants, and what is still untested.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python game/main.py          # native window
python -m pytest -q          # tests
pygbag game                  # browser build, served on http://localhost:8000
```

`pygbag --build --archive game` produces `game/build/web.zip`, which uploads to itch.io as an
HTML5 project. CI builds the same zip on every push to `main`.

## Working together

- `main` is protected: every change goes through a pull request reviewed by the other person.
- The physicist owns `game/nektoids/sim/`; the CS student owns `game/nektoids/graph/` and
  `game/nektoids/editor/`. Ownership means "decides and writes", not "the only one allowed in".
- One idea per PR. Anything that changes scope or a model choice gets a line in `docs/decisions.md`.

## Working with Claude Code

Shared configuration (committed):

| File | Role |
|---|---|
| `CLAUDE.md` | Project context, scope lock, invariants, how to behave in a learning project |
| `.claude/rules/*.md` | Extra rules loaded only when working in `sim/`, `graph/`, or the frame loop/editor |
| `.claude/skills/` | `/scope-check`, `/pr-prep`, `/walkthrough` |
| `.claude/settings.json` | Permissions (tests and local git allowed, push asks, force-push denied) and a hook that formats edited Python with ruff |

Personal configuration (not committed), one per contributor:

- `CLAUDE.local.md` at the repo root, one or two lines saying who you are, for example
  `I am the CS student. Explain, then let me write the code in graph/ and editor/.`
- Your output style, chosen in `/config` (for learning, try *Learning* or *Explanatory*).

## Credits

Icons: [Font Awesome Free](https://fontawesome.com) 6.7.2 Solid by Fonticons, Inc., under the
SIL Open Font License 1.1, bundled unmodified with its licence in `game/nektoids/assets/fontawesome/`.
