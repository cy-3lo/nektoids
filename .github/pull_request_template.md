## What

<!-- One idea per PR. One or two sentences. -->

## Why

<!-- Link the issue, the brief section, or the decision in docs/decisions.md. -->

## How to check it

<!-- What to run, what you should see on screen. -->

## What to look at (for the reviewer)

<!-- Written for the other contributor, in his vocabulary. /pr-prep drafts this. -->

## Checklist

- [ ] `ruff format --check .` and `ruff check .` pass
- [ ] `python -m pytest -q` passes, including determinism
- [ ] In scope, or a decision is logged in `docs/decisions.md`
- [ ] No new continuous parameter in the graph; no pygame import in `sim/` or `graph/`
