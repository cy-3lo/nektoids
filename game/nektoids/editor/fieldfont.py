"""How wide a character of the fields' fonts is, IBM Plex Mono, every character as wide as the
next (D-055): measured once at startup, by `Fonts.load`, and read by the scenes to find the
character under a click in a field (D-418). The values here hold until then. Pure Python, no
pygame.
"""

from __future__ import annotations

ADVANCE = {"text": 10.0, "small": 9.0}  # [px] a character of `Fonts.text`, of `Fonts.small`
