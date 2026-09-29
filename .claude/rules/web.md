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
- Drawing reads simulation state; it never mutates it.
- Editor space is scarce by design: small fixed grid, no infinite canvas, no zoom.
- Click-to-inspect and beads on wires are core features, not polish.
