"""
web_server.py – Web-Based Management UI & REST API for Apex Remapper
====================================================================
Serves a responsive modern Web Dashboard accessible from any browser
(http://localhost:5000), allowing full control over game profiles,
1:1 button remaps, combo/double-tap macros, and live remapper engine control.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string

from constants import BUTTON_OPTIONS
from profiles import ProfileManager, GameProfile, CONTROLLER_BUTTONS
from engine import RemapperEngine, EngineConfig, MappingSignals
import hidhide

app = Flask(__name__)
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

# ─── HTML/CSS/JS Dashboard Template ─────────────────────────────────
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apex Controller Remapper — Web Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0F172A;
            --bg-card: #1E293B;
            --bg-card-hover: #334155;
            --accent: #38BDF8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --border: #334155;
            --success: #10B981;
            --danger: #EF4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            color: var(--accent);
        }

        .engine-actions {
            display: flex;
            align-items: center;
            gap: 1.25rem;
        }

        .hidhide-toggle {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        .btn {
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.875rem;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary { background: #0284C7; color: white; }
        .btn-primary:hover { background: #0369A1; }
        .btn-success { background: var(--success); color: white; }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-danger:hover { background: #DC2626; }
        .btn-secondary { background: var(--bg-card-hover); color: var(--text-primary); }
        .btn-secondary:hover { background: #475569; }

        .app-layout {
            display: grid;
            grid-template-columns: 280px 1fr;
            flex: 1;
            gap: 1.5rem;
            padding: 1.5rem 2rem;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        .sidebar {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            height: calc(100vh - 120px);
            position: sticky;
            top: 90px;
        }

        .sidebar-title {
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
        }

        .profile-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            overflow-y: auto;
            flex: 1;
        }

        .profile-item {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.15s;
        }

        .profile-item:hover {
            background: var(--bg-card-hover);
            color: var(--text-primary);
        }

        .profile-item.active {
            background: #0284C7;
            color: white;
            font-weight: 600;
        }

        .main-panel {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--accent);
        }

        .remap-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }

        .remap-slot {
            background: #0F172A;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .remap-slot span {
            font-weight: 700;
            font-size: 0.85rem;
            color: var(--text-primary);
        }

        .remap-slot select {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--accent);
            font-weight: 600;
            padding: 0.3rem 0.5rem;
            outline: none;
        }

        .table-responsive {
            width: 100%;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }

        th {
            text-align: left;
            padding: 0.75rem 1rem;
            background: #0F172A;
            color: var(--text-secondary);
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
        }

        .badge {
            background: #0369A1;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .status-footer {
            background: #020617;
            border-top: 1px solid var(--border);
            padding: 0.75rem 2rem;
            font-size: 0.825rem;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }

        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--danger);
            margin-right: 0.4rem;
        }

        .status-dot.active { background: var(--success); }
    </style>
</head>
<body>

<header>
    <div class="brand">
        <span>🎮</span> APEX CONTROLLER REMAPPER
    </div>
    <div class="engine-actions">
        <label class="hidhide-toggle">
            <input type="checkbox" id="chkHidHide" checked>
            <span>Prevent Double Input (HidHide)</span>
        </label>
        <button id="btnToggleEngine" class="btn btn-primary" onclick="toggleEngine()">
            ▶ RUN REMAPPER
        </button>
    </div>
</header>

<div class="app-layout">
    <!-- LEFT: Profile Selector -->
    <div class="sidebar">
        <div class="sidebar-title">GAME PROFILES</div>
        <ul class="profile-list" id="profileList"></ul>
        <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary" style="flex: 1;" onclick="createNewProfile()">+ New</button>
            <button class="btn btn-danger" onclick="deleteCurrentProfile()">Delete</button>
        </div>
        <button class="btn btn-success" onclick="saveCurrentProfile()">💾 Save Changes</button>
    </div>

    <!-- RIGHT: Remapping Matrix & Macros -->
    <div class="main-panel">
        <!-- 16 Button Remap Grid -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">BUTTON REMAP MATRIX (Physical ➔ Virtual Output)</span>
                <span id="activeProfileDesc" style="font-size: 0.85rem; color: var(--text-secondary);"></span>
            </div>
            <div class="remap-grid" id="remapGrid"></div>
        </div>

        <!-- Macro Table -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">MACRO ENGINE (Double-Tap & Multi-Button Combos)</span>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-secondary" onclick="addDoubleTapModal()">+ Double-Tap</button>
                    <button class="btn btn-secondary" onclick="addComboModal()">+ Combo</button>
                </div>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Macro Name</th>
                            <th>Trigger Type</th>
                            <th>Trigger Buttons</th>
                            <th>Target Output</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="macroTableBody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="status-footer">
    <div>
        <span class="status-dot" id="statusDot"></span>
        <span id="engineStatusText">Status: Initializing...</span>
    </div>
    <div>ViGEmBus & HidHide Ready | Port 5000</div>
</div>

<script>
    const BUTTON_OPTIONS = {{ button_options | tojson }};
    const CONTROLLER_BUTTONS = {{ controller_buttons | tojson }};
    let currentProfile = null;
    let profiles = {};
    let isRunning = false;

    async function loadData() {
        const res = await fetch('/api/profiles');
        profiles = await res.json();
        const activeName = currentProfile ? currentProfile.name : Object.keys(profiles)[0];
        currentProfile = profiles[activeName];
        renderProfiles();
        renderMapping();
        renderMacros();
        checkEngineStatus();
    }

    function renderProfiles() {
        const list = document.getElementById('profileList');
        list.innerHTML = '';
        Object.keys(profiles).forEach(name => {
            const li = document.createElement('li');
            li.className = 'profile-item' + (name === currentProfile.name ? ' active' : '');
            li.innerHTML = `<span>🎮 ${name}</span>`;
            li.onclick = () => {
                currentProfile = profiles[name];
                renderProfiles();
                renderMapping();
                renderMacros();
            };
            list.appendChild(li);
        });
        document.getElementById('activeProfileDesc').innerText = currentProfile.description || '';
    }

    function renderMapping() {
        const grid = document.getElementById('remapGrid');
        grid.innerHTML = '';
        CONTROLLER_BUTTONS.forEach(btn => {
            const target = currentProfile.button_mapping[btn] || btn;
            const slot = document.createElement('div');
            slot.className = 'remap-slot';
            slot.innerHTML = `
                <span>[${btn}] ➔</span>
                <select onchange="updateButtonMap('${btn}', this.value)">
                    ${BUTTON_OPTIONS.map(opt => `<option value="${opt}" ${opt === target ? 'selected' : ''}>${opt}</option>`).join('')}
                </select>
            `;
            grid.appendChild(slot);
        });
    }

    function renderMacros() {
        const tbody = document.getElementById('macroTableBody');
        tbody.innerHTML = '';
        (currentProfile.macros || []).forEach((m, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${m.name}</b></td>
                <td><span class="badge">${m.trigger_type.replace('_', ' ').toUpperCase()}</span></td>
                <td>${m.trigger_buttons.join(' + ')}</td>
                <td><b>${m.output_sequence.join(', ')}</b></td>
                <td><button class="btn btn-danger" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;" onclick="deleteMacro(${idx})">Delete</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function updateButtonMap(btn, val) {
        currentProfile.button_mapping[btn] = val;
    }

    async function saveCurrentProfile() {
        await fetch('/api/profiles/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentProfile)
        });
        alert(`Profile '${currentProfile.name}' saved successfully!`);
    }

    async function createNewProfile() {
        const name = prompt("Enter Game Name (e.g. Red Dead Redemption 2):");
        if (name && name.trim()) {
            const newProf = {
                name: name.trim(),
                description: "Custom user profile",
                button_mapping: Object.fromEntries(CONTROLLER_BUTTONS.map(b => [b, b])),
                macros: []
            };
            await fetch('/api/profiles/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newProf)
            });
            await loadData();
        }
    }

    async function deleteCurrentProfile() {
        if (Object.keys(profiles).length <= 1) {
            alert("Cannot delete the only profile.");
            return;
        }
        if (confirm(`Delete profile '${currentProfile.name}'?`)) {
            await fetch(`/api/profiles/delete?name=${encodeURIComponent(currentProfile.name)}`, { method: 'POST' });
            currentProfile = null;
            await loadData();
        }
    }

    function addDoubleTapModal() {
        const btn = prompt("Enter button to double-tap (e.g. B, A, RB):", "B");
        if (!btn) return;
        const out = prompt(`Enter target action when double-tapping [${btn}]:`, "B");
        if (!out) return;
        const name = prompt("Enter macro name:", `Double-Tap ${btn} -> ${out}`) || `Double-Tap ${btn}`;

        currentProfile.macros.push({
            name: name,
            trigger_type: "double_tap",
            trigger_buttons: [btn],
            output_sequence: [out],
            hold_duration_ms: 120,
            interval_ms: 40
        });
        renderMacros();
    }

    function addComboModal() {
        const b1 = prompt("Enter first trigger button (e.g. LB):", "LB");
        if (!b1) return;
        const b2 = prompt(`Enter second trigger button to hold with [${b1}] (e.g. X):`, "X");
        if (!b2) return;
        const out = prompt(`Enter target action fired when holding [${b1} + ${b2}]:`, "RT");
        if (!out) return;
        const name = prompt("Enter macro name:", `Combo ${b1}+${b2} -> ${out}`) || `Combo ${b1}+${b2}`;

        currentProfile.macros.push({
            name: name,
            trigger_type: "combo",
            trigger_buttons: [b1, b2],
            output_sequence: [out],
            hold_duration_ms: 120,
            interval_ms: 40
        });
        renderMacros();
    }

    function deleteMacro(idx) {
        currentProfile.macros.splice(idx, 1);
        renderMacros();
    }

    async function checkEngineStatus() {
        const res = await fetch('/api/engine/status');
        const data = await res.json();
        isRunning = data.running;
        document.getElementById('engineStatusText').innerText = "Status: " + data.status;
        const dot = document.getElementById('statusDot');
        const btn = document.getElementById('btnToggleEngine');
        if (isRunning) {
            dot.className = 'status-dot active';
            btn.className = 'btn btn-danger';
            btn.innerText = '■ STOP REMAPPER';
        } else {
            dot.className = 'status-dot';
            btn.className = 'btn btn-primary';
            btn.innerText = '▶ RUN REMAPPER';
        }
    }

    async function toggleEngine() {
        const useHidHide = document.getElementById('chkHidHide').checked;
        const res = await fetch('/api/engine/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_name: currentProfile.name,
                use_hidhide: useHidHide
            })
        });
        const data = await res.json();
        await checkEngineStatus();
    }

    setInterval(checkEngineStatus, 2000);
    loadData();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML_DASHBOARD,
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
        button_mapping=data.get("button_mapping", {}),
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

@app.route("/api/engine/status")
def get_engine_status():
    global engine_instance, engine_status
    with engine_lock:
        running = engine_instance is not None and engine_instance.running
    return jsonify({
        "running": running,
        "status": engine_status
    })

@app.route("/api/engine/toggle", methods=["POST"])
def toggle_engine():
    global engine_instance, engine_status
    data = request.json or {}
    p_name = data.get("profile_name", "")
    use_hidhide = data.get("use_hidhide", True)

    with engine_lock:
        if engine_instance and engine_instance.running:
            engine_instance.stop()
            engine_instance = None
            if use_hidhide and hidhide.is_hidhide_available():
                hidhide.disable_hidhide_cloaking()
            engine_status = "Stopped"
        else:
            profile = profile_mgr.get_profile(p_name)
            if use_hidhide and hidhide.is_hidhide_available():
                engine_status = "Cloaking physical controller with HidHide..."
                hidhide.setup_hidhide_for_remapper()

            engine_instance = RemapperEngine(signals)
            engine_instance.update_config(EngineConfig(
                button_mapping=profile.button_mapping,
                macros=profile.macros
            ))
            engine_instance.start()
            engine_status = f"Active -- Streaming '{profile.name}' to Virtual Xbox 360"

    return jsonify({"success": True})

def start_web_server(port: int = 5000):
    print(f"[*] Starting Apex Controller Remapper Web UI at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_web_server()
