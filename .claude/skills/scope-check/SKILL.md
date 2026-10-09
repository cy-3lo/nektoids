---
name: scope-check
description: Check a proposed feature or change against the Nektoids scope (the current stage's, D-105) and the design non-negotiables. Use before starting a feature, and whenever a request mentions flocking, several agents, thresholds, sliders, new sensor types, new parts, levels or items, or anything else listed as out of scope.
---
# Scope check

Do not start implementing. Answer in at most ten lines.

1. Restate the proposed change in one sentence.
2. Read the "Scope" section of the project instructions, `CLAUDE.local.md` (the current stage's, D-105), sections 1 and 3 of
   `docs/brief.md`, and `docs/decisions.md` (a later decision overrides the brief).
3. Classify it: IN (explicitly in scope), OUT (explicitly excluded), or GREY (not mentioned).
4. Check it against the non-negotiables: no sliders; no threshold node in early levels;
   thrust budget rather than node budget; determinism; countable win conditions;
   spatial scarcity in the editor.
5. Give the verdict, quote the line of the brief or decision that settles it, and for OUT or
   GREY propose the smallest in-scope version — or suggest logging it in `docs/ideas.md`
   (D-028).
