"""
ui.py – Modular White Clean Theme with Dynamic RGB Status Strip
================================================================
Features:
  - Clean Minimal Modular White Theme (Apple/Braun inspired aesthetic)
  - Dynamic RGB Neon Glow Lightbar Strip:
      * Idle/Stopped: Gentle breathing cyan/silver wave
      * Active/Remapping: Energetic cycling chromatic RGB wave
      * Error/Warning: Alert amber/coral pulse
  - Real-time profile switching, button remap matrix, and macro engine
"""

from __future__ import annotations

import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QSplitter,
    QFrame
)

from constants import BUTTON_OPTIONS
from profiles import ProfileManager, GameProfile, CONTROLLER_BUTTONS
from engine import RemapperEngine, EngineConfig, MappingSignals
from visualizer_widget import ControllerVisualizerWidget
import hidhide

# ─── MODULAR WHITE THEME STYLING ────────────────────────────────────
MODULAR_WHITE_QSS = """
QMainWindow {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}
QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
}
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    margin-top: 18px;
    padding: 16px 14px 12px 14px;
    font-weight: 700;
    font-size: 13px;
    color: #0284C7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 14px;
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    color: #0F172A;
}
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px;
    color: #334155;
    font-size: 13px;
}
QListWidget::item {
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 3px;
}
QListWidget::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: 700;
}
QListWidget::item:hover:!selected {
    background-color: #F1F5F9;
    color: #0F172A;
}
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 8px;
    color: #0F172A;
    font-weight: 600;
}
QComboBox:hover {
    border: 1px solid #0284C7;
    background-color: #F8FAFC;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 7px 16px;
    color: #334155;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #0F172A;
}
QPushButton#btn_run {
    background-color: #0284C7;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 26px;
    border: none;
    border-radius: 7px;
}
QPushButton#btn_run:hover {
    background-color: #0369A1;
}
QPushButton#btn_stop {
    background-color: #EF4444;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 26px;
    border: none;
    border-radius: 7px;
}
QPushButton#btn_stop:hover {
    background-color: #DC2626;
}
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
    color: #1E293B;
}
QHeaderView::section {
    background-color: #F1F5F9;
    color: #475569;
    padding: 8px 6px;
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
}
QCheckBox {
    spacing: 8px;
    font-size: 12px;
    font-weight: 500;
    color: #475569;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #0284C7;
    border-color: #0284C7;
}
"""

class WitcherRemapperUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.profile_mgr = ProfileManager()
        self.current_profile: GameProfile = self.profile_mgr.get_profile("General Gamepad (Default)")
        self.signals = MappingSignals()
        self.signals.status_updated.connect(self._on_status)
        self.signals.telemetry_updated.connect(self._on_telemetry)
        self._engine: RemapperEngine | None = None
        self._dropdowns: dict[str, QComboBox] = {}
        self._action_labels: dict[str, QLabel] = {}

        # RGB Strip Animation State
        self.rgb_hue = 0.0
        self.rgb_timer = QTimer(self)
        self.rgb_timer.timeout.connect(self._animate_rgb_strip)
        self.rgb_timer.start(35) # ~30 FPS light wave

        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("GeForce NOW Controller Remapper PC")
        self.setMinimumSize(1180, 740)
        self.setStyleSheet(MODULAR_WHITE_QSS)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # ─── Top Bar: App Status & Controls ──────────────────────────
        top_bar = QHBoxLayout()

        app_title = QLabel("🎮 GEFORCE NOW CONTROLLER REMAPPER PC")
        app_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px;")

        self.chk_hidhide = QCheckBox("Prevent Double Input via HidHide")
        self.chk_hidhide.setChecked(True)
        self.chk_hidhide.setToolTip("Hides physical gamepad from GeForce NOW, letting only virtual Xbox 360 register.")

        self.btn_run = QPushButton("▶ RUN REMAPPER")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self._toggle_engine)

        top_bar.addWidget(app_title)
        top_bar.addSpacing(24)
        top_bar.addWidget(self.chk_hidhide)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_run)
        main_layout.addLayout(top_bar)

        # ─── DYNAMIC RGB NEON STATUS STRIP ───────────────────────────
        self.rgb_strip = QFrame()
        self.rgb_strip.setFixedHeight(5)
        self.rgb_strip.setStyleSheet("border-radius: 2px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #94A3B8, stop:1 #CBD5E1);")
        main_layout.addWidget(self.rgb_strip)

        # ─── Main Content Splitter (Left: Games, Right: Mapping & Macros)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ─── LEFT PANEL: Game Profiles & Visualizer ──────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # 1. Controller Visualizer Box
        vis_group = QGroupBox("HARDWARE CONTROLLER VISUALIZER")
        vis_layout = QVBoxLayout(vis_group)
        vis_layout.setContentsMargins(8, 14, 8, 8)
        self.visualizer = ControllerVisualizerWidget()
        vis_layout.addWidget(self.visualizer)
        left_layout.addWidget(vis_group)

        # 2. Game Profiles Box
        games_group = QGroupBox("GAME PROFILES")
        games_layout = QVBoxLayout(games_group)

        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        games_layout.addWidget(self.profile_list)

        # Profile Action Buttons
        p_btns_layout = QHBoxLayout()
        btn_new_prof = QPushButton("+ New")
        btn_new_prof.clicked.connect(self._create_new_profile)
        btn_del_prof = QPushButton("Delete")
        btn_del_prof.clicked.connect(self._delete_profile)
        btn_save_prof = QPushButton("💾 Save Profile")
        btn_save_prof.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: 700;")
        btn_save_prof.clicked.connect(self._save_current_profile)

        p_btns_layout.addWidget(btn_new_prof)
        p_btns_layout.addWidget(btn_del_prof)
        games_layout.addLayout(p_btns_layout)
        games_layout.addWidget(btn_save_prof)

        left_layout.addWidget(games_group)
        splitter.addWidget(left_panel)

        # ─── RIGHT PANEL: Remap Grid + Macro Manager ─────────────────
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # 1. Controller Button Remap Grid
        remap_group = QGroupBox("BUTTON REMAP CONFIGURATION (Physical Key ➔ Target Output)")
        grid_layout = QGridLayout(remap_group)
        grid_layout.setHorizontalSpacing(16)
        grid_layout.setVerticalSpacing(10)

        row, col = 0, 0
        for btn in CONTROLLER_BUTTONS:
            cell = QVBoxLayout()
            cell.setSpacing(3)

            # Top row: Physical label + combo selector
            selector_row = QHBoxLayout()
            lbl = QLabel(f"<b>[{btn}]</b>  ➔")
            lbl.setFixedWidth(65)
            lbl.setStyleSheet("color: #0F172A; font-size: 12px;")

            combo = QComboBox()
            combo.addItems(BUTTON_OPTIONS)
            combo.setCurrentText(btn)
            combo.setFixedWidth(75)
            combo.currentTextChanged.connect(lambda _, b=btn: self._update_single_action_label(b))
            self._dropdowns[btn] = combo

            selector_row.addWidget(lbl)
            selector_row.addWidget(combo)
            selector_row.addStretch()
            cell.addLayout(selector_row)

            # Action description badge
            act_lbl = QLabel("")
            act_lbl.setStyleSheet(
                "background-color: #F1F5F9; color: #0284C7; font-size: 11px; "
                "font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #E2E8F0;"
            )
            act_lbl.setWordWrap(True)
            self._action_labels[btn] = act_lbl
            cell.addWidget(act_lbl)

            grid_layout.addLayout(cell, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        right_layout.addWidget(remap_group)

        # 2. Advanced Macros & Combos
        macro_group = QGroupBox("GAME MACROS & COMBOS (Double-Tap & Multi-Button Actions)")
        macro_layout = QVBoxLayout(macro_group)

        self.macro_table = QTableWidget()
        self.macro_table.setColumnCount(4)
        self.macro_table.setHorizontalHeaderLabels(["Macro Name", "Trigger Type", "Trigger Buttons", "Virtual Output"])
        self.macro_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.macro_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        macro_layout.addWidget(self.macro_table)

        macro_btns = QHBoxLayout()
        btn_add_dtap = QPushButton("+ Add Double-Tap Macro")
        btn_add_dtap.clicked.connect(self._add_double_tap_macro)

        btn_add_combo = QPushButton("+ Add Multi-Button Combo")
        btn_add_combo.clicked.connect(self._add_combo_macro)

        btn_del_macro = QPushButton("Remove Selected Macro")
        btn_del_macro.clicked.connect(self._remove_selected_macro)

        macro_btns.addWidget(btn_add_dtap)
        macro_btns.addWidget(btn_add_combo)
        macro_btns.addWidget(btn_del_macro)
        macro_layout.addLayout(macro_btns)

        right_layout.addWidget(macro_group)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        # ─── Status Footer Bar ───────────────────────────────────────
        self.status_bar = QLabel("Status: Ready. Select a game profile and click 'RUN REMAPPER'.")
        self.status_bar.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; "
            "color: #64748B; padding: 8px 14px; font-size: 12px; font-weight: 500;"
        )
        main_layout.addWidget(self.status_bar)

        self.setCentralWidget(central_widget)
        self._refresh_profile_list()

    # ─── DYNAMIC RGB LIGHTBAR ANIMATION ─────────────────────────────
    def _animate_rgb_strip(self):
        is_running = self._engine is not None and self._engine.running

        if is_running:
            # Active Remapping: Chromatic vibrant neon flow
            self.rgb_hue = (self.rgb_hue + 0.015) % 1.0
            c1 = QColor.fromHsvF(self.rgb_hue, 0.85, 0.95).name()
            c2 = QColor.fromHsvF((self.rgb_hue + 0.33) % 1.0, 0.85, 0.95).name()
            c3 = QColor.fromHsvF((self.rgb_hue + 0.66) % 1.0, 0.85, 0.95).name()
            style = (
                f"border-radius: 2px; "
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {c1}, stop:0.5 {c2}, stop:1 {c3});"
            )
        else:
            # Idle/Stopped: Soft modern ice-blue wave
            self.rgb_hue = (self.rgb_hue + 0.005) % 1.0
            val = 0.6 + 0.3 * (0.5 + 0.5 * (self.rgb_hue * 6.28))
            c1 = "#0284C7"
            c2 = "#38BDF8"
            c3 = "#BAE6FD"
            style = (
                f"border-radius: 2px; "
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {c1}, stop:0.5 {c2}, stop:1 {c3});"
            )

        self.rgb_strip.setStyleSheet(style)

    # ─── Profile Management ─────────────────────────────────────────
    def _refresh_profile_list(self):
        self.profile_list.clear()
        for p_name in self.profile_mgr.profiles.keys():
            item = QListWidgetItem(f"🎮  {p_name}")
            item.setData(Qt.ItemDataRole.UserRole, p_name)
            self.profile_list.addItem(item)
            if p_name == self.current_profile.name:
                self.profile_list.setCurrentItem(item)

    def _on_profile_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        p_name = current.data(Qt.ItemDataRole.UserRole)
        self.current_profile = self.profile_mgr.get_profile(p_name)
        self._load_profile_into_ui(self.current_profile)

    def _update_single_action_label(self, btn: str):
        if btn not in self._dropdowns or btn not in self._action_labels:
            return
        target = self._dropdowns[btn].currentText()
        action_desc = self.current_profile.button_actions.get(target, target)
        self._action_labels[btn].setText(f"Action: {action_desc}")

    def _load_profile_into_ui(self, profile: GameProfile):
        for btn, combo in self._dropdowns.items():
            target = profile.button_mapping.get(btn, btn)
            combo.blockSignals(True)
            combo.setCurrentText(target)
            combo.blockSignals(False)
            action_desc = profile.button_actions.get(target, target)
            if btn in self._action_labels:
                self._action_labels[btn].setText(f"Action: {action_desc}")

        self.macro_table.setRowCount(0)
        for m in profile.macros:
            row = self.macro_table.rowCount()
            self.macro_table.insertRow(row)
            self.macro_table.setItem(row, 0, QTableWidgetItem(m.get("name", "")))
            self.macro_table.setItem(row, 1, QTableWidgetItem(m.get("trigger_type", "").replace("_", " ").title()))
            self.macro_table.setItem(row, 2, QTableWidgetItem(" + ".join(m.get("trigger_buttons", []))))
            self.macro_table.setItem(row, 3, QTableWidgetItem(", ".join(m.get("output_sequence", []))))

        self.status_bar.setText(f"Active Profile: '{profile.name}' | {profile.description}")

        if self._engine and self._engine.running:
            self._engine.update_config(self._get_engine_config())

    def _save_current_profile(self):
        new_map = {btn: combo.currentText() for btn, combo in self._dropdowns.items()}
        self.current_profile.button_mapping = new_map
        self.profile_mgr.save_profile(self.current_profile)
        self.status_bar.setText(f"✓ Configuration for '{self.current_profile.name}' saved permanently.")

        if self._engine and self._engine.running:
            self._engine.update_config(self._get_engine_config())

    def _create_new_profile(self):
        name, ok = QInputDialog.getText(self, "New Game Profile", "Enter game name (e.g., Red Dead Redemption 2):")
        if ok and name.strip():
            name = name.strip()
            new_profile = GameProfile(
                name=name,
                description="Custom user profile",
                button_mapping={b: b for b in CONTROLLER_BUTTONS},
                macros=[]
            )
            self.profile_mgr.save_profile(new_profile)
            self.current_profile = new_profile
            self._refresh_profile_list()

    def _delete_profile(self):
        if len(self.profile_mgr.profiles) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the only remaining profile.")
            return

        res = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete profile '{self.current_profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            name_to_del = self.current_profile.name
            self.profile_mgr.delete_profile(name_to_del)
            self.current_profile = next(iter(self.profile_mgr.profiles.values()))
            self._refresh_profile_list()

    # ─── Macro Add / Remove ─────────────────────────────────────────
    def _add_double_tap_macro(self):
        btn, ok = QInputDialog.getItem(
            self, "Double-Tap Trigger", "Select button to double-tap:",
            BUTTON_OPTIONS, 1, False
        )
        if not ok: return

        out, ok = QInputDialog.getItem(
            self, "Macro Output", f"Action to emit when double-tapping [{btn}]:",
            BUTTON_OPTIONS, 0, False
        )
        if not ok: return

        name, ok = QInputDialog.getText(
            self, "Macro Name", "Enter a name for this macro:",
            text=f"Double-Tap {btn} -> {out}"
        )
        if not ok or not name: name = f"Double-Tap {btn}"

        macro = {
            "name": name,
            "trigger_type": "double_tap",
            "trigger_buttons": [btn],
            "output_sequence": [out],
            "hold_duration_ms": 120,
            "interval_ms": 40
        }
        self.current_profile.macros.append(macro)
        self._load_profile_into_ui(self.current_profile)

    def _add_combo_macro(self):
        b1, ok = QInputDialog.getItem(self, "Combo Key 1", "Select first trigger button (e.g. LB):", BUTTON_OPTIONS, 4, False)
        if not ok: return

        b2, ok = QInputDialog.getItem(self, "Combo Key 2", f"Select second trigger button to hold with [{b1}]:", BUTTON_OPTIONS, 0, False)
        if not ok: return

        out, ok = QInputDialog.getItem(self, "Combo Output", f"Action to fire when holding [{b1} + {b2}]:", BUTTON_OPTIONS, 7, False)
        if not ok: return

        name, ok = QInputDialog.getText(self, "Macro Name", "Macro Name:", text=f"Combo {b1}+{b2} -> {out}")
        if not ok or not name: name = f"Combo {b1}+{b2}"

        macro = {
            "name": name,
            "trigger_type": "combo",
            "trigger_buttons": [b1, b2],
            "output_sequence": [out],
            "hold_duration_ms": 120,
            "interval_ms": 40
        }
        self.current_profile.macros.append(macro)
        self._load_profile_into_ui(self.current_profile)

    def _remove_selected_macro(self):
        row = self.macro_table.currentRow()
        if row >= 0 and row < len(self.current_profile.macros):
            del self.current_profile.macros[row]
            self._load_profile_into_ui(self.current_profile)

    # ─── Engine Execution & HidHide ─────────────────────────────────
    def _get_engine_config(self) -> EngineConfig:
        mapping = {b: combo.currentText() for b, combo in self._dropdowns.items()}
        return EngineConfig(
            button_mapping=mapping,
            macros=self.current_profile.macros
        )

    def _toggle_engine(self):
        if self._engine and self._engine.running:
            # STOP
            self._engine.stop()
            self._engine = None

            if self.chk_hidhide.isChecked() and hidhide.is_hidhide_available():
                hidhide.disable_hidhide_cloaking()

            self.btn_run.setText("▶ RUN REMAPPER")
            self.btn_run.setObjectName("btn_run")
            self.btn_run.setStyleSheet("")
            self.status_bar.setText("Status: Remapper stopped. Physical gamepad restored.")
        else:
            # START
            if self.chk_hidhide.isChecked() and hidhide.is_hidhide_available():
                self.status_bar.setText("Status: Cloaking physical controller with HidHide...")
                hidhide.setup_hidhide_for_remapper()

            self._engine = RemapperEngine(self.signals)
            self._engine.update_config(self._get_engine_config())
            self._engine.start()

            self.btn_run.setText("■ STOP REMAPPER")
            self.btn_run.setObjectName("btn_stop")
            self.btn_run.setStyleSheet("")

    def _on_status(self, msg: str):
        self.status_bar.setText(msg)

    def _on_telemetry(self, data: dict):
        self.visualizer.update_telemetry(data)

    def closeEvent(self, event):
        if self._engine and self._engine.running:
            self._engine.stop()
        if self.chk_hidhide.isChecked() and hidhide.is_hidhide_available():
            hidhide.disable_hidhide_cloaking()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WitcherRemapperUI()
    window.show()
    sys.exit(app.exec())
