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
    <title>GeForce NOW Controller Remapper PC — Web Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #F8FAFC;
            --bg-card: #FFFFFF;
            --bg-card-hover: #F1F5F9;
            --accent: #0284C7;
            --accent-glow: rgba(2, 132, 199, 0.2);
            --text-primary: #0F172A;
            --text-secondary: #64748B;
            --border: #E2E8F0;
            --success: #10B981;
            --danger: #EF4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(255, 255, 255, 0.9);
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

        /* ─── DYNAMIC RGB NEON STRIP ─── */
        .rgb-strip {
            height: 5px;
            width: 100%;
            background: linear-gradient(90deg, #0284c7, #38bdf8, #818cf8, #c084fc, #e879f9, #38bdf8);
            background-size: 300% 300%;
            animation: rgbFlow 6s ease infinite;
        }

        .rgb-strip.active {
            background: linear-gradient(90deg, #ff0055, #ff5500, #ffdd00, #00ff66, #00bbff, #b700ff, #ff0055);
            background-size: 400% 400%;
            animation: rgbFlow 2.5s linear infinite;
            box-shadow: 0 0 12px rgba(0, 187, 255, 0.4);
        }

        @keyframes rgbFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* ─── MACRO TRIGGER VISUALIZER PULSE ─── */
        @keyframes pulseAlert {
            0% { transform: scale(1.0); box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35); }
            100% { transform: scale(1.015); box-shadow: 0 6px 20px rgba(124, 58, 237, 0.65); }
        }

        .svg-macro-active {
            filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.85)) !important;
            stroke: #C084FC !important;
            stroke-width: 3.5px !important;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            color: var(--text-primary);
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
            font-weight: 500;
        }

        .btn {
            padding: 0.6rem 1.35rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.875rem;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary { background: #0284C7; color: white; border: none; }
        .btn-primary:hover { background: #0369A1; }
        .btn-success { background: #0284C7; color: white; border: none; }
        .btn-success:hover { background: #0369A1; }
        .btn-danger { background: var(--danger); color: white; border: none; }
        .btn-danger:hover { background: #DC2626; }
        .btn-secondary { background: #FFFFFF; color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--bg-card-hover); border-color: #CBD5E1; }

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
            height: calc(100vh - 140px);
            position: sticky;
            top: 90px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
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
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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
            color: #0F172A;
        }

        .remap-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }

        .remap-slot {
            background: #F8FAFC;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .remap-slot-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .remap-slot span.btn-name {
            font-weight: 700;
            font-size: 0.85rem;
            color: #0F172A;
        }

        .remap-slot select {
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            color: #0284C7;
            font-weight: 700;
            padding: 0.35rem 0.55rem;
            outline: none;
        }

        .action-desc-badge {
            background: #F1F5F9;
            color: #0284C7;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            border: 1px solid #E2E8F0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
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
            background: #F1F5F9;
            color: var(--text-secondary);
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
        }

        .badge {
            background: #E0F2FE;
            color: #0284C7;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }

        .status-footer {
            background: #FFFFFF;
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
        <span>🎮</span> GEFORCE NOW CONTROLLER REMAPPER PC
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
<div class="rgb-strip" id="rgbStrip"></div>

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

    <!-- RIGHT: Visualizer, Remapping Matrix & Macros -->
    <div class="main-panel">
        <!-- Interactive Controller Visualizer -->
        <div class="card" style="padding: 1.25rem 1.5rem;">
            <div class="card-header" style="margin-bottom: 0.75rem;">
                <span class="card-title">HARDWARE CONTROLLER VISUALIZER</span>
                <span id="visControllerName" class="badge" style="background:#E2E8F0; color:#334155;">Controller: Checking...</span>
            </div>

            <!-- Macro Trigger Alert Banner -->
            <div id="visMacroAlertBanner" style="display: none; margin-bottom: 0.85rem; padding: 0.65rem 1rem; border-radius: 8px; background: linear-gradient(135deg, #7C3AED, #2563EB); color: #FFFFFF; font-weight: 700; font-size: 0.875rem; align-items: center; justify-content: space-between; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35); animation: pulseAlert 1.2s infinite alternate;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.15rem;">⚡</span>
                    <span>MACRO TRIGGERED: <span id="visMacroNameText" style="text-decoration: underline; font-weight: 800;">Double Tap Dodge</span></span>
                </div>
                <span id="visMacroOutputBadge" style="background: rgba(255,255,255,0.25); padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.03em;">OUTPUT: [B]</span>
            </div>

            <div style="display: flex; gap: 2rem; align-items: center; justify-content: center; flex-wrap: wrap;">
                <!-- Vector Gamepad SVG -->
                <div style="flex: 1; min-width: 320px; max-width: 440px;">
                    <svg id="gamepadSvg" viewBox="0 0 400 240" style="width: 100%; height: auto; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.06));">
                        <!-- Gamepad Base Body -->
                        <path id="svg_GamepadBody" d="M 90,60 C 120,45 280,45 310,60 C 350,80 390,160 360,210 C 340,240 300,210 270,180 C 230,170 170,170 130,180 C 100,210 60,240 40,210 C 10,160 50,80 90,60 Z" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3" />
                        
                        <!-- Triggers & Bumpers -->
                        <rect id="svg_LT" x="80" y="20" width="55" height="24" rx="6" fill="#F1F5F9" stroke="#94A3B8" stroke-width="2"/>
                        <text x="107" y="36" font-size="10" font-weight="bold" fill="#0F172A" text-anchor="middle">LT</text>
                        
                        <rect id="svg_RT" x="265" y="20" width="55" height="24" rx="6" fill="#F1F5F9" stroke="#94A3B8" stroke-width="2"/>
                        <text x="292" y="36" font-size="10" font-weight="bold" fill="#0F172A" text-anchor="middle">RT</text>

                        <rect id="svg_LB" x="75" y="48" width="65" height="16" rx="5" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1.5"/>
                        <text x="107" y="60" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">LB</text>

                        <rect id="svg_RB" x="260" y="48" width="65" height="16" rx="5" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1.5"/>
                        <text x="292" y="60" font-size="9" font-weight="bold" fill="#334155" text-anchor="middle">RB</text>

                        <!-- D-Pad -->
                        <g id="svg_Dpad">
                            <rect id="svg_Up" x="115" y="115" width="18" height="20" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                            <rect id="svg_Down" x="115" y="151" width="18" height="20" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                            <rect id="svg_Left" x="97" y="133" width="20" height="18" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                            <rect id="svg_Right" x="131" y="133" width="20" height="18" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                            <rect x="115" y="133" width="18" height="18" fill="#E2E8F0" />
                        </g>

                        <!-- ABXY Cluster -->
                        <g id="svg_ABXY">
                            <circle id="svg_Y" cx="285" cy="80" r="12" fill="#FFFFFF" stroke="#EAB308" stroke-width="2" />
                            <text x="285" y="84" font-size="10" font-weight="bold" fill="#CA8A04" text-anchor="middle">Y</text>

                            <circle id="svg_A" cx="285" cy="130" r="12" fill="#FFFFFF" stroke="#22C55E" stroke-width="2" />
                            <text x="285" y="134" font-size="10" font-weight="bold" fill="#16A34A" text-anchor="middle">A</text>

                            <circle id="svg_X" cx="260" cy="105" r="12" fill="#FFFFFF" stroke="#3B82F6" stroke-width="2" />
                            <text x="260" y="109" font-size="10" font-weight="bold" fill="#2563EB" text-anchor="middle">X</text>

                            <circle id="svg_B" cx="310" cy="105" r="12" fill="#FFFFFF" stroke="#EF4444" stroke-width="2" />
                            <text x="310" y="109" font-size="10" font-weight="bold" fill="#DC2626" text-anchor="middle">B</text>
                        </g>

                        <!-- Analog Sticks -->
                        <!-- Left Stick (Upper Left) -->
                        <circle cx="125" cy="95" r="22" fill="#F1F5F9" stroke="#CBD5E1" stroke-width="2" />
                        <circle id="svg_LS_Nub" cx="125" cy="95" r="15" fill="#FFFFFF" stroke="#94A3B8" stroke-width="2" />
                        <text id="svg_LS_Text" x="125" y="99" font-size="8" font-weight="bold" fill="#64748B" text-anchor="middle">LS</text>

                        <!-- Right Stick (Lower Right) -->
                        <circle cx="240" cy="150" r="22" fill="#F1F5F9" stroke="#CBD5E1" stroke-width="2" />
                        <circle id="svg_RS_Nub" cx="240" cy="150" r="15" fill="#FFFFFF" stroke="#94A3B8" stroke-width="2" />
                        <text id="svg_RS_Text" x="240" y="154" font-size="8" font-weight="bold" fill="#64748B" text-anchor="middle">RS</text>

                        <!-- Center Nav (BACK, LOGO, START) -->
                        <rect id="svg_BACK" x="170" y="95" width="14" height="10" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                        <rect id="svg_START" x="216" y="95" width="14" height="10" rx="3" fill="#E2E8F0" stroke="#CBD5E1" />
                        <circle cx="200" cy="80" r="12" fill="#FFFFFF" stroke="#0284C7" stroke-width="2" />
                        <text x="200" y="84" font-size="10" font-weight="bold" fill="#0284C7" text-anchor="middle">⮞</text>
                    </svg>
                </div>

                <!-- Telemetry Readout Box -->
                <div style="flex: 1; min-width: 280px; display: flex; flex-direction: column; gap: 0.6rem;">
                    <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem;">
                        <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Real-Time Action Translation</div>
                        <div id="visLiveAction" style="font-size: 1rem; font-weight: 800; color: #0284C7; margin-top: 4px;">Press any button on controller...</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem;">
                        <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 0.5rem 0.75rem;">
                            <div style="font-size: 0.7rem; font-weight: 700; color: var(--text-secondary);">PHYSICAL BUTTON</div>
                            <div id="visPhysicalKeys" style="font-size: 0.95rem; font-weight: 700; color: #0F172A;">None</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 0.5rem 0.75rem;">
                            <div style="font-size: 0.7rem; font-weight: 700; color: var(--text-secondary);">VIRTUAL OUTPUT</div>
                            <div id="visVirtualKeys" style="font-size: 0.95rem; font-weight: 700; color: #10B981;">None</div>
                        </div>
                    </div>
                    <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 0.5rem 0.75rem; display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;">
                        <span>LT: <b id="visLT">0%</b></span>
                        <span>RT: <b id="visRT">0%</b></span>
                        <span>LS: <b id="visLS">(0.0, 0.0)</b></span>
                        <span>RS: <b id="visRS">(0.0, 0.0)</b></span>
                    </div>
                </div>
            </div>
        </div>

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
        const actions = currentProfile.button_actions || {};
        CONTROLLER_BUTTONS.forEach(btn => {
            const target = currentProfile.button_mapping[btn] || btn;
            const actionText = actions[target] || target;
            const slot = document.createElement('div');
            slot.className = 'remap-slot';
            slot.innerHTML = `
                <div class="remap-slot-header">
                    <span class="btn-name">[${btn}] ➔</span>
                    <select onchange="updateButtonMap('${btn}', this.value)">
                        ${BUTTON_OPTIONS.map(opt => `<option value="${opt}" ${opt === target ? 'selected' : ''}>${opt}</option>`).join('')}
                    </select>
                </div>
                <div class="action-desc-badge" id="actionDesc_${btn}" title="${actionText}">
                    Action: ${actionText}
                </div>
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
        const actions = currentProfile.button_actions || {};
        const actionText = actions[val] || val;
        const badge = document.getElementById(`actionDesc_${btn}`);
        if (badge) {
            badge.innerText = `Action: ${actionText}`;
            badge.title = actionText;
        }
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
        const rgb = document.getElementById('rgbStrip');
        if (isRunning) {
            dot.className = 'status-dot active';
            btn.className = 'btn btn-danger';
            btn.innerText = '■ STOP REMAPPER';
            if (rgb) rgb.className = 'rgb-strip active';
        } else {
            dot.className = 'status-dot';
            btn.className = 'btn btn-primary';
            btn.innerText = '▶ RUN REMAPPER';
            if (rgb) rgb.className = 'rgb-strip';
        }

        // Live Telemetry Visualizer Update
        const t = data.telemetry || {};
        updateVisualizer(t);
    }

    function updateVisualizer(t) {
        if (!t) return;
        const nameBadge = document.getElementById('visControllerName');
        if (t.connected) {
            nameBadge.innerText = "Connected: " + (t.controller_name || "Gamepad");
            nameBadge.style.background = "#DCFCE7";
            nameBadge.style.color = "#15803D";
        } else {
            nameBadge.innerText = "No Controller Connected";
            nameBadge.style.background = "#F1F5F9";
            nameBadge.style.color = "#64748B";
        }

        const phys = t.physical_pressed || [];
        const virt = t.virtual_pressed || [];
        const macroVirt = t.macro_virtual || [];
        const isMacroActive = Boolean(t.macro_active && t.last_macro);

        document.getElementById('visPhysicalKeys').innerText = phys.length ? phys.join(', ') : 'None';
        document.getElementById('visVirtualKeys').innerText = virt.length ? (virt.join(', ') + (isMacroActive ? ' (⚡ MACRO)' : '')) : 'None';

        document.getElementById('visLT').innerText = Math.round((t.lt || 0) * 100) + '%';
        document.getElementById('visRT').innerText = Math.round((t.rt || 0) * 100) + '%';
        document.getElementById('visLS').innerText = `(${t.lx || 0}, ${t.ly || 0})`;
        document.getElementById('visRS').innerText = `(${t.rx || 0}, ${t.ry || 0})`;

        // Macro Alert Banner & Gamepad Shell Aura
        const macroBanner = document.getElementById('visMacroAlertBanner');
        const gamepadBody = document.getElementById('svg_GamepadBody');
        if (isMacroActive) {
            if (macroBanner) {
                macroBanner.style.display = 'flex';
                document.getElementById('visMacroNameText').innerText = t.last_macro;
                document.getElementById('visMacroOutputBadge').innerText = 'OUTPUT: [' + (macroVirt.length ? macroVirt.join(', ') : 'Active') + ']';
            }
            if (gamepadBody) {
                gamepadBody.setAttribute('stroke', '#A855F7');
                gamepadBody.setAttribute('stroke-width', '4');
            }
        } else {
            if (macroBanner) {
                macroBanner.style.display = 'none';
            }
            if (gamepadBody) {
                gamepadBody.setAttribute('stroke', '#CBD5E1');
                gamepadBody.setAttribute('stroke-width', '3');
            }
        }

        // Show live translated action in game or active macro
        if (isMacroActive) {
            const outStr = macroVirt.length ? macroVirt.join(', ') : 'Sequence';
            document.getElementById('visLiveAction').innerHTML = `<span style="color:#7C3AED; font-weight:800;">⚡ MACRO TRIGGERED: ${t.last_macro} ➔ Emitting [${outStr}]</span>`;
        } else if (phys.length > 0) {
            const firstPhys = phys[0];
            const targetVirt = currentProfile.button_mapping[firstPhys] || firstPhys;
            const actionText = (currentProfile.button_actions && currentProfile.button_actions[targetVirt]) || targetVirt;
            document.getElementById('visLiveAction').innerText = `[${firstPhys}] ➔ Emits [${targetVirt}] (${actionText})`;
        } else if (t.last_macro) {
            document.getElementById('visLiveAction').innerText = `⚡ Macro Fired: ${t.last_macro}`;
        } else {
            document.getElementById('visLiveAction').innerText = `Press any button on controller...`;
        }

        // Update Vector SVG Elements
        const ALL_BTNS = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "START", "BACK", "Up", "Down", "Left", "Right"];
        ALL_BTNS.forEach(b => {
            const el = document.getElementById('svg_' + b);
            if (!el) return;
            const isMacroTarget = macroVirt.includes(b);
            const isPressed = phys.includes(b) || isMacroTarget;

            if (isMacroTarget) {
                el.setAttribute('fill', '#A855F7');
                el.classList.add('svg-macro-active');
            } else {
                el.classList.remove('svg-macro-active');
                if (b === 'A') el.setAttribute('fill', isPressed ? '#22C55E' : '#FFFFFF');
                else if (b === 'B') el.setAttribute('fill', isPressed ? '#EF4444' : '#FFFFFF');
                else if (b === 'X') el.setAttribute('fill', isPressed ? '#3B82F6' : '#FFFFFF');
                else if (b === 'Y') el.setAttribute('fill', isPressed ? '#EAB308' : '#FFFFFF');
                else if (b === 'LT' || b === 'RT') el.setAttribute('fill', (isPressed || (b==='LT' && t.lt>0.15) || (b==='RT' && t.rt>0.15)) ? '#38BDF8' : '#F1F5F9');
                else if (b === 'LB' || b === 'RB') el.setAttribute('fill', isPressed ? '#0284C7' : '#E2E8F0');
                else el.setAttribute('fill', isPressed ? '#0284C7' : '#E2E8F0');
            }
        });

        // Update Thumbstick Nubs
        const lsNub = document.getElementById('svg_LS_Nub');
        if (lsNub) {
            const lsX = 125 + (t.lx || 0) * 14;
            const lsY = 95 + (t.ly || 0) * 14;
            lsNub.setAttribute('cx', lsX);
            lsNub.setAttribute('cy', lsY);
            lsNub.setAttribute('fill', phys.includes('LS') ? '#0284C7' : '#FFFFFF');
            const lsText = document.getElementById('svg_LS_Text');
            if (lsText) {
                lsText.setAttribute('x', lsX);
                lsText.setAttribute('y', lsY + 4);
            }
        }

        const rsNub = document.getElementById('svg_RS_Nub');
        if (rsNub) {
            const rsX = 240 + (t.rx || 0) * 14;
            const rsY = 150 + (t.ry || 0) * 14;
            rsNub.setAttribute('cx', rsX);
            rsNub.setAttribute('cy', rsY);
            rsNub.setAttribute('fill', phys.includes('RS') ? '#0284C7' : '#FFFFFF');
            const rsText = document.getElementById('svg_RS_Text');
            if (rsText) {
                rsText.setAttribute('x', rsX);
                rsText.setAttribute('y', rsY + 4);
            }
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

    setInterval(checkEngineStatus, 100);
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
        button_mapping=data.get("button_mapping", {}),
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

@app.route("/api/engine/status")
def get_engine_status():
    global engine_instance, engine_status
    with engine_lock:
        running = engine_instance is not None and engine_instance.running
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
    print(f"[*] Starting GeForce NOW Controller Remapper PC Web UI at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_web_server()
