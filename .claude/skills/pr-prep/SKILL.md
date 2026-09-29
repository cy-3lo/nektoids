---
name: pr-prep
description: Prepare the current branch for a pull request — format, lint, tests, determinism, invariants, and a PR description written for the other contributor.
disable-model-invocation: true
---
# Prepare a pull request

1. `git status` and `git diff main...HEAD --stat`. If the current branch is `main`, stop and
   propose a branch name (`feat/…`, `fix/…`, `chore/…`).
2. `ruff format .` then `ruff check .`. Fix trivial findings; list anything that needs a human.
3. `python -m pytest -q`. If `test_determinism.py` fails, stop and explain what changed and why
   the run is no longer reproducible.
4. Read the diff against the invariants in `CLAUDE.md` and the rules in `.claude/rules/`.
   Flag every violation explicitly, even small ones.
5. If the change touches scope, check `docs/decisions.md` has an entry; if not, draft one.
6. Draft the PR description from `.github/pull_request_template.md`. Write the
   "What to look at" section for the reviewer: diffs in `sim/` are reviewed by the CS student,
   diffs in `graph/` or `editor/` by the physicist — use their vocabulary, not the author's.
7. Print the description. Do not push and do not open the PR: the human does that.
