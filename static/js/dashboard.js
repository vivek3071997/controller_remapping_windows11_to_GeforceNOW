// GeForce NOW Controller Remapper PC - Dashboard Client Logic
const BUTTON_OPTIONS = (window.APP_CONFIG && window.APP_CONFIG.buttonOptions) || ['A', 'B', 'X', 'Y', 'LB', 'RB', 'LT', 'RT', 'LS', 'RS', 'START', 'BACK', 'Up', 'Down', 'Left', 'Right'];
    const CONTROLLER_BUTTONS = (window.APP_CONFIG && window.APP_CONFIG.controllerButtons) || ['A', 'B', 'X', 'Y', 'LB', 'RB', 'LT', 'RT', 'LS', 'RS', 'START', 'BACK', 'Up', 'Down', 'Left', 'Right'];
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

    function sanitizeMapping(mapping) {
        mapping = mapping || {};
        const used = new Set();
        const clean = {};
        CONTROLLER_BUTTONS.forEach(b => {
            const target = mapping[b] || b;
            if (CONTROLLER_BUTTONS.includes(target) && !used.has(target)) {
                clean[b] = target;
                used.add(target);
            } else {
                clean[b] = null;
            }
        });
        const unused = CONTROLLER_BUTTONS.filter(b => !used.has(b));
        CONTROLLER_BUTTONS.forEach(b => {
            if (clean[b] === null) {
                clean[b] = unused.shift() || b;
            }
        });
        return clean;
    }

    function getMappedPhysicalKey(mapping, defaultKey) {
        for (const [p, v] of Object.entries(mapping)) {
            if (v === defaultKey) return p;
        }
        return defaultKey;
    }

    function swapButtonMapping(mapping, targetDefaultKey, newPhysKey) {
        mapping = sanitizeMapping(mapping);
        const oldPhysKey = getMappedPhysicalKey(mapping, targetDefaultKey);
        if (oldPhysKey === newPhysKey) return mapping;

        const otherDefaultKey = mapping[newPhysKey] || newPhysKey;
        mapping[newPhysKey] = targetDefaultKey;
        mapping[oldPhysKey] = otherDefaultKey;
        return mapping;
    }

    function renderMapping() {
        const grid = document.getElementById('remapGrid');
        grid.innerHTML = '';
        currentProfile.button_mapping = sanitizeMapping(currentProfile.button_mapping || {});
        const actions = currentProfile.button_actions || {};

        CONTROLLER_BUTTONS.forEach(defBtn => {
            // In-Game Action is FIXED to defBtn
            const actionText = actions[defBtn] || defBtn;
            // Which physical button triggers defBtn?
            const mappedPhys = getMappedPhysicalKey(currentProfile.button_mapping, defBtn);
            const isSwapped = mappedPhys !== defBtn;

            const slot = document.createElement('div');
            slot.className = 'remap-slot' + (isSwapped ? ' swapped' : '');
            slot.id = 'remapSlot_' + defBtn;
            slot.innerHTML = `
                <div class="remap-action-title" title="${actionText}">${actionText}</div>
                <div class="remap-slot-body">
                    <span class="badge-default">Default: <b>[${defBtn}]</b></span>
                    <span class="remap-arrow">➔</span>
                    <span style="font-size:0.75rem; font-weight:700; color:var(--text-secondary);">MAPPED:</span>
                    <select class="remap-select" onchange="handleButtonSwap('${defBtn}', this.value)">
                        ${CONTROLLER_BUTTONS.map(opt => `<option value="${opt}" ${opt === mappedPhys ? 'selected' : ''}>[${opt}]</option>`).join('')}
                    </select>
                    <span class="badge-status ${isSwapped ? 'active' : ''}">${isSwapped ? `⇄ Swapped [${mappedPhys}]` : 'Default'}</span>
                </div>
            `;
            grid.appendChild(slot);
        });
    }

    function handleButtonSwap(targetDefaultKey, newPhysKey) {
        currentProfile.button_mapping = swapButtonMapping(currentProfile.button_mapping, targetDefaultKey, newPhysKey);
        renderMapping();
        saveCurrentProfile();
    }

    function resetMappingsToDefault() {
        const fresh = {};
        CONTROLLER_BUTTONS.forEach(b => fresh[b] = b);
        currentProfile.button_mapping = fresh;
        renderMapping();
        saveCurrentProfile();
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
            const isPressed = phys.includes(b) || virt.includes(b) || isMacroTarget;

            if (isMacroTarget) {
                el.setAttribute('fill', '#A855F7');
                el.setAttribute('stroke', '#C084FC');
                el.classList.add('svg-macro-active');
            } else {
                el.classList.remove('svg-macro-active');
                if (b === 'A') el.setAttribute('fill', isPressed ? '#22C55E' : '#FFFFFF');
                else if (b === 'B') el.setAttribute('fill', isPressed ? '#EF4444' : '#FFFFFF');
                else if (b === 'X') el.setAttribute('fill', isPressed ? '#3B82F6' : '#FFFFFF');
                else if (b === 'Y') el.setAttribute('fill', isPressed ? '#EAB308' : '#FFFFFF');
                else if (b === 'LT') {
                    const ltOn = isPressed || phys.includes('LT') || virt.includes('LT') || (t.lt > 0.15);
                    el.setAttribute('fill', ltOn ? '#0284C7' : '#F0F9FF');
                    el.setAttribute('stroke', ltOn ? '#0369A1' : '#0284C7');
                    const txt = document.getElementById('svg_LT_Text');
                    if (txt) {
                        txt.setAttribute('fill', ltOn ? '#FFFFFF' : '#0284C7');
                        txt.textContent = (t.lt > 0.05) ? ('LT ' + Math.round(t.lt * 100) + '%') : 'LT';
                    }
                } else if (b === 'RT') {
                    const rtOn = isPressed || phys.includes('RT') || virt.includes('RT') || (t.rt > 0.15);
                    el.setAttribute('fill', rtOn ? '#0284C7' : '#F0F9FF');
                    el.setAttribute('stroke', rtOn ? '#0369A1' : '#0284C7');
                    const txt = document.getElementById('svg_RT_Text');
                    if (txt) {
                        txt.setAttribute('fill', rtOn ? '#FFFFFF' : '#0284C7');
                        txt.textContent = (t.rt > 0.05) ? ('RT ' + Math.round(t.rt * 100) + '%') : 'RT';
                    }
                } else if (b === 'LB') {
                    const lbOn = isPressed || phys.includes('LB') || virt.includes('LB');
                    el.setAttribute('fill', lbOn ? '#0284C7' : '#FFFFFF');
                    el.setAttribute('stroke', lbOn ? '#0369A1' : '#0284C7');
                    const txt = document.getElementById('svg_LB_Text');
                    if (txt) txt.setAttribute('fill', lbOn ? '#FFFFFF' : '#0284C7');
                } else if (b === 'RB') {
                    const rbOn = isPressed || phys.includes('RB') || virt.includes('RB');
                    el.setAttribute('fill', rbOn ? '#0284C7' : '#FFFFFF');
                    el.setAttribute('stroke', rbOn ? '#0369A1' : '#0284C7');
                    const txt = document.getElementById('svg_RB_Text');
                    if (txt) txt.setAttribute('fill', rbOn ? '#FFFFFF' : '#0284C7');
                } else {
                    el.setAttribute('fill', isPressed ? '#0284C7' : '#E2E8F0');
                }
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
