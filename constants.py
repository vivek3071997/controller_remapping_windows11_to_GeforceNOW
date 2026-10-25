"""
constants.py – Shared constants, default mappings, and vgamepad enum tables.
"""

import vgamepad as vg

# ──────────────────────────────────────────────────────────────────────
# Default action → virtual-button mapping (what the UI starts with)
# ──────────────────────────────────────────────────────────────────────
DEFAULT_MAPPING: dict[str, str] = {
    "Heavy Attack":                         "Y",
    "Light Attack / Dive Down":             "X",
    "Sprint / Call Horse":                  "LS",
    "Track Quest / Lock on":                "RS",
    "Interact / Roll / Horse Acceleration": "A",
    "Silver Sword (Draw, Sheathe, Oil)":    "Left",
    "Dodge / Dive Up / Jump":               "B",
    "Steel Sword (Draw, Sheathe, Oil)":     "Right",
    "Drink Potion 2":                       "Down",
    "Drink Potion 1":                       "Up",
    "Focus / Guard":                        "LT",
    "Cast Sign / Quick Sign (Hold)":        "RT",
    "Throw Item":                           "RB",
    "Quick Menu":                           "START",
    "Radial Menu":                          "LB",
    "Game Menu":                            "BACK",
}

# Every assignable virtual button label (populates every dropdown)
BUTTON_OPTIONS: list[str] = [
    "A", "B", "X", "Y",
    "LB", "RB", "LT", "RT",
    "LS", "RS",
    "START", "BACK",
    "Up", "Down", "Left", "Right",
]

# ──────────────────────────────────────────────────────────────────────
# String → vgamepad XUSB_BUTTON / special flag
# LT and RT are analog triggers, not digital XUSB buttons — we handle
# them separately in the engine, but still give them keys here.
# ──────────────────────────────────────────────────────────────────────
VG_BUTTONS: dict[str, int] = {
    "A":     vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "B":     vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "X":     vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Y":     vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "LB":    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB":    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "LS":    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "RS":    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "BACK":  vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "Up":    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "Down":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "Left":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "Right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}

# Triggers are analog axes on the virtual pad (0–255).
# We store them separately so the engine can emit full-press / release.
TRIGGER_LABELS = {"LT", "RT"}

# ──────────────────────────────────────────────────────────────────────
# Physical hardware → canonical label mapping  (pygame button indices)
# These numbers match a standard XInput-exposed controller as reported
# by pygame on Windows.
# ──────────────────────────────────────────────────────────────────────
PHYSICAL_BUTTON_MAP: dict[int, str] = {
    0: "A",
    1: "B",
    2: "X",
    3: "Y",
    4: "LB",
    5: "RB",
    6: "BACK",
    7: "START",
    8: "LS",
    9: "RS",
}

# Physical axis indices (pygame)
AXIS_LX   = 0  # Left stick horizontal
AXIS_LY   = 1  # Left stick vertical
AXIS_RX   = 2  # Right stick horizontal
AXIS_RY   = 3  # Right stick vertical
AXIS_LT   = 4  # Left trigger  (–1 … +1, rest = –1)
AXIS_RT   = 5  # Right trigger (–1 … +1, rest = –1)

# Trigger dead zone — treat >0.15 as "pressed" for digital-style actions
TRIGGER_DIGITAL_THRESHOLD = 0.15

# Left-stick forward threshold for horse acceleration detection
HORSE_ACCEL_STICK_THRESHOLD = -0.80

# Engine polling interval (seconds). ~125 Hz ≈ 8 ms per tick.
ENGINE_POLL_INTERVAL = 0.008

# Double-tap window (seconds) for dodge detection
DOUBLE_TAP_WINDOW = 0.30
