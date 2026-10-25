"""
engine.py – Universal High-Performance Gamepad Remapper & Macro Engine
=======================================================================
Runs a 125 Hz translation loop (~8 ms per tick) bridging physical gamepad
(e.g., Cosmic Byte Ares Pro) to a ViGEmBus Virtual Xbox 360 controller for
GeForce NOW or any Windows game.

Features:
  - 1:1 customizable button remapping per game profile
  - Macro execution:
      * Double-tap detection (e.g. double-tap B -> dodge or sequence)
      * Multi-button combos (e.g. LB + X -> instant RT sign cast or complex macro)
  - Full analog trigger gradient handling (0.0 to 1.0)
  - Stick deadzones and axis normalization
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
    input_activity = pyqtSignal(str)  # Sends real-time detected button labels to UI

@dataclass
class EngineConfig:
    # Physical Button -> Virtual Target Button (e.g. {"A": "A", "B": "X", ...})
    button_mapping: Dict[str, str] = field(default_factory=dict)
    # List of macros defined for this profile
    macros: List[Dict[str, Any]] = field(default_factory=list)

class RemapperEngine(threading.Thread):
    def __init__(self, signals: MappingSignals) -> None:
        super().__init__(daemon=True)
        self.signals = signals
        self.running = False
        self._config = EngineConfig()
        self._config_lock = threading.Lock()

        # Virtual pad handle
        self._vpad: vg.VX360Gamepad | None = None

        # Double tap tracking state: {button: last_press_timestamp}
        self._last_press_time: Dict[str, float] = {}
        self._prev_pressed_physical: Set[str] = set()

        # Active macro execution state: list of dicts
        # [{ "buttons": ['RT'], "release_time": float }]
        self._active_macro_outputs: List[Dict[str, Any]] = []

    def update_config(self, cfg: EngineConfig) -> None:
        with self._config_lock:
            self._config = cfg

    def _get_config(self) -> EngineConfig:
        with self._config_lock:
            return self._config

    def run(self) -> None:
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.signals.status_updated.emit("Error: No physical controller found.")
            return

        # Initialize physical gamepad FIRST
        joy = pygame.joystick.Joystick(0)
        joy.init()

        # Create virtual Xbox 360 controller
        try:
            self._vpad = vg.VX360Gamepad()
        except Exception as exc:
            self.signals.status_updated.emit(f"ViGEmBus Error: {exc}")
            return

        self.running = True
        self.signals.status_updated.emit(f"Active -- Remapping '{joy.get_name()}' -> Virtual Xbox 360")

        # Prime event pump to calibrate resting axis baseline
        pygame.event.pump()
        time.sleep(0.05)

        while self.running:
            pygame.event.pump()
            cfg = self._get_config()
            now = time.monotonic()

            # ─── 1. Read Physical Controller Inputs ──────────────────
            pressed_physical: Set[str] = set()

            # Read digital buttons
            for idx, label in PHYSICAL_BUTTON_MAP.items():
                if idx < joy.get_numbuttons() and joy.get_button(idx):
                    pressed_physical.add(label)

            # Read D-Pad (Hat)
            if joy.get_numhats() > 0:
                hat = joy.get_hat(0)
                if hat[1] == 1: pressed_physical.add("Up")
                elif hat[1] == -1: pressed_physical.add("Down")
                if hat[0] == -1: pressed_physical.add("Left")
                elif hat[0] == 1: pressed_physical.add("Right")

            # Read and Normalize Triggers [-1.0, 1.0] -> [0.0, 1.0]
            raw_lt = joy.get_axis(AXIS_LT) if joy.get_numaxes() > AXIS_LT else -1.0
            raw_rt = joy.get_axis(AXIS_RT) if joy.get_numaxes() > AXIS_RT else -1.0
            lt_val = max(0.0, min(1.0, (raw_lt + 1.0) / 2.0))
            rt_val = max(0.0, min(1.0, (raw_rt + 1.0) / 2.0))

            if lt_val > TRIGGER_DIGITAL_THRESHOLD:
                pressed_physical.add("LT")
            if rt_val > TRIGGER_DIGITAL_THRESHOLD:
                pressed_physical.add("RT")

            # Read Analog Sticks
            lx = joy.get_axis(AXIS_LX) if joy.get_numaxes() > AXIS_LX else 0.0
            ly = joy.get_axis(AXIS_LY) if joy.get_numaxes() > AXIS_LY else 0.0
            rx = joy.get_axis(AXIS_RX) if joy.get_numaxes() > AXIS_RX else 0.0
            ry = joy.get_axis(AXIS_RY) if joy.get_numaxes() > AXIS_RY else 0.0

            # ─── 2. Evaluate Macros (Double-Tap & Combos) ────────────
            # Detect rising edges (buttons newly pressed this frame)
            newly_pressed = pressed_physical - self._prev_pressed_physical
            triggered_macro_buttons: Set[str] = set()
            macro_produced_virtual: Set[str] = set()

            for macro in cfg.macros:
                m_type = macro.get("trigger_type", "")
                m_trigs = macro.get("trigger_buttons", [])
                m_out = macro.get("output_sequence", [])
                hold_sec = macro.get("hold_duration_ms", 120) / 1000.0

                if m_type == "double_tap" and len(m_trigs) == 1:
                    btn = m_trigs[0]
                    if btn in newly_pressed:
                        last_t = self._last_press_time.get(btn, 0.0)
                        if (now - last_t) <= DOUBLE_TAP_WINDOW:
                            # Double-tap detected!
                            for out_btn in m_out:
                                self._active_macro_outputs.append({
                                    "button": out_btn,
                                    "release_time": now + hold_sec
                                })
                            triggered_macro_buttons.add(btn)
                            self._last_press_time[btn] = 0.0  # reset
                        else:
                            self._last_press_time[btn] = now

                elif m_type == "combo" and len(m_trigs) >= 2:
                    # All combo trigger buttons must be pressed
                    if all(b in pressed_physical for b in m_trigs):
                        for out_btn in m_out:
                            macro_produced_virtual.add(out_btn)
                        # Suppress individual buttons involved in the combo
                        triggered_macro_buttons.update(m_trigs)

            self._prev_pressed_physical = pressed_physical

            # Check active timed macro outputs
            still_active_macros = []
            for item in self._active_macro_outputs:
                if now < item["release_time"]:
                    macro_produced_virtual.add(item["button"])
                    still_active_macros.append(item)
            self._active_macro_outputs = still_active_macros

            # ─── 3. Standard Profile Remapping ───────────────────────
            pressed_virtual: Set[str] = set(macro_produced_virtual)

            for phys_btn in pressed_physical:
                if phys_btn in triggered_macro_buttons:
                    continue  # Intercepted by macro
                target_virt = cfg.button_mapping.get(phys_btn, phys_btn)
                pressed_virtual.add(target_virt)

            # ─── 4. Push Output to Virtual Gamepad ───────────────────
            for label, btn_flag in VG_BUTTONS.items():
                if label in TRIGGER_LABELS:
                    continue
                if label in pressed_virtual:
                    self._vpad.press_button(button=btn_flag)
                else:
                    self._vpad.release_button(button=btn_flag)

            # Forward analog triggers
            v_lt = (lt_val if "LT" in pressed_physical else 1.0) if "LT" in pressed_virtual else 0.0
            v_rt = (rt_val if "RT" in pressed_physical else 1.0) if "RT" in pressed_virtual else 0.0
            self._vpad.left_trigger_float(value_float=v_lt)
            self._vpad.right_trigger_float(value_float=v_rt)

            # Forward analog joysticks (Pygame Y is inverted vs XInput)
            self._vpad.left_joystick_float(
                x_value_float=max(-1.0, min(1.0, lx)),
                y_value_float=max(-1.0, min(1.0, -ly))
            )
            self._vpad.right_joystick_float(
                x_value_float=max(-1.0, min(1.0, rx)),
                y_value_float=max(-1.0, min(1.0, -ry))
            )

            self._vpad.update()
            time.sleep(ENGINE_POLL_INTERVAL)

    def stop(self) -> None:
        self.running = False
        time.sleep(ENGINE_POLL_INTERVAL * 2)
        try:
            pygame.quit()
        except Exception:
            pass
