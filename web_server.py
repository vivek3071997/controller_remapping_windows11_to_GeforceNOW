"""
web_server.py – Web-Based Management UI & REST API for GeForce NOW Controller Remapper PC
========================================================================================
Serves a responsive modern Web Dashboard accessible from any browser
(http://localhost:5000), allowing full control over game profiles,
1:1 button remaps, combo/double-tap macros, and live remapper engine control.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from flask import Flask, jsonify, request, render_template

from constants import BUTTON_OPTIONS
from profiles import ProfileManager, GameProfile, CONTROLLER_BUTTONS, sanitize_mapping
from engine import RemapperEngine, EngineConfig, MappingSignals
import hidhide

# Flask application configured with template and static folders
BASE_DIR = Path(__file__).parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

profile_mgr = ProfileManager()
engine_lock = threading.Lock()
engine_instance: RemapperEngine | None = None
engine_status = "Stopped"

class WebSignals(MappingSignals):
    def __init__(self):
        super().__init__()
        self.status_updated.connect(self._on_status)

    def _on_status(self, msg: str):
        global engine_status
        engine_status = msg

signals = WebSignals()

@app.route("/")
def index():
    return render_template(
        "dashboard.html",
        button_options=BUTTON_OPTIONS,
        controller_buttons=CONTROLLER_BUTTONS
    )

@app.route("/api/profiles")
def get_profiles():
    profile_mgr.load_profiles()
    return jsonify({
        p.name: {
            "name": p.name,
            "description": p.description,
            "button_mapping": p.button_mapping,
            "button_actions": p.button_actions,
            "macros": p.macros
        }
        for p in profile_mgr.profiles.values()
    })

@app.route("/api/profiles/save", methods=["POST"])
def save_profile():
    data = request.json or {}
    profile = GameProfile(
        name=data["name"],
        description=data.get("description", ""),
        button_mapping=sanitize_mapping(data.get("button_mapping", {})),
        button_actions=data.get("button_actions", {}),
        macros=data.get("macros", [])
    )
    profile_mgr.save_profile(profile)

    # Hot update engine if running
    global engine_instance
    with engine_lock:
        if engine_instance and engine_instance.running:
            engine_instance.update_config(EngineConfig(
                button_mapping=profile.button_mapping,
                macros=profile.macros
            ))

    return jsonify({"success": True})

@app.route("/api/profiles/delete", methods=["POST"])
def delete_profile():
    name = request.args.get("name", "")
    success = profile_mgr.delete_profile(name)
    return jsonify({"success": success})

def init_web_background_engine():
    """Initializes the background test monitor at launch so the visualizer is immediately live."""
    global engine_instance, engine_status
    with engine_lock:
        if engine_instance is None:
            engine_instance = RemapperEngine(signals)
            engine_instance.remapping_active = False
            profile_mgr.load_profiles()
            active_p = profile_mgr.get_profile("The Witcher 3: Wild Hunt") or next(iter(profile_mgr.profiles.values()), None)
            if active_p:
                engine_instance.update_config(EngineConfig(
                    button_mapping=active_p.button_mapping,
                    macros=active_p.macros
                ))
            engine_instance.start()
            engine_status = "Monitor Mode (Hardware visualizer active)"

@app.route("/api/engine/status")
def get_engine_status():
    global engine_instance, engine_status
    with engine_lock:
        running = engine_instance is not None and getattr(engine_instance, "remapping_active", False)
    from engine import CURRENT_TELEMETRY
    return jsonify({
        "running": running,
        "status": engine_status,
        "telemetry": CURRENT_TELEMETRY
    })

@app.route("/api/engine/toggle", methods=["POST"])
def toggle_engine():
    global engine_instance, engine_status
    data = request.json or {}
    p_name = data.get("profile_name", "")
    use_hidhide = data.get("use_hidhide", True)

    with engine_lock:
        if engine_instance is None or not engine_instance.running:
            engine_instance = RemapperEngine(signals)
            engine_instance.remapping_active = False
            engine_instance.start()

        if engine_instance.remapping_active:
            engine_instance.remapping_active = False
            if use_hidhide and hidhide.is_hidhide_available():
                hidhide.disable_hidhide_cloaking()
            engine_status = "Monitor Mode (Remapping Paused)"
        else:
            profile = profile_mgr.get_profile(p_name)
            if use_hidhide and hidhide.is_hidhide_available():
                engine_status = "Cloaking physical controller with HidHide..."
                hidhide.setup_hidhide_for_remapper()

            engine_instance.update_config(EngineConfig(
                button_mapping=profile.button_mapping,
                macros=profile.macros
            ))
            engine_instance.remapping_active = True
            engine_status = f"Active -- Streaming '{profile.name}' to Virtual Xbox 360"

    return jsonify({"success": True})

def start_web_server(port: int = 5000):
    init_web_background_engine()
    print(f"[*] Starting GeForce NOW Controller Remapper PC Web UI at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_web_server()
