"""
styles.py – Theme, Styling & Dynamic RGB Lightbar Stylesheet System
===================================================================
Provides the Modular White design system with crisp high-DPI borders,
accessible contrast, smooth hover states, and dynamic RGB neon status strip.
"""

from __future__ import annotations

# ─── Color Palette Constants ─────────────────────────────────────────
class Palette:
    BG_BASE = "#F8FAFC"
    BG_CARD = "#FFFFFF"
    BORDER_DEFAULT = "#E2E8F0"
    BORDER_MUTED = "#CBD5E1"
    BORDER_HOVER = "#0284C7"
    
    PRIMARY = "#0284C7"
    PRIMARY_HOVER = "#0369A1"
    
    SUCCESS = "#16A34A"
    SUCCESS_BG = "#DCFCE7"
    
    DANGER = "#EF4444"
    DANGER_HOVER = "#DC2626"
    
    PURPLE = "#7C3AED"
    PURPLE_BG = "#FAF5FF"
    PURPLE_BORDER = "#C084FC"
    
    TEXT_MAIN = "#0F172A"
    TEXT_MUTED = "#475569"
    TEXT_LIGHT = "#64748B"

# ─── Main Application QSS ───────────────────────────────────────────
MODULAR_WHITE_QSS = f"""
QMainWindow {{
    background-color: {Palette.BG_BASE};
    color: {Palette.TEXT_MAIN};
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}}
QWidget {{
    background-color: {Palette.BG_BASE};
    color: {Palette.TEXT_MAIN};
}}
QGroupBox {{
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_DEFAULT};
    border-radius: 12px;
    margin-top: 18px;
    padding: 16px 14px 12px 14px;
    font-weight: 700;
    font-size: 13px;
    color: {Palette.PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 14px;
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_DEFAULT};
    border-radius: 6px;
    color: {Palette.TEXT_MAIN};
}}
QListWidget {{
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 6px;
    color: #334155;
    font-size: 13px;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 3px;
}}
QListWidget::item:selected {{
    background-color: {Palette.PRIMARY};
    color: #FFFFFF;
    font-weight: 700;
}}
QListWidget::item:hover:!selected {{
    background-color: #F1F5F9;
    color: {Palette.TEXT_MAIN};
}}
QComboBox {{
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_MUTED};
    border-radius: 6px;
    padding: 4px 8px;
    color: {Palette.TEXT_MAIN};
    font-weight: 600;
}}
QComboBox:hover {{
    border: 1px solid {Palette.PRIMARY};
    background-color: {Palette.BG_BASE};
}}
QComboBox QAbstractItemView {{
    background-color: {Palette.BG_CARD};
    selection-background-color: {Palette.PRIMARY};
    selection-color: #FFFFFF;
    color: {Palette.TEXT_MAIN};
    border: 1px solid {Palette.BORDER_DEFAULT};
}}
QPushButton {{
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_MUTED};
    border-radius: 7px;
    padding: 7px 16px;
    color: #334155;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {Palette.BG_BASE};
    border-color: #94A3B8;
    color: {Palette.TEXT_MAIN};
}}
QPushButton#btn_run {{
    background-color: {Palette.PRIMARY};
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 26px;
    border: none;
    border-radius: 7px;
}}
QPushButton#btn_run:hover {{
    background-color: {Palette.PRIMARY_HOVER};
}}
QPushButton#btn_stop {{
    background-color: {Palette.DANGER};
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 26px;
    border: none;
    border-radius: 7px;
}}
QPushButton#btn_stop:hover {{
    background-color: {Palette.DANGER_HOVER};
}}
QTableWidget {{
    background-color: {Palette.BG_CARD};
    border: 1px solid {Palette.BORDER_DEFAULT};
    border-radius: 8px;
    gridline-color: #F1F5F9;
    color: #1E293B;
}}
QHeaderView::section {{
    background-color: #F1F5F9;
    color: {Palette.TEXT_MUTED};
    padding: 8px 6px;
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid {Palette.BORDER_DEFAULT};
}}
QCheckBox {{
    spacing: 8px;
    font-size: 12px;
    font-weight: 500;
    color: {Palette.TEXT_MUTED};
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid {Palette.BORDER_MUTED};
    background-color: {Palette.BG_CARD};
}}
QCheckBox::indicator:checked {{
    background-color: {Palette.PRIMARY};
    border-color: {Palette.PRIMARY};
}}
"""

def get_rgb_lightbar_qss(hue: float, is_active: bool = False) -> str:
    """Computes dynamic flowing RGB neon gradient for the top lightbar."""
    from PyQt6.QtGui import QColor
    
    c1 = QColor.fromHsvF(hue % 1.0, 0.85, 0.98).name()
    c2 = QColor.fromHsvF((hue + 0.33) % 1.0, 0.85, 0.98).name()
    c3 = QColor.fromHsvF((hue + 0.66) % 1.0, 0.85, 0.98).name()
    
    height = 5 if is_active else 3
    glow = "box-shadow: 0 0 10px rgba(2, 132, 199, 0.5);" if is_active else ""
    return f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {c1}, stop:0.5 {c2}, stop:1 {c3});
        border-radius: 2px;
        min-height: {height}px;
        max-height: {height}px;
        {glow}
    """
