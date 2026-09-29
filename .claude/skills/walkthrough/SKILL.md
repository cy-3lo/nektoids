---
name: walkthrough
description: Explain a diff, pull request, file or concept to the other contributor in his own vocabulary — physics for the physicist, software engineering for the CS student. Use when reviewing a PR or reading code the other person wrote.
---
# Walkthrough for the other contributor

Find out who is reading from `CLAUDE.local.md`; if it is missing, ask once.

For the CS student reading physics code: what physical quantity each array holds and its units,
which equation is integrated, why this numerical scheme, and what would break if `dt` doubled.
Name the idea (Newton's second law with linear drag, symplectic Euler, ray casting) and give
the one-line intuition rather than a derivation.

For the physicist reading software code: the data structures and their invariants, the control
flow of one frame, where state lives and who may mutate it. Use a physics analogy only when it is
accurate (topological evaluation order is causal ordering; a pure function has no hidden state).

Structure the answer as:
1. What it does, in two sentences.
2. The key lines, in execution order.
3. Two or three questions the reviewer should be able to answer after reading — the review
   checklist for this diff.
4. Anything suspicious or untested.

Do not rewrite the code. Point at lines; let the reviewer comment on the PR.
