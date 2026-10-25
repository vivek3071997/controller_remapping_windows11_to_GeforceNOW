"""
ui.py – Modern Production GUI with Game Profile Selection & Macro Builder
==========================================================================
Features:
  - Game Profile sidebar (Left): Quick selection of game profiles
  - Profile Management: New, Save, and Delete Game Profiles
  - Visual 16-Button Remap Matrix (Center): Physical -> Target Gamepad Mapping
  - Macro Engine Builder (Right/Bottom):
      * Double-Tap Macros (e.g. Double-tap B -> Custom Action)
      * Button Combination Combos (e.g. LB + X -> RT)
  - HidHide Integration toggle to prevent double input on GeForce NOW
  - Modern Dark Gamer Theme with status telemetry
"""

from __future__ import annotations

import sys
from pathlib import Path
from PyQt6.QtCore import Qt
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
import hidhide

# Modern Theme Styling
THEME_QSS = """
QMainWindow {
    background-color: #12151B;
    color: #E2E8F0;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
QWidget {
    background-color: #12151B;
    color: #E2E8F0;
}
QGroupBox {
    border: 1px solid #2D3748;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: bold;
    color: #63B3ED;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}
QListWidget {
    background-color: #1A202C;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 4px;
    color: #EDF2F7;
    font-size: 13px;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    margin-bottom: 2px;
}
QListWidget::item:selected {
    background-color: #3182CE;
    color: #FFFFFF;
    font-weight: bold;
}
QListWidget::item:hover:!selected {
    background-color: #2D3748;
}
QComboBox {
    background-color: #2D3748;
    border: 1px solid #4A5568;
    border-radius: 4px;
    padding: 4px 8px;
    color: #FFFFFF;
    font-weight: 500;
}
QComboBox:hover {
    border: 1px solid #63B3ED;
}
QComboBox QAbstractItemView {
    background-color: #2D3748;
    selection-background-color: #3182CE;
    color: #FFFFFF;
}
QPushButton {
    background-color: #2D3748;
    border: 1px solid #4A5568;
    border-radius: 5px;
    padding: 6px 14px;
    color: #E2E8F0;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3B4758;
    border-color: #63B3ED;
}
QPushButton#btn_run {
    background-color: #2B6CB0;
    color: #FFFFFF;
    font-size: 13px;
    padding: 8px 24px;
    border: none;
}
QPushButton#btn_run:hover {
    background-color: #3182CE;
}
QPushButton#btn_stop {
    background-color: #C53030;
    color: #FFFFFF;
    font-size: 13px;
    padding: 8px 24px;
    border: none;
}
QPushButton#btn_stop:hover {
    background-color: #E53E3E;
}
QTableWidget {
    background-color: #1A202C;
    border: 1px solid #2D3748;
    border-radius: 6px;
    gridline-color: #2D3748;
    color: #E2E8F0;
}
QHeaderView::section {
    background-color: #2D3748;
    color: #A0AEC0;
    padding: 4px;
    font-weight: bold;
    border: none;
}
QCheckBox {
    spacing: 8px;
    font-size: 12px;
    color: #CBD5E0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #4A5568;
    background-color: #2D3748;
}
QCheckBox::indicator:checked {
    background-color: #3182CE;
    border-color: #63B3ED;
}
"""

class WitcherRemapperUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.profile_mgr = ProfileManager()
        self.current_profile: GameProfile = self.profile_mgr.get_profile("General Gamepad (Default)")
        self.signals = MappingSignals()
        self.signals.status_updated.connect(self._on_status)
        self._engine: RemapperEngine | None = None
        self._dropdowns: dict[str, QComboBox] = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("GeForce NOW Controller Remapper PC")
        self.setMinimumSize(1150, 720)
        self.setStyleSheet(THEME_QSS)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 12)
        main_layout.setSpacing(10)

        # ─── Top Bar: App Status & Controls ──────────────────────────
        top_bar = QHBoxLayout()

        app_title = QLabel("🎮 GEFORCE NOW CONTROLLER REMAPPER PC")
        app_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #63B3ED; letter-spacing: 1px;")

        self.chk_hidhide = QCheckBox("Prevent Double Input via HidHide")
        self.chk_hidhide.setChecked(True)
        self.chk_hidhide.setToolTip("Hides physical gamepad from GeForce NOW & games, letting only virtual Xbox 360 register.")

        self.btn_run = QPushButton("▶ RUN REMAPPER")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self._toggle_engine)

        top_bar.addWidget(app_title)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.chk_hidhide)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_run)
        main_layout.addLayout(top_bar)

        # ─── Main Content Splitter (Left: Games, Right: Mapping & Macros)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ─── LEFT PANEL: Game Profiles ───────────────────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)

        games_group = QGroupBox("SELECT GAME PROFILE")
        games_layout = QVBoxLayout(games_group)

        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        games_layout.addWidget(self.profile_list)

        # Profile Action Buttons
        p_btns_layout = QHBoxLayout()
        btn_new_prof = QPushButton("+ New Profile")
        btn_new_prof.clicked.connect(self._create_new_profile)
        btn_del_prof = QPushButton("Delete")
        btn_del_prof.clicked.connect(self._delete_profile)
        btn_save_prof = QPushButton("💾 Save Profile")
        btn_save_prof.setStyleSheet("background-color: #2C5282; color: #FFFFFF;")
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

        # Build 16 button remapper slots in a 4x4 grid
        row, col = 0, 0
        for btn in CONTROLLER_BUTTONS:
            cell = QHBoxLayout()
            lbl = QLabel(f"<b>[{btn}]</b>  ➔")
            lbl.setFixedWidth(70)
            lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")

            combo = QComboBox()
            combo.addItems(BUTTON_OPTIONS)
            combo.setCurrentText(btn)
            combo.setFixedWidth(85)
            self._dropdowns[btn] = combo

            cell.addWidget(lbl)
            cell.addWidget(combo)
            grid_layout.addLayout(cell, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        right_layout.addWidget(remap_group)

        # 2. Advanced Macros & Combos
        macro_group = QGroupBox("GAME MACROS & COMBOS (Double-Tap & Combination Buttons)")
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
            "background-color: #1A202C; border: 1px solid #2D3748; border-radius: 4px; "
            "color: #A0AEC0; padding: 6px 12px; font-size: 12px;"
        )
        main_layout.addWidget(self.status_bar)

        self.setCentralWidget(central_widget)

        # Populate profile list
        self._refresh_profile_list()

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

    def _load_profile_into_ui(self, profile: GameProfile):
        # Update dropdowns
        for btn, combo in self._dropdowns.items():
            target = profile.button_mapping.get(btn, btn)
            combo.setCurrentText(target)

        # Update macro table
        self.macro_table.setRowCount(0)
        for m in profile.macros:
            row = self.macro_table.rowCount()
            self.macro_table.insertRow(row)
            self.macro_table.setItem(row, 0, QTableWidgetItem(m.get("name", "")))
            self.macro_table.setItem(row, 1, QTableWidgetItem(m.get("trigger_type", "").replace("_", " ").title()))
            self.macro_table.setItem(row, 2, QTableWidgetItem(" + ".join(m.get("trigger_buttons", []))))
            self.macro_table.setItem(row, 3, QTableWidgetItem(", ".join(m.get("output_sequence", []))))

        self.status_bar.setText(f"Active Profile: '{profile.name}' | {profile.description}")

        # If engine is actively running, hot-update it with this game profile
        if self._engine and self._engine.running:
            self._engine.update_config(self._get_engine_config())

    def _save_current_profile(self):
        # Update mapping
        new_map = {btn: combo.currentText() for btn, combo in self._dropdowns.items()}
        self.current_profile.button_mapping = new_map

        # Save to disk
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
