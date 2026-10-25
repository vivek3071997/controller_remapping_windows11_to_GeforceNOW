"""
engine.py – Universal High-Performance Gamepad Remapper & Macro Engine
=======================================================================
Runs a 125 Hz translation loop (~8 ms per tick) bridging physical gamepad
(e.g., Cosmic Byte Ares Pro) to a ViGEmBus Virtual Xbox 360 controller for
GeForce NOW or any Windows game.

Features:
  - 1:1 customizable button remapping per game profile
  - Macro execution (Double-tap & multi-button combos)
  - Full analog trigger gradient handling (0.0 to 1.0)
  - Stick deadzones and axis normalization
  - Real-time telemetry broadcast for live visualizer (physical & virtual state)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any

import pygame
import vgamepad as vg
from PyQt6.QtCore import QObject, pyqtSignal

from constants import (
    AXIS_LT,
    AXIS_LX,
    AXIS_LY,
    AXIS_RT,
    AXIS_RX,
    AXIS_RY,
    DOUBLE_TAP_WINDOW,
    ENGINE_POLL_INTERVAL,
    PHYSICAL_BUTTON_MAP,
    TRIGGER_DIGITAL_THRESHOLD,
    TRIGGER_LABELS,
    VG_BUTTONS,
)

class MappingSignals(QObject):
    status_updated = pyqtSignal(str)
    # Broadcasts live state: (controller_name, physical_buttons, virtual_buttons, lt_val, rt_val, lx, ly, rx, ry)
    telemetry_updated = pyqtSignal(dict)

@dataclass
class EngineConfig:
    # Physical Button -> Virtual Target Button (e.g. {"A": "A", "B": "X", ...})
    button_mapping: Dict[str, str] = field(default_factory=dict)
    # List of macros defined for this profile
    macros: List[Dict[str, Any]] = field(default_factory=list)

# Global shared telemetry dictionary for Web UI and background listeners
CURRENT_TELEMETRY: Dict[str, Any] = {
    "connected": False,
    "controller_name": "No controller detected",
    "buttons_num": 0,
    "axes_num": 0,
    "hats_num": 0,
    "physical_pressed": [],
    "virtual_pressed": [],
    "lt": 0.0,
    "rt": 0.0,
    "lx": 0.0,
    "ly": 0.0,
    "rx": 0.0,
    "ry": 0.0,
    "last_macro": "",
    "macro_active": False,
    "macro_virtual": []
}

class RemapperEngine(threading.Thread):
    def __init__(self, signals: MappingSignals) -> None:
        super().__init__(daemon=True)
        self.signals = signals
        self.running = False
        self.remapping_active = False
        self._config = EngineConfig()
        self._config_lock = threading.Lock()

        # Virtual pad handle
        self._vpad: vg.VX360Gamepad | None = None

        # Double tap tracking state: {button: last_press_timestamp}
        self._last_press_time: Dict[str, float] = {}
        self._prev_pressed_physical: Set[str] = set()

        # Active macro execution state
        self._active_macro_outputs: List[Dict[str, Any]] = []
        self._last_macro_time: float = 0.0
        self._last_macro_name: str = ""
        self._last_macro_virtual: List[str] = []

        # Trigger calibration state (prevents uninitialized 0.0 reading as 50%)
        self._lt_seen_negative: bool = False
        self._rt_seen_negative: bool = False

        # Pre-indexed macro cache
        self._dt_macros: Dict[str, Dict[str, Any]] = {}
        self._combo_macros: List[Dict[str, Any]] = []

    def update_config(self, cfg: EngineConfig) -> None:
        with self._config_lock:
            self._config = cfg
            # Pre-index double-tap macros for O(1) hot-loop matching
            self._dt_macros = {
                m["trigger_buttons"][0]: m
                for m in cfg.macros
                if m.get("trigger_type") == "double_tap" and m.get("trigger_buttons")
            }
            # Pre-sort combo macros by button count descending
            self._combo_macros = sorted(
                [m for m in cfg.macros if m.get("trigger_type") == "combo"],
                key=lambda m: len(m.get("trigger_buttons", [])),
                reverse=True
            )

    def _get_config(self) -> EngineConfig:
        with self._config_lock:
            return self._config

    def run(self) -> None:
        global CURRENT_TELEMETRY
        self.running = True

        try:
            pygame.init()
            pygame.joystick.init()
        except Exception:
            pass

        last_telemetry_emit = 0.0
        last_hotplug_check = 0.0
        joy: pygame.joystick.Joystick | None = None
        ctrl_name = "Connected Gamepad"

        while self.running:
            now = time.monotonic()
            try:
                pygame.event.pump()
            except Exception:
                pass

            # Hotplug handling: if no joystick, recheck every 0.8s
            if joy is None or pygame.joystick.get_count() == 0:
                if now - last_hotplug_check >= 0.8:
                    last_hotplug_check = now
                    try:
                        pygame.joystick.quit()
                        pygame.joystick.init()
                        if pygame.joystick.get_count() > 0:
                            joy = pygame.joystick.Joystick(0)
                            joy.init()
                            ctrl_name = joy.get_name()
                            CURRENT_TELEMETRY["connected"] = True
                            CURRENT_TELEMETRY["controller_name"] = ctrl_name
                            self.signals.status_updated.emit(f"Connected: '{ctrl_name}'")
                            time.sleep(0.05)
                            pygame.event.pump()
                        else:
                            CURRENT_TELEMETRY["connected"] = False
                            CURRENT_TELEMETRY["controller_name"] = "No controller detected"
                    except Exception:
                        pass

                if joy is None or pygame.joystick.get_count() == 0:
                    time.sleep(0.05)
                    continue

            # Read physical controller inputs
            cfg = self._get_config()
            pressed_physical: Set[str] = set()

            try:
                num_buttons = joy.get_numbuttons()
                num_axes = joy.get_numaxes()
                ctrl_name_lower = (joy.get_name() or "").lower()

                # PlayStation / DirectInput controller detection
                is_playstation = any(k in ctrl_name_lower for k in ("ps4", "ps5", "dualshock", "dualsense", "wireless controller"))

                if is_playstation:
                    ps_button_map = {
                        0: "X", 1: "A", 2: "B", 3: "Y",
                        4: "LB", 5: "RB", 6: "LT", 7: "RT",
                        8: "BACK", 9: "START", 10: "LS", 11: "RS"
                    }
                    for idx, label in ps_button_map.items():
                        if idx < num_buttons and joy.get_button(idx):
                            pressed_physical.add(label)
                else:
                    for idx, label in PHYSICAL_BUTTON_MAP.items():
                        if idx < num_buttons and joy.get_button(idx):
                            pressed_physical.add(label)

                # Read D-Pad (Hat)
                if joy.get_numhats() > 0:
                    hat = joy.get_hat(0)
                    if hat[1] == 1: pressed_physical.add("Up")
                    elif hat[1] == -1: pressed_physical.add("Down")
                    if hat[0] == -1: pressed_physical.add("Left")
                    elif hat[0] == 1: pressed_physical.add("Right")

                # Read Analog Sticks (Canonical: 0=LX, 1=LY, 2=RX, 3=RY)
                lx = joy.get_axis(AXIS_LX) if num_axes > AXIS_LX else 0.0
                ly = joy.get_axis(AXIS_LY) if num_axes > AXIS_LY else 0.0
                rx = joy.get_axis(AXIS_RX) if num_axes > AXIS_RX else 0.0
                ry = joy.get_axis(AXIS_RY) if num_axes > AXIS_RY else 0.0

                # Read Triggers (Canonical: 4=LT, 5=RT)
                raw_lt = joy.get_axis(AXIS_LT) if num_axes > AXIS_LT else 0.0
                raw_rt = joy.get_axis(AXIS_RT) if num_axes > AXIS_RT else 0.0

                # Detect if triggers rest at negative values (-1.0)
                if raw_lt < -0.2:
                    self._lt_seen_negative = True
                if raw_rt < -0.2:
                    self._rt_seen_negative = True

                # Normalize triggers [0.0, 1.0] without uninitialized 0.0 becoming 50%
                if self._lt_seen_negative:
                    lt_val = max(0.0, min(1.0, (raw_lt + 1.0) / 2.0))
                else:
                    lt_val = max(0.0, min(1.0, raw_lt)) if raw_lt > 0.05 else 0.0

                if self._rt_seen_negative:
                    rt_val = max(0.0, min(1.0, (raw_rt + 1.0) / 2.0))
                else:
                    rt_val = max(0.0, min(1.0, raw_rt)) if raw_rt > 0.05 else 0.0

                # If digital button was pressed for LT/RT, treat as 100% pressed
                if "LT" in pressed_physical and lt_val < 0.5:
                    lt_val = 1.0
                if "RT" in pressed_physical and rt_val < 0.5:
                    rt_val = 1.0

                if lt_val > TRIGGER_DIGITAL_THRESHOLD:
                    pressed_physical.add("LT")
                if rt_val > TRIGGER_DIGITAL_THRESHOLD:
                    pressed_physical.add("RT")
            except Exception:
                joy = None
                continue

            # ─── 2. Evaluate Macros (Double-Tap & Combos) ────────────
            newly_pressed = pressed_physical - self._prev_pressed_physical
            triggered_macro_buttons: Set[str] = set()
            macro_produced_virtual: Set[str] = set()
            active_macro_name = ""

            # Fast Double-Tap evaluation: O(1) matching on newly pressed keys
            for btn in newly_pressed:
                macro = self._dt_macros.get(btn)
                if macro:
                    last_t = self._last_press_time.get(btn, 0.0)
                    if (now - last_t) <= DOUBLE_TAP_WINDOW:
                        hold_sec = macro.get("hold_duration_ms", 120) / 1000.0
                        for out_btn in macro.get("output_sequence", []):
                            self._active_macro_outputs.append({
                                "button": out_btn,
                                "release_time": now + hold_sec,
                                "name": macro.get("name", "Double-Tap")
                            })
                        triggered_macro_buttons.add(btn)
                        self._last_press_time[btn] = 0.0
                        active_macro_name = macro.get("name", "Double-Tap")
                        self._last_macro_time = now
                        self._last_macro_name = active_macro_name
                        self._last_macro_virtual = list(macro.get("output_sequence", []))
                    else:
                        self._last_press_time[btn] = now

            # Fast Combo evaluation: sorted by longest trigger combinations
            for macro in self._combo_macros:
                m_trigs = macro.get("trigger_buttons", [])
                if m_trigs and all(b in pressed_physical for b in m_trigs):
                    for out_btn in macro.get("output_sequence", []):
                        macro_produced_virtual.add(out_btn)
                    triggered_macro_buttons.update(m_trigs)
                    active_macro_name = macro.get("name", "Combo")
                    self._last_macro_time = now
                    self._last_macro_name = active_macro_name
                    self._last_macro_virtual = list(macro.get("output_sequence", []))
                    break

            self._prev_pressed_physical = pressed_physical

            # Check active timed macro outputs
            still_active_macros = []
            for item in self._active_macro_outputs:
                if now < item["release_time"]:
                    macro_produced_virtual.add(item["button"])
                    still_active_macros.append(item)
                    active_macro_name = item.get("name", active_macro_name)
                    self._last_macro_time = now
                    self._last_macro_name = active_macro_name
            self._active_macro_outputs = still_active_macros

            # ─── 3. Standard Profile Remapping ───────────────────────
            pressed_virtual: Set[str] = set(macro_produced_virtual)

            for phys_btn in pressed_physical:
                if phys_btn in triggered_macro_buttons:
                    continue
                target_virt = cfg.button_mapping.get(phys_btn, phys_btn)
                pressed_virtual.add(target_virt)

            # ─── 4. Push Output to Virtual Gamepad (if remapping is active) ───
            if self.remapping_active:
                if self._vpad is None:
                    try:
                        self._vpad = vg.VX360Gamepad()
                    except Exception as exc:
                        self.signals.status_updated.emit(f"ViGEmBus Note: {exc}")

                if self._vpad is not None:
                    for label, btn_flag in VG_BUTTONS.items():
                        if label in TRIGGER_LABELS:
                            continue
                        if label in pressed_virtual:
                            self._vpad.press_button(button=btn_flag)
                        else:
                            self._vpad.release_button(button=btn_flag)

                    v_lt = (lt_val if "LT" in pressed_physical else 1.0) if "LT" in pressed_virtual else 0.0
                    v_rt = (rt_val if "RT" in pressed_physical else 1.0) if "RT" in pressed_virtual else 0.0
                    self._vpad.left_trigger_float(value_float=v_lt)
                    self._vpad.right_trigger_float(value_float=v_rt)

                    self._vpad.left_joystick_float(
                        x_value_float=max(-1.0, min(1.0, lx)),
                        y_value_float=max(-1.0, min(1.0, -ly))
                    )
                    self._vpad.right_joystick_float(
                        x_value_float=max(-1.0, min(1.0, rx)),
                        y_value_float=max(-1.0, min(1.0, -ry))
                    )
                    self._vpad.update()

            # Linger macro display (~850ms)
            macro_active_state = (now - self._last_macro_time) < 0.85
            display_macro_name = self._last_macro_name if macro_active_state else ""
            display_macro_virtual = self._last_macro_virtual if macro_active_state else []

            # ─── 5. Update Telemetry Broadcast (~30 Hz) ─────────────
            if now - last_telemetry_emit >= 0.033:
                last_telemetry_emit = now
                telemetry_payload = {
                    "connected": True,
                    "controller_name": ctrl_name,
                    "physical_pressed": sorted(list(pressed_physical)),
                    "virtual_pressed": sorted(list(pressed_virtual)),
                    "lt": round(lt_val, 2),
                    "rt": round(rt_val, 2),
                    "lx": round(lx, 2),
                    "ly": round(ly, 2),
                    "rx": round(rx, 2),
                    "ry": round(ry, 2),
                    "last_macro": display_macro_name,
                    "macro_active": macro_active_state,
                    "macro_virtual": sorted(list(set(display_macro_virtual)))
                }
                CURRENT_TELEMETRY.update(telemetry_payload)
                self.signals.telemetry_updated.emit(telemetry_payload)

            time.sleep(ENGINE_POLL_INTERVAL)

    def stop(self) -> None:
        global CURRENT_TELEMETRY
        self.running = False
        CURRENT_TELEMETRY["physical_pressed"] = []
        CURRENT_TELEMETRY["virtual_pressed"] = []
        CURRENT_TELEMETRY["last_macro"] = ""
        CURRENT_TELEMETRY["macro_active"] = False
        CURRENT_TELEMETRY["macro_virtual"] = []
        time.sleep(ENGINE_POLL_INTERVAL * 2)
        try:
            pygame.quit()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
