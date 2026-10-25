# GeForce NOW Controller Remapper PC

An advanced, high-performance, low-latency Windows controller remapper and macro engine built specifically for cloud gaming (**NVIDIA GeForce NOW**) and native PC gaming. It intercepts raw gamepad inputs (XInput/DirectInput), maps them dynamically through custom per-game profiles with a bijective auto-swap system, executes double-tap and multi-button combination macros, and streams inputs to a virtual Xbox 360 controller via the ViGEmBus driver.

---

## Key Highlights

- **Per-Game Profiles with Persistent Storage**: Select games from the left sidebar (*The Witcher 3*, *Cyberpunk 2077*, *Elden Ring*, or create custom game profiles). All button remaps and macros are saved permanently into `profiles.json` using atomic file writes.
- **Bijective Auto-Swap System**: In-game actions and default keys are fixed. Changing any mapped button automatically swaps with the displaced key, guaranteeing a strict 1:1 bijection with zero duplicates.
- **Advanced Macro Engine & Real-Time Macro Visualizer**:
  - **Double-Tap Macros**: Execute evasive dodges, sprints, or rapid-fire actions by double-tapping any button (e.g., double-tap `B` ➔ Dodge Roll).
  - **Multi-Button Combinations (Combos)**: Press and hold key combinations to trigger instant single-button or sequenced actions (e.g., `LB + X` ➔ Cast Sign `RT`, `Y + RB` ➔ Two-Hand Weapon).
  - **Live Hardware Model Visualizer with Macro Cues**: Real-time vector gamepad visualizer on both Desktop & Web Dashboard highlights physical presses, translated virtual outputs, trigger depth gauges (`LT 85%`, `RT 92%`), and flashes an electric purple macro alert banner + pulsing neon aura rings on the exact buttons triggered by active macros.
- **Continuous Hotplug Test Monitor**: The hardware visualizer remains continuously active and hotplug-resilient immediately upon app launch, even before clicking "RUN REMAPPER".
- **Anti-Double Input Protection (Integrated HidHide)**: Completely hides the physical gamepad from GeForce NOW at the driver level, ensuring only the remapped virtual Xbox 360 controller registers.
- **125 Hz Translation Loop**: Sub-8ms response latency with normalized trigger gradients (`0.0` to `1.0`), automatic resting calibration, and stick deadzone filtering.
- **Dual UI (PyQt6 Desktop + Responsive Web Dashboard)**: Modular White aesthetic with dynamic RGB neon lightbar status indicator.

---

## Modular Architecture

```
controller_remapping/
├── witcher_remapper.py      # Unified CLI/GUI/Web launcher
├── ui.py                    # Native PyQt6 desktop window controller
├── visualizer_widget.py     # Zero-allocation high-DPI ergonomic gamepad visualizer
├── styles.py                # Modular White QSS system & dynamic RGB generator
├── dialogs.py               # Unified modal dialogs for macros and profiles
├── engine.py                # High-frequency 125Hz input & macro streaming engine
├── profiles.py              # Bijective auto-swap logic & atomic profile manager
├── constants.py             # Canonical controller axis and button mappings
├── hidhide.py               # Nefarius HidHide driver integration & cloaking
├── web_server.py            # Lightweight Flask REST API and web controller
├── templates/
│   └── dashboard.html       # Web dashboard HTML template
├── static/
│   ├── css/
│   │   └── dashboard.css    # Responsive Modular White stylesheet
│   └── js/
│       └── dashboard.js     # Client-side telemetry and visualizer controller
└── profiles.json            # Persistent profile storage
```

---

## System Architecture

```mermaid
flowchart LR
    A["Physical Gamepad\n(Xbox / Ares Pro / DualShock)"] -->|Raw USB / Bluetooth Packets| B["Pygame Input Layer"]
    B --> C["Translation & Macro Engine\n(125 Hz Daemon)"]
    D["profiles.json\n(Game Profiles & Combos)"] -.->|Loads Config| C
    E["HidHide Filter Driver"] -.->|Hides Physical Pad| F["GeForce NOW / Game Process"]
    C -->|Emulated XInput Packets| G["ViGEmBus\n(Virtual Xbox 360)"]
    G -->|Pipes Virtual Gamepad| F
```

---

## Getting Started

### 1. Prerequisites
- **Windows 10 / 11 (64-bit)**
- **Python 3.10+** (Tested on Python 3.12)
- **ViGEmBus Driver**: [ViGEmBus Releases](https://github.com/ViGEm/ViGEmBus/releases) *(Installs the system-level virtual controller bus)*
- **HidHide Driver (Optional but Recommended)**: [HidHide Releases](https://github.com/nefarius/HidHide/releases) *(Prevents double input on GeForce NOW)*

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/vivek3071997/controller_remapping_windows11_to_GeforceNOW.git
cd controller_remapping_windows11_to_GeforceNOW
pip install -r requirements.txt
```

### 3. Launching the App
Double-click `Launch Witcher Remapper.bat` on your Desktop, or run:
```bash
# Launch Native Desktop GUI
python witcher_remapper.py

# Launch Web Dashboard (http://localhost:5000)
python witcher_remapper.py --web

# Launch Both Desktop GUI and Web Server Simultaneously
python witcher_remapper.py --all
```

---

## How to Use

1. **Select or Create a Game Profile**:
   - Choose a profile from the left sidebar or click `+ New Profile` to add your own game.
2. **Remap Any Button**:
   - Change any dropdown in the 16-button matrix (`Default [X] ➔ Mapped [Y]`). The auto-swap system updates the displaced button automatically.
3. **Add Powerful Macros**:
   - Click `+ Add Double-Tap Macro` to create actions triggered by rapid double clicks.
   - Click `+ Add Multi-Button Combo` to create complex actions fired by holding two buttons simultaneously.
4. **Save Profile**:
   - Click `💾 Save Profile` to write your configuration to `profiles.json`.
5. **Run Remapper**:
   - Click **▶ RUN REMAPPER**. The dynamic RGB lightbar will glow and inputs will stream to GeForce NOW!

---

## Automated GitHub CI/CD Build
A GitHub Actions workflow (`.github/workflows/build.yml`) automatically builds standalone Windows executable binaries on every release and commit to `main`.
