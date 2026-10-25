"""
visualizer_widget.py – Interactive Controller Hardware Model Visualizer (PyQt6)
================================================================================
Renders a modern, precision-scaled vector gamepad model representing physical
controllers (Cosmic Byte Ares Pro / Xbox style). Dynamically lights up physical
button presses, highlights remapped target outputs, and animates analog sticks
and triggers in real time.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QRadialGradient, QLinearGradient
from PyQt6.QtWidgets import QWidget

class ControllerVisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self.connected = False
        self.controller_name = "Cosmic Byte Ares Pro"
        self.physical_pressed = set()
        self.virtual_pressed = set()
        self.lt_val = 0.0
        self.rt_val = 0.0
        self.lx_val = 0.0
        self.ly_val = 0.0
        self.rx_val = 0.0
        self.ry_val = 0.0
        self.active_macro = ""
        self.macro_active = False
        self.macro_virtual = set()
        self.last_action_desc = ""

    def update_telemetry(self, data: dict):
        self.connected = data.get("connected", True)
        self.controller_name = data.get("controller_name", "Connected Controller")
        self.physical_pressed = set(data.get("physical_pressed", []))
        self.virtual_pressed = set(data.get("virtual_pressed", []))
        self.lt_val = data.get("lt", 0.0)
        self.rt_val = data.get("rt", 0.0)
        self.lx_val = data.get("lx", 0.0)
        self.ly_val = data.get("ly", 0.0)
        self.rx_val = data.get("rx", 0.0)
        self.ry_val = data.get("ry", 0.0)
        self.active_macro = data.get("last_macro", "")
        self.macro_active = bool(data.get("macro_active", False) or self.active_macro)
        self.macro_virtual = set(data.get("macro_virtual", []))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Scale and center controller model in widget
        scale = min(w / 440.0, h / 270.0)
        painter.save()
        painter.translate((w - 400 * scale) / 2.0, (h - 250 * scale) / 2.0)
        painter.scale(scale, scale)

        # ── 0. Macro Trigger Alert Banner (Top Header) ─────────────
        if self.macro_active and self.active_macro:
            macro_banner_rect = QRectF(30, -6, 340, 20)
            banner_grad = QLinearGradient(30, -6, 370, 14)
            banner_grad.setColorAt(0.0, QColor("#7C3AED"))   # Vibrant Neon Purple
            banner_grad.setColorAt(1.0, QColor("#2563EB"))   # Electric Blue
            painter.setPen(QPen(QColor("#C084FC"), 1.8))
            painter.setBrush(QBrush(banner_grad))
            painter.drawRoundedRect(macro_banner_rect, 6, 6)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            macro_out_str = ", ".join(sorted(self.macro_virtual)) or "Action"
            painter.drawText(macro_banner_rect, Qt.AlignmentFlag.AlignCenter, f"MACRO TRIGGERED: {self.active_macro}  ->  [{macro_out_str}]")

        # ── 1. Gamepad Body Shell ──────────────────────────────────
        body_color = QColor("#FAF5FF") if self.macro_active else QColor("#F1F5F9")
        border_pen = QPen(QColor("#A855F7"), 3.5) if self.macro_active else QPen(QColor("#CBD5E1"), 2.5)
        painter.setPen(border_pen)
        painter.setBrush(QBrush(body_color))

        # Main ergonomic gamepad chassis
        painter.drawRoundedRect(QRectF(60, 50, 280, 150), 40, 40)
        # Left grip
        painter.drawRoundedRect(QRectF(30, 80, 75, 140), 32, 32)
        # Right grip
        painter.drawRoundedRect(QRectF(295, 80, 75, 140), 32, 32)

        # Center Grip Bridge
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(body_color))
        painter.drawRect(QRectF(85, 75, 230, 110))

        # ── 2. Bumpers & Triggers (Top) ────────────────────────────
        # Left Trigger (LT)
        lt_macro = "LT" in self.macro_virtual
        lt_active = "LT" in self.physical_pressed or self.lt_val > 0.15 or lt_macro
        if lt_macro:
            lt_color = QColor("#A855F7")
            painter.setPen(QPen(QColor("#C084FC"), 2.2))
        else:
            lt_color = QColor("#38BDF8") if lt_active else QColor("#E2E8F0")
            painter.setPen(QPen(QColor("#94A3B8"), 1.5))
        painter.setBrush(QBrush(lt_color))
        painter.drawRoundedRect(QRectF(75, 18, 55, 22), 6, 6)
        painter.setPen(QColor("#FFFFFF") if (lt_active or lt_macro) else QColor("#0F172A"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lt_text = "LT [M]" if lt_macro else f"LT {int(self.lt_val*100)}%"
        painter.drawText(QRectF(75, 18, 55, 22), Qt.AlignmentFlag.AlignCenter, lt_text)

        # Right Trigger (RT)
        rt_macro = "RT" in self.macro_virtual
        rt_active = "RT" in self.physical_pressed or self.rt_val > 0.15 or rt_macro
        if rt_macro:
            rt_color = QColor("#A855F7")
            painter.setPen(QPen(QColor("#C084FC"), 2.2))
        else:
            rt_color = QColor("#38BDF8") if rt_active else QColor("#E2E8F0")
            painter.setPen(QPen(QColor("#94A3B8"), 1.5))
        painter.setBrush(QBrush(rt_color))
        painter.drawRoundedRect(QRectF(270, 18, 55, 22), 6, 6)
        painter.setPen(QColor("#FFFFFF") if (rt_active or rt_macro) else QColor("#0F172A"))
        rt_text = "RT [M]" if rt_macro else f"RT {int(self.rt_val*100)}%"
        painter.drawText(QRectF(270, 18, 55, 22), Qt.AlignmentFlag.AlignCenter, rt_text)

        # Left Bumper (LB)
        lb_macro = "LB" in self.macro_virtual
        lb_active = "LB" in self.physical_pressed or lb_macro
        if lb_macro:
            lb_color = QColor("#7C3AED")
            painter.setPen(QPen(QColor("#C084FC"), 2.0))
        else:
            lb_color = QColor("#0284C7") if lb_active else QColor("#CBD5E1")
            painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
        painter.setBrush(QBrush(lb_color))
        painter.drawRoundedRect(QRectF(70, 44, 65, 16), 5, 5)
        painter.setPen(QColor("#FFFFFF") if lb_active else QColor("#475569"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(70, 44, 65, 16), Qt.AlignmentFlag.AlignCenter, "LB [M]" if lb_macro else "LB")

        # Right Bumper (RB)
        rb_macro = "RB" in self.macro_virtual
        rb_active = "RB" in self.physical_pressed or rb_macro
        if rb_macro:
            rb_color = QColor("#7C3AED")
            painter.setPen(QPen(QColor("#C084FC"), 2.0))
        else:
            rb_color = QColor("#0284C7") if rb_active else QColor("#CBD5E1")
            painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
        painter.setBrush(QBrush(rb_color))
        painter.drawRoundedRect(QRectF(265, 44, 65, 16), 5, 5)
        painter.setPen(QColor("#FFFFFF") if rb_active else QColor("#475569"))
        painter.drawText(QRectF(265, 44, 65, 16), Qt.AlignmentFlag.AlignCenter, "RB [M]" if rb_macro else "RB")

        # ── 3. D-Pad (Left Lower Area) ─────────────────────────────
        dpad_center_x, dpad_center_y = 125, 145
        dpad_w, dpad_h = 20, 20
        d_color_base = QColor("#E2E8F0")
        d_color_active = QColor("#0284C7")
        d_color_macro = QColor("#A855F7")

        # D-pad Up
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        col_up = d_color_macro if "Up" in self.macro_virtual else (d_color_active if "Up" in self.physical_pressed else d_color_base)
        painter.setBrush(QBrush(col_up))
        painter.drawRoundedRect(QRectF(dpad_center_x - 10, dpad_center_y - 30, dpad_w, dpad_h), 3, 3)

        # D-pad Down
        col_down = d_color_macro if "Down" in self.macro_virtual else (d_color_active if "Down" in self.physical_pressed else d_color_base)
        painter.setBrush(QBrush(col_down))
        painter.drawRoundedRect(QRectF(dpad_center_x - 10, dpad_center_y + 10, dpad_w, dpad_h), 3, 3)

        # D-pad Left
        col_left = d_color_macro if "Left" in self.macro_virtual else (d_color_active if "Left" in self.physical_pressed else d_color_base)
        painter.setBrush(QBrush(col_left))
        painter.drawRoundedRect(QRectF(dpad_center_x - 30, dpad_center_y - 10, dpad_w, dpad_h), 3, 3)

        # D-pad Right
        col_right = d_color_macro if "Right" in self.macro_virtual else (d_color_active if "Right" in self.physical_pressed else d_color_base)
        painter.setBrush(QBrush(col_right))
        painter.drawRoundedRect(QRectF(dpad_center_x + 10, dpad_center_y - 10, dpad_w, dpad_h), 3, 3)

        # D-pad Center connector
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(d_color_base))
        painter.drawRect(QRectF(dpad_center_x - 10, dpad_center_y - 10, dpad_w, dpad_h))

        # ── 4. ABXY Action Buttons (Right Cluster) ─────────────────
        btn_cluster_x, btn_cluster_y = 285, 100
        btn_radius = 12

        buttons_def = [
            ("Y", btn_cluster_x, btn_cluster_y - 25, QColor("#EAB308")),   # Yellow
            ("A", btn_cluster_x, btn_cluster_y + 25, QColor("#22C55E")),   # Green
            ("X", btn_cluster_x - 25, btn_cluster_y, QColor("#3B82F6")),   # Blue
            ("B", btn_cluster_x + 25, btn_cluster_y, QColor("#EF4444")),   # Red
        ]

        for b_name, bx, by, glow_col in buttons_def:
            is_macro_btn = b_name in self.macro_virtual
            is_pressed = b_name in self.physical_pressed

            if is_macro_btn:
                # Glowing Neon Purple Pulse Halo
                painter.setPen(QPen(QColor("#C084FC"), 3.5))
                painter.setBrush(QBrush(QColor("#FAF5FF")))
                painter.drawEllipse(QPointF(bx, by), btn_radius + 4, btn_radius + 4)

                painter.setPen(QPen(QColor("#7C3AED"), 2.0))
                painter.setBrush(QBrush(QColor("#9333EA")))
                painter.drawEllipse(QPointF(bx, by), btn_radius, btn_radius)

                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(bx - btn_radius, by - btn_radius, btn_radius * 2, btn_radius * 2), Qt.AlignmentFlag.AlignCenter, b_name)
            elif is_pressed:
                painter.setPen(QPen(glow_col, 2.5))
                painter.setBrush(QBrush(glow_col))
                painter.drawEllipse(QPointF(bx, by), btn_radius, btn_radius)
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(bx - btn_radius, by - btn_radius, btn_radius * 2, btn_radius * 2), Qt.AlignmentFlag.AlignCenter, b_name)
            else:
                painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.drawEllipse(QPointF(bx, by), btn_radius, btn_radius)
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(glow_col)
                painter.drawText(QRectF(bx - btn_radius, by - btn_radius, btn_radius * 2, btn_radius * 2), Qt.AlignmentFlag.AlignCenter, b_name)

        # ── 5. Analog Thumbsticks ──────────────────────────────────
        # Left Stick (Top Left)
        ls_center_x, ls_center_y = 120, 95
        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.drawEllipse(QPointF(ls_center_x, ls_center_y), 24, 24)

        # Moving Left Nub
        ls_pressed = "LS" in self.physical_pressed
        ls_nub_x = ls_center_x + self.lx_val * 14
        ls_nub_y = ls_center_y + self.ly_val * 14
        painter.setPen(QPen(QColor("#0284C7") if ls_pressed else QColor("#94A3B8"), 2))
        painter.setBrush(QBrush(QColor("#0284C7") if ls_pressed else QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(ls_nub_x, ls_nub_y), 16, 16)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF") if ls_pressed else QColor("#64748B"))
        painter.drawText(QRectF(ls_nub_x - 16, ls_nub_y - 16, 32, 32), Qt.AlignmentFlag.AlignCenter, "LS")

        # Right Stick (Bottom Right)
        rs_center_x, rs_center_y = 240, 150
        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.drawEllipse(QPointF(rs_center_x, rs_center_y), 24, 24)

        # Moving Right Nub
        rs_pressed = "RS" in self.physical_pressed
        rs_nub_x = rs_center_x + self.rx_val * 14
        rs_nub_y = rs_center_y + self.ry_val * 14
        painter.setPen(QPen(QColor("#0284C7") if rs_pressed else QColor("#94A3B8"), 2))
        painter.setBrush(QBrush(QColor("#0284C7") if rs_pressed else QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(rs_nub_x, rs_nub_y), 16, 16)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF") if rs_pressed else QColor("#64748B"))
        painter.drawText(QRectF(rs_nub_x - 16, rs_nub_y - 16, 32, 32), Qt.AlignmentFlag.AlignCenter, "RS")

        # ── 6. Center Navigation (BACK, XBOX/HOME, START) ──────────
        # BACK / VIEW
        back_active = "BACK" in self.physical_pressed
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(QBrush(QColor("#0284C7") if back_active else QColor("#E2E8F0")))
        painter.drawRoundedRect(QRectF(170, 95, 14, 10), 3, 3)

        # START / MENU
        start_active = "START" in self.physical_pressed
        painter.setBrush(QBrush(QColor("#0284C7") if start_active else QColor("#E2E8F0")))
        painter.drawRoundedRect(QRectF(216, 95, 14, 10), 3, 3)

        # Center Ares / Xbox Home Sphere
        painter.setPen(QPen(QColor("#0284C7"), 2))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(200, 75), 12, 12)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#0284C7"))
        painter.drawText(QRectF(188, 63, 24, 24), Qt.AlignmentFlag.AlignCenter, "X")

        # ── 7. Active Macro / Output Telemetry Banner ───────────────
        if self.physical_pressed or self.virtual_pressed or self.macro_active:
            phys_str = ", ".join(sorted(self.physical_pressed)) or "None"
            virt_str = ", ".join(sorted(self.virtual_pressed)) or "None"
            painter.setPen(QPen(QColor("#C084FC") if self.macro_active else QColor("#E2E8F0"), 1.5 if self.macro_active else 1.0))
            painter.setBrush(QBrush(QColor("#FAF5FF") if self.macro_active else QColor("#FFFFFF")))
            painter.drawRoundedRect(QRectF(30, 222, 340, 24), 6, 6)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            if self.macro_active and self.active_macro:
                painter.setPen(QColor("#7C3AED"))
                painter.drawText(QRectF(35, 222, 330, 24), Qt.AlignmentFlag.AlignCenter, f"MACRO: {self.active_macro}  |  Virtual [{virt_str}]")
            else:
                painter.setPen(QColor("#0F172A"))
                painter.drawText(QRectF(35, 222, 330, 24), Qt.AlignmentFlag.AlignCenter, f"Physical [{phys_str}]  ->  Virtual Output [{virt_str}]")

        painter.restore()
