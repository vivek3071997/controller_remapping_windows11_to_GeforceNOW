"""
dialogs.py – Modal Dialogs for Profile & Macro Configuration
============================================================
Provides modern, styled modal dialogs for adding double-tap macros,
multi-button combos, and creating custom game profiles.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt
from constants import BUTTON_OPTIONS

class DoubleTapDialog(QDialog):
    """Modal dialog for defining a double-tap macro."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Double-Tap Macro")
        self.setFixedWidth(360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        
        self.combo_trigger = QComboBox()
        self.combo_trigger.addItems(BUTTON_OPTIONS)
        self.combo_trigger.setCurrentText("B")

        self.combo_output = QComboBox()
        self.combo_output.addItems(BUTTON_OPTIONS)
        self.combo_output.setCurrentText("B")

        self.edit_name = QLineEdit("Double-Tap Dodge")
        
        self.spin_hold = QSpinBox()
        self.spin_hold.setRange(20, 1000)
        self.spin_hold.setValue(120)
        self.spin_hold.setSuffix(" ms")

        form.addRow("Trigger Button:", self.combo_trigger)
        form.addRow("Macro Output:", self.combo_output)
        form.addRow("Macro Name:", self.edit_name)
        form.addRow("Hold Duration:", self.spin_hold)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Add Macro")
        btn_ok.setObjectName("btn_run")
        btn_ok.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def get_macro_data(self) -> Dict[str, Any]:
        return {
            "name": self.edit_name.text().strip() or f"Double-Tap {self.combo_trigger.currentText()}",
            "trigger_type": "double_tap",
            "trigger_buttons": [self.combo_trigger.currentText()],
            "output_sequence": [self.combo_output.currentText()],
            "hold_duration_ms": self.spin_hold.value(),
            "interval_ms": 40
        }

class ComboDialog(QDialog):
    """Modal dialog for defining a multi-button combo macro."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multi-Button Combo")
        self.setFixedWidth(380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()

        self.combo_b1 = QComboBox()
        self.combo_b1.addItems(BUTTON_OPTIONS)
        self.combo_b1.setCurrentText("LB")

        self.combo_b2 = QComboBox()
        self.combo_b2.addItems(BUTTON_OPTIONS)
        self.combo_b2.setCurrentText("X")

        self.combo_out = QComboBox()
        self.combo_out.addItems(BUTTON_OPTIONS)
        self.combo_out.setCurrentText("RT")

        self.edit_name = QLineEdit("Quick Sign Combo")

        self.spin_hold = QSpinBox()
        self.spin_hold.setRange(20, 1000)
        self.spin_hold.setValue(150)
        self.spin_hold.setSuffix(" ms")

        form.addRow("Button 1 (Hold):", self.combo_b1)
        form.addRow("Button 2 (Tap):", self.combo_b2)
        form.addRow("Output Action:", self.combo_out)
        form.addRow("Macro Name:", self.edit_name)
        form.addRow("Hold Duration:", self.spin_hold)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Add Combo")
        btn_ok.setObjectName("btn_run")
        btn_ok.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def get_macro_data(self) -> Dict[str, Any]:
        b1 = self.combo_b1.currentText()
        b2 = self.combo_b2.currentText()
        out = self.combo_out.currentText()
        return {
            "name": self.edit_name.text().strip() or f"Combo {b1}+{b2} -> {out}",
            "trigger_type": "combo",
            "trigger_buttons": [b1, b2],
            "output_sequence": [out],
            "hold_duration_ms": self.spin_hold.value(),
            "interval_ms": 40
        }
