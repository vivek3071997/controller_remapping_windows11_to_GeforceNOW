"""
visualizer_widget.py – Interactive Controller Hardware Model Visualizer (PyQt6)
================================================================================
Renders a modern, precision-scaled vector gamepad model representing physical
controllers (Cosmic Byte Ares Pro / Xbox style). Dynamically lights up physical
button presses, highlights remapped target outputs, and animates analog sticks
and triggers in real time.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath, QLinearGradient
from PyQt6.QtWidgets import QWidget

class ControllerVisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self.connected = False
        self.controller_name = "No controller detected"
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
        self.active_actions = []

        # Pre-built reusable Bezier controller contour path
        self._body_path = QPainterPath()
        self._body_path.moveTo(90, 60)
        self._body_path.cubicTo(120, 45, 280, 45, 310, 60)
        self._body_path.cubicTo(350, 80, 390, 160, 360, 210)
        self._body_path.cubicTo(340, 240, 300, 210, 270, 180)
        self._body_path.cubicTo(230, 170, 170, 170, 130, 180)
        self._body_path.cubicTo(100, 210, 60, 240, 40, 210)
        self._body_path.cubicTo(10, 160, 50, 80, 90, 60)
        self._body_path.closeSubpath()

        # Pre-cached reusable UI fonts
        self._font_bold_8 = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self._font_bold_9 = QFont("Segoe UI", 9, QFont.Weight.Bold)

    def update_telemetry(self, data: dict):
        self.connected = data.get("connected", False)
        self.controller_name = data.get("controller_name", "Connected Gamepad")
        self.physical_pressed = set(data.get("physical_pressed") or data.get("physical_buttons") or [])
        self.virtual_pressed = set(data.get("virtual_pressed") or data.get("virtual_buttons") or [])
        self.lt_val = data.get("lt", 0.0)
        self.rt_val = data.get("rt", 0.0)
        self.lx_val = data.get("lx", 0.0)
        self.ly_val = data.get("ly", 0.0)
        self.rx_val = data.get("rx", 0.0)
        self.ry_val = data.get("ry", 0.0)
        self.active_macro = data.get("last_macro") or data.get("macro_name") or ""
        self.macro_active = bool(data.get("macro_active", False) or self.active_macro)
        self.macro_virtual = set(data.get("macro_virtual") or ([data.get("macro_output")] if data.get("macro_output") else []))
        self.active_actions = list(data.get("active_actions", []))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Scale and center controller model in widget
        scale = min(w / 430.0, h / 265.0)
        painter.save()
        painter.translate((w - 400 * scale) / 2.0, (h - 240 * scale) / 2.0)
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

        # ── 1. Authentic Ergonomic Gamepad Chassis (Bezier Path) ──
        body_color = QColor("#FAF5FF") if self.macro_active else QColor("#FFFFFF")
        border_pen = QPen(QColor("#A855F7"), 3.5) if self.macro_active else QPen(QColor("#CBD5E1"), 2.8)
        painter.setPen(border_pen)
        painter.setBrush(QBrush(body_color))
        painter.drawPath(self._body_path)

        # ── 2. Bumpers & Triggers (Top) ────────────────────────────
        # Left Trigger (LT)
        lt_macro = "LT" in self.macro_virtual
        lt_active = ("LT" in self.physical_pressed) or ("LT" in self.virtual_pressed) or (self.lt_val > 0.15) or lt_macro
        lt_rect = QRectF(80, 18, 55, 26)
        
        if lt_macro:
            painter.setPen(QPen(QColor("#C084FC"), 2.4))
            painter.setBrush(QBrush(QColor("#7C3AED")))
            painter.drawRoundedRect(lt_rect, 6, 6)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(lt_rect, Qt.AlignmentFlag.AlignCenter, "LT [M]")
        elif lt_active:
            # Active illuminated trigger with depth fill
            painter.setPen(QPen(QColor("#0284C7"), 2.2))
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(lt_rect, 6, 6)
            # Inner fill meter based on trigger pull
            fill_pct = max(0.2, self.lt_val) if self.lt_val > 0.05 else 1.0
            meter_h = (lt_rect.height() - 4) * fill_pct
            meter_rect = QRectF(lt_rect.left() + 2, lt_rect.bottom() - 2 - meter_h, lt_rect.width() - 4, meter_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#38BDF8")))
            painter.drawRoundedRect(meter_rect, 4, 4)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            pct_txt = f"LT {int(self.lt_val * 100)}%" if self.lt_val > 0.05 else "LT"
            painter.drawText(lt_rect, Qt.AlignmentFlag.AlignCenter, pct_txt)
        else:
            # Idle highlighted badge
            painter.setPen(QPen(QColor("#0284C7"), 2.0))
            painter.setBrush(QBrush(QColor("#F0F9FF")))
            painter.drawRoundedRect(lt_rect, 6, 6)
            painter.setPen(QColor("#0284C7"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(lt_rect, Qt.AlignmentFlag.AlignCenter, "LT")

        # Right Trigger (RT)
        rt_macro = "RT" in self.macro_virtual
        rt_active = ("RT" in self.physical_pressed) or ("RT" in self.virtual_pressed) or (self.rt_val > 0.15) or rt_macro
        rt_rect = QRectF(265, 18, 55, 26)

        if rt_macro:
            painter.setPen(QPen(QColor("#C084FC"), 2.4))
            painter.setBrush(QBrush(QColor("#7C3AED")))
            painter.drawRoundedRect(rt_rect, 6, 6)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rt_rect, Qt.AlignmentFlag.AlignCenter, "RT [M]")
        elif rt_active:
            # Active illuminated trigger with depth fill
            painter.setPen(QPen(QColor("#0284C7"), 2.2))
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(rt_rect, 6, 6)
            fill_pct = max(0.2, self.rt_val) if self.rt_val > 0.05 else 1.0
            meter_h = (rt_rect.height() - 4) * fill_pct
            meter_rect = QRectF(rt_rect.left() + 2, rt_rect.bottom() - 2 - meter_h, rt_rect.width() - 4, meter_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#38BDF8")))
            painter.drawRoundedRect(meter_rect, 4, 4)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            pct_txt = f"RT {int(self.rt_val * 100)}%" if self.rt_val > 0.05 else "RT"
            painter.drawText(rt_rect, Qt.AlignmentFlag.AlignCenter, pct_txt)
        else:
            # Idle highlighted badge
            painter.setPen(QPen(QColor("#0284C7"), 2.0))
            painter.setBrush(QBrush(QColor("#F0F9FF")))
            painter.drawRoundedRect(rt_rect, 6, 6)
            painter.setPen(QColor("#0284C7"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rt_rect, Qt.AlignmentFlag.AlignCenter, "RT")

        # Left Bumper (LB)
        lb_macro = "LB" in self.macro_virtual
        lb_active = ("LB" in self.physical_pressed) or ("LB" in self.virtual_pressed) or lb_macro
        lb_rect = QRectF(75, 47, 65, 17)
        if lb_macro:
            painter.setPen(QPen(QColor("#C084FC"), 2.2))
            painter.setBrush(QBrush(QColor("#7C3AED")))
            painter.drawRoundedRect(lb_rect, 5, 5)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(lb_rect, Qt.AlignmentFlag.AlignCenter, "LB [M]")
        elif lb_active:
            painter.setPen(QPen(QColor("#0369A1"), 2.2))
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(lb_rect, 5, 5)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(lb_rect, Qt.AlignmentFlag.AlignCenter, "LB")
        else:
            painter.setPen(QPen(QColor("#0284C7"), 1.8))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRoundedRect(lb_rect, 5, 5)
            painter.setPen(QColor("#0284C7"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(lb_rect, Qt.AlignmentFlag.AlignCenter, "LB")

        # Right Bumper (RB)
        rb_macro = "RB" in self.macro_virtual
        rb_active = ("RB" in self.physical_pressed) or ("RB" in self.virtual_pressed) or rb_macro
        rb_rect = QRectF(260, 47, 65, 17)
        if rb_macro:
            painter.setPen(QPen(QColor("#C084FC"), 2.2))
            painter.setBrush(QBrush(QColor("#7C3AED")))
            painter.drawRoundedRect(rb_rect, 5, 5)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rb_rect, Qt.AlignmentFlag.AlignCenter, "RB [M]")
        elif rb_active:
            painter.setPen(QPen(QColor("#0369A1"), 2.2))
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(rb_rect, 5, 5)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rb_rect, Qt.AlignmentFlag.AlignCenter, "RB")
        else:
            painter.setPen(QPen(QColor("#0284C7"), 1.8))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRoundedRect(rb_rect, 5, 5)
            painter.setPen(QColor("#0284C7"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rb_rect, Qt.AlignmentFlag.AlignCenter, "RB")

        # ── 3. D-Pad Cross ─────────────────────────────────────────
        d_color_base = QColor("#E2E8F0")
        d_color_active = QColor("#0284C7")
        d_color_macro = QColor("#A855F7")

        # Up
        up_active = ("Up" in self.physical_pressed) or ("Up" in self.virtual_pressed)
        up_macro = "Up" in self.macro_virtual
        col_up = d_color_macro if up_macro else (d_color_active if up_active else d_color_base)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(QBrush(col_up))
        painter.drawRoundedRect(QRectF(115, 115, 18, 20), 3, 3)

        # Down
        dn_active = ("Down" in self.physical_pressed) or ("Down" in self.virtual_pressed)
        dn_macro = "Down" in self.macro_virtual
        col_dn = d_color_macro if dn_macro else (d_color_active if dn_active else d_color_base)
        painter.setBrush(QBrush(col_dn))
        painter.drawRoundedRect(QRectF(115, 151, 18, 20), 3, 3)

        # Left
        lf_active = ("Left" in self.physical_pressed) or ("Left" in self.virtual_pressed)
        lf_macro = "Left" in self.macro_virtual
        col_lf = d_color_macro if lf_macro else (d_color_active if lf_active else d_color_base)
        painter.setBrush(QBrush(col_lf))
        painter.drawRoundedRect(QRectF(97, 133, 20, 18), 3, 3)

        # Right
        rt_dpad_active = ("Right" in self.physical_pressed) or ("Right" in self.virtual_pressed)
        rt_dpad_macro = "Right" in self.macro_virtual
        col_rt = d_color_macro if rt_dpad_macro else (d_color_active if rt_dpad_active else d_color_base)
        painter.setBrush(QBrush(col_rt))
        painter.drawRoundedRect(QRectF(131, 133, 20, 18), 3, 3)

        # Center D-pad block
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(d_color_base))
        painter.drawRect(QRectF(115, 133, 18, 18))

        # ── 4. ABXY Action Buttons (Right Cluster) ─────────────────
        buttons_def = [
            ("Y", 285, 80, QColor("#EAB308")),   # Yellow
            ("A", 285, 130, QColor("#22C55E")),  # Green
            ("X", 260, 105, QColor("#3B82F6")),  # Blue
            ("B", 310, 105, QColor("#EF4444")),  # Red
        ]

        for b_name, bx, by, glow_col in buttons_def:
            is_macro_btn = b_name in self.macro_virtual
            is_pressed = (b_name in self.physical_pressed) or (b_name in self.virtual_pressed)

            if is_macro_btn:
                # Glowing Neon Purple Pulse Halo
                painter.setPen(QPen(QColor("#C084FC"), 3.2))
                painter.setBrush(QBrush(QColor("#FAF5FF")))
                painter.drawEllipse(QPointF(bx, by), 16, 16)

                painter.setPen(QPen(QColor("#7C3AED"), 2.0))
                painter.setBrush(QBrush(QColor("#9333EA")))
                painter.drawEllipse(QPointF(bx, by), 12, 12)

                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(bx - 12, by - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, b_name)
            elif is_pressed:
                painter.setPen(QPen(glow_col, 2.5))
                painter.setBrush(QBrush(glow_col))
                painter.drawEllipse(QPointF(bx, by), 12, 12)
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(bx - 12, by - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, b_name)
            else:
                painter.setPen(QPen(glow_col, 2.0))
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.drawEllipse(QPointF(bx, by), 12, 12)
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(glow_col)
                painter.drawText(QRectF(bx - 12, by - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, b_name)

        # ── 5. Analog Thumbsticks ──────────────────────────────────
        # Left Stick Well (x=125, y=95)
        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.setBrush(QBrush(QColor("#F1F5F9")))
        painter.drawEllipse(QPointF(125, 95), 22, 22)

        # Moving Left Nub
        ls_pressed = ("LS" in self.physical_pressed) or ("LS" in self.virtual_pressed)
        ls_nub_x = 125 + self.lx_val * 14
        ls_nub_y = 95 + self.ly_val * 14
        painter.setPen(QPen(QColor("#0284C7") if ls_pressed else QColor("#94A3B8"), 2))
        painter.setBrush(QBrush(QColor("#0284C7") if ls_pressed else QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(ls_nub_x, ls_nub_y), 15, 15)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF") if ls_pressed else QColor("#64748B"))
        painter.drawText(QRectF(ls_nub_x - 15, ls_nub_y - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, "LS")

        # Right Stick Well (x=240, y=150)
        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.setBrush(QBrush(QColor("#F1F5F9")))
        painter.drawEllipse(QPointF(240, 150), 22, 22)

        # Moving Right Nub
        rs_pressed = ("RS" in self.physical_pressed) or ("RS" in self.virtual_pressed)
        rs_nub_x = 240 + self.rx_val * 14
        rs_nub_y = 150 + self.ry_val * 14
        painter.setPen(QPen(QColor("#0284C7") if rs_pressed else QColor("#94A3B8"), 2))
        painter.setBrush(QBrush(QColor("#0284C7") if rs_pressed else QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(rs_nub_x, rs_nub_y), 15, 15)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF") if rs_pressed else QColor("#64748B"))
        painter.drawText(QRectF(rs_nub_x - 15, rs_nub_y - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, "RS")

        # ── 6. Center Navigation (BACK, XBOX GUIDE, START) ─────────
        # BACK / VIEW (x=170, y=95)
        back_active = ("BACK" in self.physical_pressed) or ("BACK" in self.virtual_pressed)
        painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
        painter.setBrush(QBrush(QColor("#0284C7") if back_active else QColor("#E2E8F0")))
        painter.drawRoundedRect(QRectF(170, 95, 14, 10), 3, 3)

        # START / MENU (x=216, y=95)
        start_active = ("START" in self.physical_pressed) or ("START" in self.virtual_pressed)
        painter.setBrush(QBrush(QColor("#0284C7") if start_active else QColor("#E2E8F0")))
        painter.drawRoundedRect(QRectF(216, 95, 14, 10), 3, 3)

        # Center Guide Sphere (x=200, y=80)
        painter.setPen(QPen(QColor("#0284C7"), 2.2))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(200, 80), 12, 12)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#0284C7"))
        painter.drawText(QRectF(188, 68, 24, 24), Qt.AlignmentFlag.AlignCenter, "X")

        # ── 7. Active Telemetry / Live Action Status Banner ────────
        banner_rect = QRectF(30, 224, 340, 22)
        if self.physical_pressed or self.virtual_pressed or self.macro_active:
            phys_str = ", ".join(sorted(self.physical_pressed)) or "None"
            virt_str = ", ".join(sorted(self.virtual_pressed)) or "None"
            painter.setPen(QPen(QColor("#C084FC") if self.macro_active else QColor("#E2E8F0"), 1.5 if self.macro_active else 1.0))
            painter.setBrush(QBrush(QColor("#FAF5FF") if self.macro_active else QColor("#FFFFFF")))
            painter.drawRoundedRect(banner_rect, 6, 6)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            if self.macro_active and self.active_macro:
                painter.setPen(QColor("#7C3AED"))
                out_m = ", ".join(sorted(self.macro_virtual)) or virt_str
                painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, f"⚡ MACRO: {self.active_macro}  ->  [{out_m}]")
            else:
                act_str = f"  ({', '.join(self.active_actions)})" if getattr(self, "active_actions", None) else ""
                painter.setPen(QColor("#0369A1"))
                painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, f"[{phys_str}]  ->  Virtual [{virt_str}]{act_str}")
        else:
            # Controller connection status
            painter.setPen(QPen(QColor("#E2E8F0"), 1))
            painter.setBrush(QBrush(QColor("#F8FAFC")))
            painter.drawRoundedRect(banner_rect, 6, 6)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            if self.connected:
                painter.setPen(QColor("#16A34A"))
                painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, f"[CONNECTED] {self.controller_name}")
            else:
                painter.setPen(QColor("#64748B"))
                painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, "Waiting for controller... (Plug in USB or Wireless)")

        painter.restore()
