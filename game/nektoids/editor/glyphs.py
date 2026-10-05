"""The icons' names and their codepoints in Font Awesome Free 6.7.2 Solid (D-012), and which of
them turn with their part. Plain data, no pygame, so that tests check every name an icon is
drawn by (the table of kinds', the objectives'); `icons.py` draws them.
"""

# Codepoints from the font's own metadata (icons.yml, Font Awesome Free 6.7.2).
GLYPH = {
    "eye": 0xF06E,
    "pencil": 0xF303,
    "arrow-right-arrow-left": 0xF0EC,
    "eraser": 0xF12D,
    "angles-up": 0xF102,
    "angles-down": 0xF103,
    "rocket": 0xF135,
    "plus": 0x2B,
    "link": 0xF0C1,
    "rotate-right": 0xF2F9,
    "up-down-left-right": 0xF0B2,
    "trash-can": 0xF2ED,
    "caret-down": 0xF0D7,
    "caret-right": 0xF0DA,
    "infinity": 0xF534,
    "minus": 0xF068,
    "shapes": 0xF61F,  # the Maker's Objects (D-301)
    "circle": 0xF111,  # an obstacle
    "location-arrow": 0xF124,  # the swimmer's start
    "circle-dot": 0xF192,  # a mark (D-306)
    "magnifying-glass-plus": 0xF00E,
    "magnifying-glass-minus": 0xF010,
    "hand": 0xF256,
    "location-crosshairs": 0xF601,
    "play": 0xF04B,
    "pause": 0xF04C,
    "forward-step": 0xF051,
    "rotate-left": 0xF2EA,
    "backward-step": 0xF048,
    "forward": 0xF04E,
    "lightbulb": 0xF0EB,
    "gauge-high": 0xF625,
    "wind": 0xF72E,
    "check": 0xF00C,
    "backward-fast": 0xF049,
    "reply": 0xF3E5,
    "share": 0xF064,
    "floppy-disk": 0xF0C7,
    "folder-open": 0xF07C,
    "copy": 0xF0C5,  # Save: the board as text (D-206)
    "paste": 0xF0EA,  # Load's field
    "pen": 0xF304,
    "map": 0xF279,
    "lock": 0xF023,
    "circle-info": 0xF05A,
    "puzzle-piece": 0xF12E,
    "screwdriver-wrench": 0xF7D9,
    "compass": 0xF14E,
    "chevron-left": 0xF053,
    "gear": 0xF013,
    "keyboard": 0xF11C,
    "key": 0xF084,  # Chapters' passkey field (D-075)
    "clock": 0xF017,
    "graduation-cap": 0xF19D,
    "volume-high": 0xF028,
    "music": 0xF001,
    "border-all": 0xF84C,
    "list-check": 0xF0AE,
    "magnifying-glass": 0xF002,
    "trophy": 0xF091,
    "diagram-project": 0xF542,
    "bullseye": 0xF140,
    "circle-xmark": 0xF057,
    "right-from-bracket": 0xF2F5,
    "rotate": 0xF2F1,  # Circle the light (D-097)
    "location-dot": 0xF3C5,
    "stethoscope": 0xF0F1,
    "life-ring": 0xF1CD,  # Hints (D-078)
    "comment": 0xF075,  # each of its rows, a hint (D-088)
}
# Direction an icon points to as drawn by the font [degrees, counter-clockwise from E]. The eye
# looks up: turned to face E, its long axis runs along the eye's flat side.
POINTS_TO = {"rocket": 45.0, "eye": 90.0}
