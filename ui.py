"""
ui.py – PyQt6 GUI for the Witcher Remapper
============================================
Lays out the full window:
  • Path bar + Run/Stop button
  • Utility bar (Reset / Apply / Export / Import)
  • Advanced toggle checkboxes
  • Controller image placeholder + 4-column mapping grid
  • Status bar footer
"""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import BUTTON_OPTIONS, DEFAULT_MAPPING
from engine import EngineConfig, MappingSignals, RemapperEngine
import hidhide

# ──────────────────────────────────────────────────────────────────────
# Colour palette (warm parchment theme)
# ──────────────────────────────────────────────────────────────────────
_BG          = "#F4EFEB"
_FG          = "#2C2523"
_INPUT_BG    = "#EADFD7"
_GROUP_BG    = "#EFEAE6"
_GROUP_BD    = "#DCD6D0"
_BAR_BG      = "#E2DDD9"
_BTN_NEUTRAL = "#C8BFB9"
_BTN_PRIMARY = "#1A3644"
_BTN_DANGER  = "#B22222"


class WitcherRemapperUI(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.signals = MappingSignals()
        self.signals.status_updated.connect(self._on_status)
        self._engine: RemapperEngine | None = None
        self._dropdowns: dict[str, QComboBox] = {}
        self._init_ui()

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────
    def _init_ui(self) -> None:
        self.setWindowTitle("Witcher Remapper — The Witcher 3 Remastered")
        self.setMinimumSize(1060, 580)
        self.setStyleSheet(
            f"background-color: {_BG}; color: {_FG}; font-family: 'Segoe UI';"
        )

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(12, 10, 12, 8)
        root_layout.setSpacing(8)

        # ── Row 1: path bar ──────────────────────────────────────────
        path_row = QHBoxLayout()

        self._path_label = QLabel("Select game path…")
        self._path_label.setStyleSheet(
            f"background-color: {_BAR_BG}; padding: 6px; border-radius: 4px;"
        )

        btn_browse = QPushButton("Browse")
        btn_browse.setStyleSheet(
            f"background-color: {_BTN_NEUTRAL}; padding: 6px 15px;"
        )
        btn_browse.clicked.connect(self._browse_path)

        self._btn_run = QPushButton("▶ Run")
        self._btn_run.setStyleSheet(
            f"background-color: {_BTN_PRIMARY}; color: white; "
            "font-weight: bold; padding: 6px 20px;"
        )
        self._btn_run.clicked.connect(self._toggle_engine)

        path_row.addWidget(self._path_label, 8)
        path_row.addWidget(btn_browse, 1)
        path_row.addWidget(self._btn_run, 1)
        root_layout.addLayout(path_row)

        # ── Row 2: utility bar ───────────────────────────────────────
        util_row = QHBoxLayout()

        btn_reset = QPushButton("Reset Layout")
        btn_reset.setStyleSheet(f"background-color: {_BTN_NEUTRAL}; padding: 5px 12px;")
        btn_reset.clicked.connect(self._reset_layout)

        btn_apply = QPushButton("Apply")
        btn_apply.setStyleSheet(
            f"background-color: {_BTN_PRIMARY}; color: white; "
            "font-weight: bold; padding: 5px 14px;"
        )
        btn_apply.clicked.connect(self._apply_config)

        btn_export = QPushButton("Export")
        btn_export.setStyleSheet(f"background-color: {_BTN_NEUTRAL}; padding: 5px 12px;")
        btn_export.clicked.connect(self._export_config)

        btn_import = QPushButton("Import")
        btn_import.setStyleSheet(f"background-color: {_BTN_NEUTRAL}; padding: 5px 12px;")
        btn_import.clicked.connect(self._import_config)

        util_row.addWidget(btn_reset)
        util_row.addWidget(btn_apply)
        util_row.addStretch()
        util_row.addWidget(btn_export)
        util_row.addWidget(btn_import)
        root_layout.addLayout(util_row)

        # ── Row 3: advanced toggles ──────────────────────────────────
        adv_box = QWidget()
        adv_box.setStyleSheet(
            f"background-color: {_GROUP_BG}; border: 1px solid {_GROUP_BD}; "
            "border-radius: 6px;"
        )
        adv_lay = QHBoxLayout()
        adv_lay.setContentsMargins(12, 6, 12, 6)

        self._chk_throw = QCheckBox("Use Left Stick for Throw Aiming")
        self._chk_swap  = QCheckBox("Swap Dodge with Roll")
        self._chk_horse = QCheckBox("Horse Acceleration on Left Stick")
        self._chk_hidhide = QCheckBox("Hide Physical Controller (HidHide)")
        self._chk_hidhide.setChecked(True)
        self._chk_hidhide.setToolTip("Hides physical controller from GeForce NOW to prevent double input")

        for chk in (self._chk_throw, self._chk_swap, self._chk_horse, self._chk_hidhide):
            chk.setStyleSheet("font-size: 12px;")
            adv_lay.addWidget(chk)

        adv_box.setLayout(adv_lay)
        root_layout.addWidget(adv_box)

        # ── Row 4: content split (image + grid) ─────────────────────
        content_row = QHBoxLayout()

        # Left: controller image placeholder
        self._controller_img = QLabel()
        self._controller_img.setFixedWidth(280)
        self._controller_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._controller_img.setStyleSheet(
            f"background-color: {_GROUP_BG}; border: 1px solid {_GROUP_BD}; "
            "border-radius: 6px;"
        )
        img_path = Path(__file__).parent / "assets" / "controller.png"
        if img_path.exists():
            pm = QPixmap(str(img_path))
            self._controller_img.setPixmap(
                pm.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio)
            )
        else:
            self._controller_img.setText("🎮\n(controller.png)")
        content_row.addWidget(self._controller_img)

        # Right: 4-column mapping grid
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)

        row, col = 0, 0
        for action, default_val in DEFAULT_MAPPING.items():
            cell = QVBoxLayout()

            lbl = QLabel(action)
            lbl.setStyleSheet("font-size: 11px; color: #5E524E;")
            lbl.setWordWrap(True)

            combo = QComboBox()
            combo.addItems(BUTTON_OPTIONS)
            combo.setCurrentText(default_val)
            combo.setStyleSheet(
                f"background-color: {_INPUT_BG}; padding: 4px; border-radius: 3px;"
            )

            cell.addWidget(lbl)
            cell.addWidget(combo)
            grid_layout.addLayout(cell, row, col)

            self._dropdowns[action] = combo

            col += 1
            if col > 3:
                col = 0
                row += 1

        grid_widget.setLayout(grid_layout)
        content_row.addWidget(grid_widget, 7)
        root_layout.addLayout(content_row)

        # ── Row 5: status bar ────────────────────────────────────────
        self._status = QLabel("Status: Ready to Initialize")
        self._status.setStyleSheet(
            f"background-color: {_BTN_PRIMARY}; color: white; "
            "padding: 6px; font-size: 12px; border-radius: 3px;"
        )
        root_layout.addWidget(self._status)

        root.setLayout(root_layout)
        self.setCentralWidget(root)

    # ──────────────────────────────────────────────────────────────────
    # Slot: status updates from the engine thread
    # ──────────────────────────────────────────────────────────────────
    def _on_status(self, msg: str) -> None:
        self._status.setText(msg)

    # ──────────────────────────────────────────────────────────────────
    # Build an EngineConfig from current UI state
    # ──────────────────────────────────────────────────────────────────
    def _current_config(self) -> EngineConfig:
        return EngineConfig(
            mapping={act: cb.currentText() for act, cb in self._dropdowns.items()},
            toggle_throw_aim=self._chk_throw.isChecked(),
            toggle_swap_dodge=self._chk_swap.isChecked(),
            toggle_horse_accel=self._chk_horse.isChecked(),
        )

    # ──────────────────────────────────────────────────────────────────
    # Button handlers
    # ──────────────────────────────────────────────────────────────────
    def _browse_path(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Game Executable", "", "Executables (*.exe)"
        )
        if path:
            self._path_label.setText(path)

    def _reset_layout(self) -> None:
        for action, default_val in DEFAULT_MAPPING.items():
            self._dropdowns[action].setCurrentText(default_val)
        self._chk_throw.setChecked(False)
        self._chk_swap.setChecked(False)
        self._chk_horse.setChecked(False)
        self._apply_config()
        self._status.setText("Status: Layout reset to defaults.")

    def _apply_config(self) -> None:
        cfg = self._current_config()
        if self._engine and self._engine.is_alive():
            self._engine.update_config(cfg)
            self._status.setText(
                "Status: Configuration applied to running engine."
            )
        else:
            self._status.setText(
                "Status: Configuration saved (engine not running)."
            )

    def _toggle_engine(self) -> None:
        if self._engine and self._engine.running:
            # ── Stop ──
            self._engine.stop()
            self._engine = None
            if self._chk_hidhide.isChecked() and hidhide.is_hidhide_available():
                hidhide.disable_hidhide_cloaking()
            self._btn_run.setText("▶ Run")
            self._btn_run.setStyleSheet(
                f"background-color: {_BTN_PRIMARY}; color: white; "
                "font-weight: bold; padding: 6px 20px;"
            )
            self._status.setText("Status: Interception stopped.")
        else:
            # ── Start ──
            if self._chk_hidhide.isChecked() and hidhide.is_hidhide_available():
                self._status.setText("Status: Configuring HidHide device cloaking...")
                hidhide.setup_hidhide_for_remapper()

            self._engine = RemapperEngine(self.signals)
            self._engine.update_config(self._current_config())
            self._engine.start()
            self._btn_run.setText("■ Stop")
            self._btn_run.setStyleSheet(
                f"background-color: {_BTN_DANGER}; color: white; "
                "font-weight: bold; padding: 6px 20px;"
            )

    def _export_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "", "JSON Files (*.json)"
        )
        if not path:
            return
        cfg = self._current_config()
        payload = {
            "mappings": cfg.mapping,
            "throw_aim": cfg.toggle_throw_aim,
            "swap_dodge": cfg.toggle_swap_dodge,
            "horse_accel": cfg.toggle_horse_accel,
        }
        Path(path).write_text(json.dumps(payload, indent=4), encoding="utf-8")
        self._status.setText(f"Status: Profile exported → {path}")

    def _import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            self._status.setText(f"Import error: {exc}")
            return

        for action, val in payload.get("mappings", {}).items():
            if action in self._dropdowns:
                self._dropdowns[action].setCurrentText(val)

        self._chk_throw.setChecked(payload.get("throw_aim", False))
        self._chk_swap.setChecked(payload.get("swap_dodge", False))
        self._chk_horse.setChecked(payload.get("horse_accel", False))
        self._apply_config()
        self._status.setText(f"Status: Profile imported ← {path}")

    # ──────────────────────────────────────────────────────────────────
    # Clean shutdown
    # ──────────────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # noqa: N802
        if self._engine and self._engine.running:
            self._engine.stop()
        if self._chk_hidhide.isChecked() and hidhide.is_hidhide_available():
            hidhide.disable_hidhide_cloaking()
        event.accept()
