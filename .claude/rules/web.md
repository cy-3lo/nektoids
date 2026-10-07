---
paths:
  - "game/main.py"
  - "game/nektoids/editor/**"
---
# Frame loop and editor rules (pygbag)

- The main loop is `async` and does `await asyncio.sleep(0)` exactly once per frame.
- `asyncio.run(main())` is the last line of `main.py`. Nothing after it: no `sys.exit()`,
  no `pygame.quit()`.
- Load every asset at startup. No file I/O, threads, subprocesses or network during the loop.
- Web dependencies are declared in the `# /// script` header of `main.py`.
- The page's JavaScript is reached only through `editor/clipboard.py`, its script put in once
  at startup (D-206); nothing else talks to the page.
- Drawing reads simulation state; it never mutates it.
- Board space is scarce by design: each level's zone is small and fixed, and the canvas is not
  infinite. Zoom and pan move the view only, never the zone (D-013).
- Click-to-inspect and beads on wires are core features, not polish.
- Colours come only from `editor/palette.py`, named by their job; no RGB tuple or hex code
  anywhere else (D-047, `test_architecture.py`).
