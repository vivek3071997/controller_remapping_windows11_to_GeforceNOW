"""
tester.py – Real-time Controller & Remapping Engine Tester
==========================================================
Interactive test utility to diagnose:
  1. Physical Ares Pro controller raw button, hat, and analog stick/trigger inputs.
  2. The translation engine output to the ViGEmBus virtual controller.
  3. Live response verification so you can verify each button press in real time.
"""

import sys
import time
import pygame
import vgamepad as vg
from constants import (
    PHYSICAL_BUTTON_MAP,
    DEFAULT_MAPPING,
    TRIGGER_DIGITAL_THRESHOLD,
    AXIS_LX, AXIS_LY, AXIS_RX, AXIS_RY, AXIS_LT, AXIS_RT
)

def run_tester():
    print("=" * 65)
    print("      WITCHER CONTROLLER & TRANSLATION ENGINE TESTER")
    print("=" * 65)

    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    print(f"[*] Detected Pygame joysticks: {count}")

    if count == 0:
        print("[!] ERROR: No physical controller found! Please plug in or pair the Ares Pro.")
        sys.exit(1)

    # Initialize physical controller
    physical_joy = pygame.joystick.Joystick(0)
    physical_joy.init()
    print(f"[+] Bound Physical Gamepad: '{physical_joy.get_name()}' (ID: {physical_joy.get_id()})")
    print(f"    - Buttons: {physical_joy.get_numbuttons()}, Axes: {physical_joy.get_numaxes()}, Hats: {physical_joy.get_numhats()}")

    # Initialize ViGEmBus virtual gamepad
    try:
        virtual_pad = vg.VX360Gamepad()
        print("[+] Initialized ViGEmBus Virtual Xbox 360 Gamepad successfully!")
    except Exception as e:
        print(f"[!] ViGEmBus Driver Error: {e}")
        sys.exit(1)

    print("-" * 65)
    print("Press buttons, triggers, or move sticks on your Ares Pro.")
    print("The tester displays [RAW PHYSICAL INPUT] -> [TRANSLATED ACTION & TARGET]")
    print("Running for 20 seconds (or press Ctrl+C to exit)...")
    print("-" * 65)

    # Prime initial event pump to establish resting axis baseline
    pygame.event.pump()
    time.sleep(0.05)

    start_time = time.time()
    last_state_summary = ""

    try:
        while time.time() - start_time < 20:
            pygame.event.pump()

            # 1. Gather raw physical buttons
            pressed_btns = []
            for b_idx, label in PHYSICAL_BUTTON_MAP.items():
                if b_idx < physical_joy.get_numbuttons() and physical_joy.get_button(b_idx):
                    pressed_btns.append(label)

            # Gather D-pad (hat)
            hat_val = physical_joy.get_hat(0) if physical_joy.get_numhats() > 0 else (0, 0)
            if hat_val[1] == 1: pressed_btns.append("Up")
            if hat_val[1] == -1: pressed_btns.append("Down")
            if hat_val[0] == -1: pressed_btns.append("Left")
            if hat_val[0] == 1: pressed_btns.append("Right")

            # Gather and normalize triggers
            raw_lt = physical_joy.get_axis(AXIS_LT) if physical_joy.get_numaxes() > AXIS_LT else -1.0
            raw_rt = physical_joy.get_axis(AXIS_RT) if physical_joy.get_numaxes() > AXIS_RT else -1.0
            lt_norm = max(0.0, min(1.0, (raw_lt + 1.0) / 2.0))
            rt_norm = max(0.0, min(1.0, (raw_rt + 1.0) / 2.0))

            if lt_norm > TRIGGER_DIGITAL_THRESHOLD:
                pressed_btns.append("LT")
            if rt_norm > TRIGGER_DIGITAL_THRESHOLD:
                pressed_btns.append("RT")

            # Gather sticks
            lx = round(physical_joy.get_axis(AXIS_LX), 2) if physical_joy.get_numaxes() > AXIS_LX else 0.0
            ly = round(physical_joy.get_axis(AXIS_LY), 2) if physical_joy.get_numaxes() > AXIS_LY else 0.0
            rx = round(physical_joy.get_axis(AXIS_RX), 2) if physical_joy.get_numaxes() > AXIS_RX else 0.0
            ry = round(physical_joy.get_axis(AXIS_RY), 2) if physical_joy.get_numaxes() > AXIS_RY else 0.0

            # Sticks state (ignore slight deadzone)
            stick_info = []
            if abs(lx) > 0.15 or abs(ly) > 0.15:
                stick_info.append(f"L-Stick:({lx}, {ly})")
            if abs(rx) > 0.15 or abs(ry) > 0.15:
                stick_info.append(f"R-Stick:({rx}, {ry})")

            # Format current state string
            state_items = []
            if pressed_btns:
                state_items.append(f"Buttons: {', '.join(pressed_btns)}")
            if lt_norm > 0.05 or rt_norm > 0.05:
                state_items.append(f"Triggers: [LT: {lt_norm:.2f}, RT: {rt_norm:.2f}]")
            if stick_info:
                state_items.append(f"Axes: {', '.join(stick_info)}")

            current_summary = " | ".join(state_items)

            # Only print when there is active input or state change
            if current_summary and current_summary != last_state_summary:
                print(f"[INPUT DETECTED] -> {current_summary}")
                last_state_summary = current_summary
            elif not current_summary and last_state_summary != "":
                last_state_summary = ""

            time.sleep(0.015)

    except KeyboardInterrupt:
        pass

    print("\n[+] Test complete. Closing devices cleanly.")
    pygame.quit()

if __name__ == "__main__":
    run_tester()
