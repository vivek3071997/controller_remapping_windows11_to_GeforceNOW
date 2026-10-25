"""
profiles.py – Multi-Game Profile & Macro Manager
=================================================
Manages persistent game profiles, button remaps, combo macros, and double-tap macros.
Profiles are stored in 'profiles.json'.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any

# Standard 16 controller buttons
CONTROLLER_BUTTONS = [
    "A", "B", "X", "Y",
    "LB", "RB", "LT", "RT",
    "LS", "RS",
    "START", "BACK",
    "Up", "Down", "Left", "Right"
]

@dataclass
class MacroAction:
    """A macro triggered by double-tapping or combining buttons."""
    name: str                           # e.g. "Instant Quickcast", "Jump-Attack"
    trigger_type: str                   # 'double_tap' or 'combo'
    trigger_buttons: List[str]          # ['B'] for double-tap or ['LB', 'A'] for combo
    output_sequence: List[str]          # sequence of buttons to press, e.g. ['RT', 'X']
    hold_duration_ms: int = 100         # Duration to hold output in ms
    interval_ms: int = 50               # Delay between sequence buttons in ms

@dataclass
class GameProfile:
    name: str
    description: str = ""
    # Map from Physical Button -> Target Virtual Button (e.g. "Y": "Y", "B": "A")
    button_mapping: Dict[str, str] = field(default_factory=lambda: {b: b for b in CONTROLLER_BUTTONS})
    macros: List[Dict[str, Any]] = field(default_factory=list)

PROFILES_FILE = Path(__file__).parent / "profiles.json"

DEFAULT_PROFILES = [
    {
        "name": "General Gamepad (Default)",
        "description": "Standard 1:1 pass-through with low latency",
        "button_mapping": {b: b for b in CONTROLLER_BUTTONS},
        "macros": [
            {
                "name": "Quick Dodge (Double Tap B)",
                "trigger_type": "double_tap",
                "trigger_buttons": ["B"],
                "output_sequence": ["B"],
                "hold_duration_ms": 120,
                "interval_ms": 40
            }
        ]
    },
    {
        "name": "The Witcher 3: Wild Hunt",
        "description": "Optimized combat layout with instant quicksign & dodge swap",
        "button_mapping": {
            "A": "A", "B": "B", "X": "X", "Y": "Y",
            "LB": "LB", "RB": "RB", "LT": "LT", "RT": "RT",
            "LS": "LS", "RS": "RS", "START": "START", "BACK": "BACK",
            "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right"
        },
        "macros": [
            {
                "name": "Aard Combo (LB + X)",
                "trigger_type": "combo",
                "trigger_buttons": ["LB", "X"],
                "output_sequence": ["RT"],
                "hold_duration_ms": 150,
                "interval_ms": 50
            },
            {
                "name": "Double Tap Roll (Double Tap A)",
                "trigger_type": "double_tap",
                "trigger_buttons": ["A"],
                "output_sequence": ["B"],
                "hold_duration_ms": 120,
                "interval_ms": 40
            }
        ]
    },
    {
        "name": "Cyberpunk 2077",
        "description": "Shooter layout with tactical sprint and dash macros",
        "button_mapping": {b: b for b in CONTROLLER_BUTTONS},
        "macros": [
            {
                "name": "Fast Dash (Double Tap B)",
                "trigger_type": "double_tap",
                "trigger_buttons": ["B"],
                "output_sequence": ["B", "B"],
                "hold_duration_ms": 80,
                "interval_ms": 40
            }
        ]
    },
    {
        "name": "Elden Ring / Souls-like",
        "description": "Optimized for two-handing weapon macro & heavy attack combo",
        "button_mapping": {b: b for b in CONTROLLER_BUTTONS},
        "macros": [
            {
                "name": "Two-Hand Weapon (Y + RB)",
                "trigger_type": "combo",
                "trigger_buttons": ["Y", "RB"],
                "output_sequence": ["Y", "RB"],
                "hold_duration_ms": 120,
                "interval_ms": 50
            }
        ]
    }
]

class ProfileManager:
    def __init__(self, file_path: Path = PROFILES_FILE):
        self.file_path = file_path
        self.profiles: Dict[str, GameProfile] = {}
        self.load_profiles()

    def load_profiles(self):
        if not self.file_path.exists():
            self._create_default_profiles()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.profiles = {}
            for item in data.get("profiles", []):
                profile = GameProfile(
                    name=item["name"],
                    description=item.get("description", ""),
                    button_mapping=item.get("button_mapping", {b: b for b in CONTROLLER_BUTTONS}),
                    macros=item.get("macros", [])
                )
                self.profiles[profile.name] = profile
        except Exception:
            self._create_default_profiles()

    def _create_default_profiles(self):
        self.profiles = {}
        for item in DEFAULT_PROFILES:
            profile = GameProfile(
                name=item["name"],
                description=item.get("description", ""),
                button_mapping=item["button_mapping"],
                macros=item["macros"]
            )
            self.profiles[profile.name] = profile
        self.save_profiles()

    def save_profiles(self):
        data = {
            "profiles": [
                {
                    "name": p.name,
                    "description": p.description,
                    "button_mapping": p.button_mapping,
                    "macros": p.macros
                }
                for p in self.profiles.values()
            ]
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_profile(self, name: str) -> GameProfile:
        if name in self.profiles:
            return self.profiles[name]
        return next(iter(self.profiles.values()))

    def save_profile(self, profile: GameProfile):
        self.profiles[profile.name] = profile
        self.save_profiles()

    def delete_profile(self, name: str) -> bool:
        if name in self.profiles and len(self.profiles) > 1:
            del self.profiles[name]
            self.save_profiles()
            return True
        return False
