---
name: pr-prep
description: Prepare the current branch for a pull request — format, lint, tests, determinism, invariants, and a PR description written for the physicist's review.
disable-model-invocation: true
---
# Prepare a pull request

1. Find the PR's base: `origin/main`, or the stage branch for an item of a stage
   (`stage/…`, D-200). `git status` and `git diff <base>...HEAD --stat`. If the current branch
   is `main` or a stage, stop and propose a branch name (`feat/…`, `fix/…`, `chore/…`).
2. `ruff format .` then `ruff check .`. Fix trivial findings; list anything that needs a human.
3. `python -m pytest -q`. If `test_determinism.py` fails, stop and explain what changed and why
   the run is no longer reproducible.
4. Read the diff against the invariants in `CLAUDE.md` and the rules in `.claude/rules/`.
   Flag every violation explicitly, even small ones.
5. If the change touches scope, check `docs/decisions.md` has an entry; if not, draft one.
6. Draft the PR description from `.github/pull_request_template.md`, its base named above it.
   Write the "What to look at" section for the physicist, who reviews his own PRs (D-041):
   what to read in the diff, in his vocabulary, and what changes on screen for Camille to
   playtest.
7. Print the description. Do not push and do not open the PR: the human does that.
