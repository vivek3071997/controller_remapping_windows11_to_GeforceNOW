"""
engine.py – Translation Engine (RemapperEngine)
================================================
Runs in a daemon thread.  Every tick (~8 ms / 125 Hz):

  1. Reads raw physical controller state via pygame.
  2. Converts each physical button/hat/trigger to a canonical label
     ("A", "B", "LT", etc.).
  3. Walks the UI mapping table — for every *game action* whose
     *physical source* is currently pressed, marks the corresponding
     *virtual target* as active.
  4. Applies advanced toggle overrides (throw aiming, dodge↔roll swap,
     horse acceleration).
  5. Pushes the accumulated virtual state into vgamepad's VX360Gamepad.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

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
    DEFAULT_MAPPING,
    DOUBLE_TAP_WINDOW,
    ENGINE_POLL_INTERVAL,
    HORSE_ACCEL_STICK_THRESHOLD,
    PHYSICAL_BUTTON_MAP,
    TRIGGER_DIGITAL_THRESHOLD,
    TRIGGER_LABELS,
    VG_BUTTONS,
)


# ──────────────────────────────────────────────────────────────────────
# Qt signal carrier — thread-safe bridge from engine → UI
# ──────────────────────────────────────────────────────────────────────
class MappingSignals(QObject):
    status_updated = pyqtSignal(str)


# ──────────────────────────────────────────────────────────────────────
# Engine configuration snapshot (immutable between apply() calls)
# ──────────────────────────────────────────────────────────────────────
@dataclass
class EngineConfig:
    """Passed from the UI thread to the engine via update_config()."""

    # action → virtual button label, e.g. {"Heavy Attack": "Y", …}
    mapping: dict[str, str] = field(default_factory=lambda: DEFAULT_MAPPING.copy())
    toggle_throw_aim: bool = False
    toggle_swap_dodge: bool = False
    toggle_horse_accel: bool = False


# ──────────────────────────────────────────────────────────────────────
# The engine itself
# ──────────────────────────────────────────────────────────────────────
class RemapperEngine(threading.Thread):
    """Daemon thread that bridges physical → virtual controller."""

    def __init__(self, signals: MappingSignals) -> None:
        super().__init__(daemon=True)
        self.signals = signals
        self.running = False
        self._config = EngineConfig()
        self._config_lock = threading.Lock()

        # Virtual pad handle (created inside run())
        self._vpad: vg.VX360Gamepad | None = None

        # ── State for double-tap dodge detection ──
        self._dodge_last_press_time: float = 0.0
        self._dodge_was_pressed: bool = False   # edge tracking
        self._dodge_tap_count: int = 0

        # ── State for horse acceleration automation ──
        self._horse_tap_active: bool = False
        self._horse_next_toggle: float = 0.0
        self._horse_tap_interval: float = 0.22  # seconds between taps

    # ── Thread-safe config hot-swap ─────────────────────────────────
    def update_config(self, cfg: EngineConfig) -> None:
        with self._config_lock:
            self._config = cfg

    def _get_config(self) -> EngineConfig:
        with self._config_lock:
            return self._config

    # ── Build the *reverse* lookup table ────────────────────────────
    @staticmethod
    def _build_reverse_map(
        mapping: dict[str, str],
    ) -> dict[str, str]:
        """Return {physical_label → virtual_label} for every mapping entry.

        The UI mapping is  action → virtual_target  (e.g. "Heavy Attack" → "Y").
        The *default* physical binding for each action mirrors the default
        mapping table:  the physical button whose DEFAULT mapping matches
        the action is the one that triggers it.

        So "Heavy Attack" has default target "Y".  The physical button that
        *by default* emits "Y" is pygame button 3 (label "Y").

        When the user reassigns "Heavy Attack" to, say, "RB", the physical
        button that fires "Heavy Attack" stays the *same hardware key* (Y on
        the pad) — but the virtual output changes to RB.

        Therefore:  physical_label → virtual_label  is built by:
            for each (action, virtual) in mapping:
                physical = DEFAULT_MAPPING[action]   # what key fires this action
                result[physical] = virtual
        """
        reverse: dict[str, str] = {}
        for action, virtual_target in mapping.items():
            physical_source = DEFAULT_MAPPING.get(action)
            if physical_source is not None:
                reverse[physical_source] = virtual_target
        return reverse

    # ── Main loop ───────────────────────────────────────────────────
    def run(self) -> None:  # noqa: C901 (complexity is inherent)
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.signals.status_updated.emit(
                "Error: No physical controller detected.  "
                "Connect the Cosmic Byte Ares Pro and restart."
            )
            return

        joy = pygame.joystick.Joystick(0)
        joy.init()

        try:
            self._vpad = vg.VX360Gamepad()
        except Exception as exc:
            self.signals.status_updated.emit(
                f"Driver Error (is ViGEmBus installed?): {exc}"
            )
            return

        self.running = True
        self.signals.status_updated.emit(
            f"Active -- intercepting '{joy.get_name()}' -> Virtual Xbox 360"
        )

        while self.running:
            pygame.event.pump()
            cfg = self._get_config()
            reverse = self._build_reverse_map(cfg.mapping)

            # ─── 1. Read raw physical state ─────────────────────────
            pressed_physical: set[str] = set()

            # Digital buttons
            for idx, label in PHYSICAL_BUTTON_MAP.items():
                if idx < joy.get_numbuttons() and joy.get_button(idx):
                    pressed_physical.add(label)

            # D-pad (hat)
            if joy.get_numhats() > 0:
                hat = joy.get_hat(0)
                if hat[1] == 1:
                    pressed_physical.add("Up")
                if hat[1] == -1:
                    pressed_physical.add("Down")
                if hat[0] == -1:
                    pressed_physical.add("Left")
                if hat[0] == 1:
                    pressed_physical.add("Right")

            # Analog triggers treated as digital buttons
            if joy.get_numaxes() > AXIS_LT and joy.get_axis(AXIS_LT) > TRIGGER_DIGITAL_THRESHOLD:
                pressed_physical.add("LT")
            if joy.get_numaxes() > AXIS_RT and joy.get_axis(AXIS_RT) > TRIGGER_DIGITAL_THRESHOLD:
                pressed_physical.add("RT")

            # Raw analog axes (sticks)
            lx = joy.get_axis(AXIS_LX) if joy.get_numaxes() > AXIS_LX else 0.0
            ly = joy.get_axis(AXIS_LY) if joy.get_numaxes() > AXIS_LY else 0.0
            rx = joy.get_axis(AXIS_RX) if joy.get_numaxes() > AXIS_RX else 0.0
            ry = joy.get_axis(AXIS_RY) if joy.get_numaxes() > AXIS_RY else 0.0

            # ─── 2. Translate through mapping matrix ────────────────
            pressed_virtual: set[str] = set()

            for phys_label in pressed_physical:
                virt_label = reverse.get(phys_label, phys_label)
                pressed_virtual.add(virt_label)

            # ─── 3. Advanced toggle overrides ───────────────────────

            # 3a. Swap Dodge ↔ Roll
            if cfg.toggle_swap_dodge:
                dodge_virt = cfg.mapping.get("Dodge / Dive Up / Jump", "B")
                roll_virt = cfg.mapping.get("Interact / Roll / Horse Acceleration", "A")
                new_pressed: set[str] = set()
                for v in pressed_virtual:
                    if v == dodge_virt:
                        new_pressed.add(roll_virt)
                    elif v == roll_virt:
                        new_pressed.add(dodge_virt)
                    else:
                        new_pressed.add(v)
                pressed_virtual = new_pressed

            # 3b. Throw-aim: redirect left stick → virtual right stick
            throw_btn = cfg.mapping.get("Throw Item", "RB")
            override_sticks = cfg.toggle_throw_aim and throw_btn in pressed_virtual
            if override_sticks:
                # Physical left stick drives virtual right stick
                aim_rx, aim_ry = lx, ly
                # Center virtual left stick so the character stays still
                out_lx, out_ly = 0.0, 0.0
                out_rx, out_ry = aim_rx, aim_ry
            else:
                out_lx, out_ly = lx, ly
                out_rx, out_ry = rx, ry

            # 3c. Horse acceleration on left-stick forward
            #     When enabled and the left stick is pushed hard forward,
            #     we rhythmically tap the virtual A button.
            if cfg.toggle_horse_accel and ly < HORSE_ACCEL_STICK_THRESHOLD:
                now = time.monotonic()
                if now >= self._horse_next_toggle:
                    self._horse_tap_active = not self._horse_tap_active
                    self._horse_next_toggle = now + self._horse_tap_interval
                if self._horse_tap_active:
                    pressed_virtual.add("A")
                else:
                    pressed_virtual.discard("A")
            else:
                self._horse_tap_active = False
                self._horse_next_toggle = 0.0

            # 3d. Double-tap dodge detection
            #     If the physical dodge button is tapped twice within
            #     DOUBLE_TAP_WINDOW, we emit the dodge virtual output
            #     as a *held press* for 150 ms to ensure in-game registration.
            dodge_phys = DEFAULT_MAPPING.get("Dodge / Dive Up / Jump", "B")
            dodge_currently_pressed = dodge_phys in pressed_physical
            if dodge_currently_pressed and not self._dodge_was_pressed:
                # Rising edge
                now = time.monotonic()
                if now - self._dodge_last_press_time <= DOUBLE_TAP_WINDOW:
                    self._dodge_tap_count += 1
                else:
                    self._dodge_tap_count = 1
                self._dodge_last_press_time = now
            self._dodge_was_pressed = dodge_currently_pressed

            # ─── 4. Push to virtual controller ──────────────────────
            for label, btn_flag in VG_BUTTONS.items():
                if label in TRIGGER_LABELS:
                    continue  # handled as analog below
                if label in pressed_virtual:
                    self._vpad.press_button(button=btn_flag)
                else:
                    self._vpad.release_button(button=btn_flag)

            # Analog triggers
            self._vpad.left_trigger_float(
                value_float=1.0 if "LT" in pressed_virtual else 0.0
            )
            self._vpad.right_trigger_float(
                value_float=1.0 if "RT" in pressed_virtual else 0.0
            )

            # Analog sticks (pygame Y axis is inverted vs XInput)
            self._vpad.left_joystick_float(
                x_value_float=self._clamp(out_lx),
                y_value_float=self._clamp(-out_ly),
            )
            self._vpad.right_joystick_float(
                x_value_float=self._clamp(out_rx),
                y_value_float=self._clamp(-out_ry),
            )

            self._vpad.update()
            time.sleep(ENGINE_POLL_INTERVAL)

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    def stop(self) -> None:
        self.running = False
        # Give the loop one tick to exit cleanly
        time.sleep(ENGINE_POLL_INTERVAL * 2)
        try:
            pygame.quit()
        except Exception:
            pass
