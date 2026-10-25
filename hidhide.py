"""
hidhide.py – Direct HidHide CLI Integration
============================================
Handles automatic hiding/unhiding of physical controllers using HidHideCLI.exe.
When cloaking is ON:
  - The physical gamepad is hidden from GeForce NOW and all standard apps.
  - Python is registered in the whitelist so the remapper can still read it.
  - GeForce NOW only sees the virtual Xbox 360 controller created by vgamepad.
"""

import os
import sys
import ctypes
import subprocess
from pathlib import Path

HIDHIDE_CLI_PATH = Path(r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe")

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def is_hidhide_available() -> bool:
    return HIDHIDE_CLI_PATH.exists()

def run_hidhide_cmd(arguments: list[str]) -> bool:
    """Execute HidHideCLI command, elevating via UAC if not currently admin."""
    if not is_hidhide_available():
        return False

    args_str = " ".join(f'"{a}"' if " " in a else a for a in arguments)

    if is_admin():
        try:
            res = subprocess.run(
                [str(HIDHIDE_CLI_PATH)] + arguments,
                capture_output=True,
                text=True,
                shell=False
            )
            return res.returncode == 0
        except Exception:
            return False
    else:
        # Launch elevated via PowerShell Start-Process -Verb RunAs
        ps_cmd = (
            f'Start-Process -FilePath "{HIDHIDE_CLI_PATH}" '
            f'-ArgumentList \'{args_str}\' -Verb RunAs -WindowStyle Hidden -Wait'
        )
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            return res.returncode == 0
        except Exception:
            return False

def setup_hidhide_for_remapper() -> bool:
    """
    1. Whitelist python.exe in HidHide so the remapper retains access.
    2. Cloak physical gaming devices so GeForce NOW cannot see them.
    """
    if not is_hidhide_available():
        return False

    python_exe = sys.executable

    # Batch setup script to perform all steps in a single elevated UAC prompt
    script = (
        f'& "{HIDHIDE_CLI_PATH}" --app-reg "{python_exe}"; '
        f'$devs = & "{HIDHIDE_CLI_PATH}" --dev-gaming; '
        f'foreach ($d in $devs) {{ if ($d -match "HID\\\\") {{ & "{HIDHIDE_CLI_PATH}" --dev-hide "$d" }} }}; '
        f'& "{HIDHIDE_CLI_PATH}" --cloak-on'
    )

    if is_admin():
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)
            return True
        except Exception:
            return False
    else:
        ps_cmd = f'Start-Process powershell -ArgumentList \'-NoProfile -Command "{script}"\' -Verb RunAs -WindowStyle Hidden -Wait'
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            return True
        except Exception:
            return False

def disable_hidhide_cloaking() -> bool:
    """Disable cloaking when the remapper stops."""
    return run_hidhide_cmd(["--cloak-off"])

def enable_hidhide_cloaking() -> bool:
    """Re-enable cloaking."""
    return run_hidhide_cmd(["--cloak-on"])
