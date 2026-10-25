"""
profiles.py – Multi-Game Profile, Action Labels & Macro Manager
===============================================================
Manages persistent game profiles, button remaps, in-game action labels,
combo macros, and double-tap macros. Profiles are stored in 'profiles.json'.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any

# Standard 16 controller buttons
CONTROLLER_BUTTONS = [
    "A", "B", "X", "Y",
    "LB", "RB", "LT", "RT",
    "LS", "RS",
    "START", "BACK",
    "Up", "Down", "Left", "Right"
]

def sanitize_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
    """Ensures mapping is a clean 1:1 bijection across all CONTROLLER_BUTTONS with zero duplicates."""
    used_virt = set()
    sanitized: Dict[str, str] = {}

    for b in CONTROLLER_BUTTONS:
        target = mapping.get(b, b)
        if target in CONTROLLER_BUTTONS and target not in used_virt:
            sanitized[b] = target
            used_virt.add(target)
        else:
            sanitized[b] = None  # to be filled with available unused button

    available_virt = [b for b in CONTROLLER_BUTTONS if b not in used_virt]
    for b in CONTROLLER_BUTTONS:
        if sanitized[b] is None:
            sanitized[b] = available_virt.pop(0) if available_virt else b

    return sanitized

def get_mapped_physical_key(mapping: Dict[str, str], default_key: str) -> str:
    """Finds which physical controller button is currently mapped to default_key."""
    for p, v in mapping.items():
        if v == default_key:
            return p
    return default_key

def swap_button_mapping(mapping: Dict[str, str], target_default_key: str, new_physical_key: str) -> Dict[str, str]:
    """
    Swaps the mapped controller key for target_default_key with new_physical_key.
    Guarantees strict 1:1 correspondence with zero duplicates.
    """
    clean_map = sanitize_mapping(mapping)
    old_physical_key = get_mapped_physical_key(clean_map, target_default_key)

    if old_physical_key == new_physical_key:
        return clean_map

    # What default action was new_physical_key previously triggering?
    other_default_key = clean_map.get(new_physical_key, new_physical_key)

    # Perform bijective swap
    clean_map[new_physical_key] = target_default_key
    clean_map[old_physical_key] = other_default_key

    return clean_map

@dataclass
class GameProfile:
    name: str
    description: str = ""
    # Physical Button -> Target Virtual Button (e.g. "Y": "Y", "B": "A")
    button_mapping: Dict[str, str] = field(default_factory=lambda: {b: b for b in CONTROLLER_BUTTONS})
    # Virtual Button (or Physical Button) -> What this action actually does in this game
    button_actions: Dict[str, str] = field(default_factory=dict)
    macros: List[Dict[str, Any]] = field(default_factory=list)

PROFILES_FILE = Path(__file__).parent / "profiles.json"

DEFAULT_PROFILES = [
    {
        "name": "General Gamepad (Default)",
        "description": "Standard 1:1 pass-through with low latency",
        "button_mapping": {b: b for b in CONTROLLER_BUTTONS},
        "button_actions": {
            "A": "Primary Action / Select / Jump",
            "B": "Cancel / Crouch / Dodge",
            "X": "Interact / Reload / Attack",
            "Y": "Switch Weapon / Heavy Attack",
            "LB": "Left Bumper / Secondary Skill",
            "RB": "Right Bumper / Melee / Ability",
            "LT": "Aim Down Sights / Block / Guard",
            "RT": "Fire Weapon / Primary Attack",
            "LS": "Click Left Stick / Sprint",
            "RS": "Click Right Stick / Melee / Camera Reset",
            "START": "Pause Menu / Options",
            "BACK": "Map / Inventory / Scoreboard",
            "Up": "D-Pad Up / Quick Item 1",
            "Down": "D-Pad Down / Quick Item 2",
            "Left": "D-Pad Left / Next Weapon",
            "Right": "D-Pad Right / Prev Weapon"
        },
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
        "button_actions": {
            "A": "Interact / Roll / Horse Canter",
            "B": "Dodge / Dive Up / Jump",
            "X": "Fast Attack / Dive Down",
            "Y": "Strong Attack",
            "LB": "Radial Menu (Signs & Bombs)",
            "RB": "Cast Quick Bomb / Pocket Item",
            "LT": "Witcher Senses / Parry / Guard",
            "RT": "Cast Selected Witcher Sign",
            "LS": "Sprint / Call Roach (Horse)",
            "RS": "Lock-On Target / Track Quest",
            "START": "Game Pause Menu",
            "BACK": "Inventory / Character / Map",
            "Up": "Drink Potion / Food Slot 1",
            "Down": "Drink Potion / Food Slot 2",
            "Left": "Draw / Sheathe Silver Sword",
            "Right": "Draw / Sheathe Steel Sword"
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
        "description": "Night City combat setup with tactical dash & weapon hotkeys",
        "button_mapping": {b: b for b in CONTROLLER_BUTTONS},
        "button_actions": {
            "A": "Jump / Mantle",
            "B": "Crouch / Slide / Dodge",
            "X": "Reload Weapon / Interact",
            "Y": "Cycle Weapon / Holster (Double-Tap)",
            "LB": "Combat Cyberware / Grenade",
            "RB": "Sandevistan / Berserk / Quickhack",
            "LT": "Aim Down Sights / Block",
            "RT": "Fire Weapon / Strong Melee",
            "LS": "Sprint",
            "RS": "Quick Melee Attack / Camera Reset",
            "START": "Pause / Game Settings",
            "BACK": "Hub Menu (Inventory, Map, Journal)",
            "Up": "Use Inhaler / MaxDoc Healing",
            "Down": "Phone / Contacts",
            "Left": "Radio / Vehicle Controls",
            "Right": "Call Vehicle"
        },
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
        "button_actions": {
            "A": "Jump",
            "B": "Roll / Backstep / Sprint (Hold)",
            "X": "Use Equipped Quick Item (Flask)",
            "Y": "Interact / Event Action / Two-Hand Stance",
            "LB": "Guard / Left Hand Skill",
            "RB": "Right Hand Light Attack",
            "LT": "Ash of War / Weapon Skill",
            "RT": "Right Hand Heavy Attack / Charge",
            "LS": "Crouch / Stealth Mode",
            "RS": "Lock-On Target / Camera Reset",
            "START": "Equipment & Game Menu",
            "BACK": "Map",
            "Up": "Cycle Sorcery / Incantation",
            "Down": "Cycle Equipped Item",
            "Left": "Cycle Left Armament",
            "Right": "Cycle Right Armament"
        },
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
                    button_actions=item.get("button_actions", {}),
                    macros=item.get("macros", [])
                )
                self.profiles[profile.name] = profile
            
            # If loaded profiles lack default button actions, merge defaults
            for def_item in DEFAULT_PROFILES:
                if def_item["name"] in self.profiles:
                    p = self.profiles[def_item["name"]]
                    if not p.button_actions:
                        p.button_actions = def_item.get("button_actions", {})
        except Exception:
            self._create_default_profiles()

    def _create_default_profiles(self):
        self.profiles = {}
        for item in DEFAULT_PROFILES:
            profile = GameProfile(
                name=item["name"],
                description=item.get("description", ""),
                button_mapping=item["button_mapping"],
                button_actions=item.get("button_actions", {}),
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
                    "button_actions": p.button_actions,
                    "macros": p.macros
                }
                for p in self.profiles.values()
            ]
        }
        temp_file = self.file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        temp_file.replace(self.file_path)

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
