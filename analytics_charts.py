"""
SRIVANI BOOKING MANAGER - Interactive Pure-Tkinter Analytics Charting Library
High-performance Canvas-based interactive charting components:
- CanvasBarChart: Multi-series or single-series bar chart with dynamic scaling,
  gridlines, and interactive hover tooltips.
- CanvasDonutChart: Ring/donut chart with center KPI counter, legend, and hover tooltips.
- CanvasLineChart: Smooth trend polyline with data points and hover inspection.
Zero third-party C-extensions required; native Windows compatibility and theme-aware.
"""
import tkinter as tk
from tkinter import ttk
import math
from typing import List, Dict, Tuple, Any, Optional

from themes import get_theme_palette, get_current_theme_name


class TooltipPopup:
    """Floating tooltip bubble on hover for canvas charts."""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.tag = "chart_tooltip"

    def show(self, x: float, y: float, text: str, bg="#0F172A", fg="#FFFFFF"):
        self.hide()
        # Draw small balloon with text
        # Bound coordinates to avoid clipping outside canvas
        cw = max(200, self.canvas.winfo_width())
        ch = max(150, self.canvas.winfo_height())

        # Position slightly above/to the right of target point
        tx = x + 12
        ty = y - 28
        if tx + 140 > cw:
            tx = x - 130
        if ty < 10:
            ty = y + 15

        # Measure text approximation
        lines = text.split("\n")
        w_box = max(len(l) for l in lines) * 7 + 16
        h_box = len(lines) * 16 + 10

        self.canvas.create_rectangle(
            tx, ty, tx + w_box, ty + h_box,
            fill=bg, outline="#38BDF8", width=1.5,
            tags=self.tag
        )
        self.canvas.create_text(
            tx + 8, ty + 6,
            text=text,
            anchor="nw",
            font=("Segoe UI", 8, "bold"),
            fill=fg,
            tags=self.tag,
        )

    def hide(self):
        self.canvas.delete(self.tag)


class CanvasBarChart(tk.Canvas):
    """
    Interactive Bar Chart with auto-scaling Y axis, grid lines,
    legend, and hover tooltips.
    """
    def __init__(self, parent, bg=None, highlightthickness=0, **kwargs):
        palette = get_theme_palette()
        chart_bg = bg or palette.get("bg_card", "#FFFFFF")
        super().__init__(parent, bg=chart_bg, highlightthickness=highlightthickness, **kwargs)

        self.tooltip = TooltipPopup(self)
        self.bars_meta: List[Dict[str, Any]] = []
        self.raw_data: List[Dict[str, Any]] = []
        self.title_text = ""
        self.val_key = "value"
        self.label_key = "label"
        self.secondary_key = ""
        self.bar_color = "#2563EB"
        self.sec_color = "#F59E0B"

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Leave>", lambda e: self.tooltip.hide())

    def set_data(
        self,
        data: List[Dict[str, Any]],
        label_key: str = "label",
        val_key: str = "value",
        secondary_key: str = "",
        title: str = "",
        bar_color: str = "#2563EB",
        sec_color: str = "#F59E0B",
    ):
        """Update chart data and redraw."""
        self.raw_data = data or []
        self.label_key = label_key
        self.val_key = val_key
        self.secondary_key = secondary_key
        self.title_text = title
        self.bar_color = bar_color
        self.sec_color = sec_color
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.bars_meta.clear()

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50:
            return

        palette = get_theme_palette()
        is_dark = get_current_theme_name() == "dark"
        fg_text = palette.get("fg_text", "#0F172A")
        fg_muted = palette.get("fg_muted", "#64748B")
        border_c = palette.get("border", "#E2E8F0")

        # Empty state handling
        if not self.raw_data:
            self.create_text(
                w / 2, h / 2 - 8,
                text="📊",
                font=("Segoe UI", 24),
                fill=fg_muted,
                anchor="center",
            )
            self.create_text(
                w / 2, h / 2 + 20,
                text="No performance data available for this range",
                font=("Segoe UI", 9, "italic"),
                fill=fg_muted,
                anchor="center",
            )
            return

        # Margins
        pad_left = 54
        pad_right = 24
        pad_top = 36 if self.title_text else 20
        pad_bottom = 44

        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bottom
        if chart_w <= 10 or chart_h <= 10:
            return

        # Title
        if self.title_text:
            self.create_text(
                pad_left, 14,
                text=self.title_text,
                font=("Segoe UI", 10, "bold"),
                fill=fg_text,
                anchor="w",
            )

        # Max Value Calculation
        max_val = 0.0
        for d in self.raw_data:
            v1 = float(d.get(self.val_key, 0) or 0)
            v2 = float(d.get(self.secondary_key, 0) or 0) if self.secondary_key else 0.0
            max_val = max(max_val, v1, v2)

        if max_val <= 0:
            max_val = 1.0

        # Round max_val up to clean tick step
        magnitude = 10 ** math.floor(math.log10(max(1.0, max_val)))
        step = max(1.0, math.ceil(max_val / 4.0 / magnitude) * magnitude)
        top_y_val = step * 4
        if top_y_val < max_val:
            top_y_val = step * 5

        # Draw Gridlines & Y-Axis labels
        for i in range(5):
            y_tick = (top_y_val / 4.0) * i
            y_pos = pad_top + chart_h - (i * (chart_h / 4.0))

            # Gridline
            self.create_line(
                pad_left, y_pos, pad_left + chart_w, y_pos,
                fill=border_c,
                dash=(3, 3) if i > 0 else (),
                width=1,
            )
            # Label
            tick_str = f"{int(y_tick)}" if y_tick == int(y_tick) else f"{y_tick:.1f}"
            self.create_text(
                pad_left - 8, y_pos,
                text=tick_str,
                font=("Segoe UI", 8),
                fill=fg_muted,
                anchor="e",
            )

        # Draw Bars
        n_items = len(self.raw_data)
        col_w = chart_w / max(1, n_items)
        has_sec = bool(self.secondary_key)

        bar_sub_w = max(4.0, (col_w * 0.7) / (2.0 if has_sec else 1.0))
        bar_sub_w = min(bar_sub_w, 36.0)

        # Skip labels if too crowded
        label_skip = max(1, int(n_items / (chart_w / 60)))

        for idx, item in enumerate(self.raw_data):
            cx = pad_left + idx * col_w + (col_w / 2.0)
            v1 = float(item.get(self.val_key, 0) or 0)
            h1 = (v1 / top_y_val) * chart_h
            y1_top = pad_top + chart_h - h1

            if has_sec:
                # Grouped bar 1 (Primary)
                bx1 = cx - bar_sub_w
                bx2 = cx
                self.create_rectangle(bx1, y1_top, bx2, pad_top + chart_h, fill=self.bar_color, outline="")
                self.bars_meta.append({
                    "rect": (bx1, y1_top, bx2, pad_top + chart_h),
                    "text": f"{item.get(self.label_key)}: {v1:.0f} (Booked)",
                })

                # Grouped bar 2 (Secondary)
                v2 = float(item.get(self.secondary_key, 0) or 0)
                h2 = (v2 / top_y_val) * chart_h
                y2_top = pad_top + chart_h - h2
                bx3 = cx
                bx4 = cx + bar_sub_w
                self.create_rectangle(bx3, y2_top, bx4, pad_top + chart_h, fill=self.sec_color, outline="")
                self.bars_meta.append({
                    "rect": (bx3, y2_top, bx4, pad_top + chart_h),
                    "text": f"{item.get(self.label_key)}: {v2:.0f} (Pending)",
                })
            else:
                bx1 = cx - (bar_sub_w / 2.0)
                bx2 = cx + (bar_sub_w / 2.0)
                self.create_rectangle(bx1, y1_top, bx2, pad_top + chart_h, fill=self.bar_color, outline="")
                rev = item.get("booked_revenue", None)
                txt = f"{item.get(self.label_key)}: {v1:.0f}"
                if rev is not None:
                    txt += f"\nRevenue: ₹{rev:,.2f}"
                self.bars_meta.append({
                    "rect": (bx1, y1_top, bx2, pad_top + chart_h),
                    "text": txt,
                })

            # X-Axis Label
            if idx % label_skip == 0:
                raw_lbl = str(item.get(self.label_key, ""))
                # Shorten date or week
                if len(raw_lbl) >= 10:
                    lbl = raw_lbl[5:]  # MM-DD
                else:
                    lbl = raw_lbl
                self.create_text(
                    cx, pad_top + chart_h + 10,
                    text=lbl,
                    font=("Segoe UI", 8),
                    fill=fg_muted,
                    anchor="n",
                )

    def _on_mouse_move(self, event):
        mx, my = event.x, event.y
        for meta in self.bars_meta:
            x1, y1, x2, y2 = meta["rect"]
            if x1 <= mx <= x2 and y1 <= my <= y2:
                self.tooltip.show(mx, my, meta["text"])
                return
        self.tooltip.hide()


class CanvasDonutChart(tk.Canvas):
    """
    Interactive Donut / Pie chart with percentage labels,
    center counter, color legend, and interactive mouse hover tooltips.
    """
    def __init__(self, parent, bg=None, highlightthickness=0, **kwargs):
        palette = get_theme_palette()
        chart_bg = bg or palette.get("bg_card", "#FFFFFF")
        super().__init__(parent, bg=chart_bg, highlightthickness=highlightthickness, **kwargs)

        self.tooltip = TooltipPopup(self)
        self.slices_data: List[Tuple[str, float, str]] = []
        self.title_text = ""
        self.center_label = ""
        self.slices_meta: List[Dict[str, Any]] = []

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Leave>", lambda e: self.tooltip.hide())

    def set_data(
        self,
        slices: List[Tuple[str, float, str]],
        title: str = "",
        center_label: str = "",
    ):
        """Update chart slices [(label, value, hex_color)]."""
        self.slices_data = [s for s in slices if s[1] > 0]
        self.title_text = title
        self.center_label = center_label
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.slices_meta.clear()

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50:
            return

        palette = get_theme_palette()
        fg_text = palette.get("fg_text", "#0F172A")
        fg_muted = palette.get("fg_muted", "#64748B")
        bg_card = self["bg"]

        total = sum(s[1] for s in self.slices_data)

        if total <= 0:
            self.create_text(
                w / 2, h / 2 - 8,
                text="⭕",
                font=("Segoe UI", 24),
                fill=fg_muted,
                anchor="center",
            )
            self.create_text(
                w / 2, h / 2 + 20,
                text="Zero records recorded",
                font=("Segoe UI", 9, "italic"),
                fill=fg_muted,
                anchor="center",
            )
            return

        # Title
        if self.title_text:
            self.create_text(
                20, 16,
                text=self.title_text,
                font=("Segoe UI", 10, "bold"),
                fill=fg_text,
                anchor="w",
            )

        # Layout: Left side Donut, Right side Legend
        cx = min(w * 0.38, 160.0)
        cy = h / 2.0 + (6 if self.title_text else 0)
        outer_r = min(cx - 24, cy - 24, 80.0)
        inner_r = outer_r * 0.54

        if outer_r < 20:
            return

        start_angle = 90.0
        for label, val, color in self.slices_data:
            extent = (val / total) * 360.0
            pct = (val / total) * 100.0

            # Outer pie slice
            x0 = cx - outer_r
            y0 = cy - outer_r
            x1 = cx + outer_r
            y1 = cy + outer_r
            self.create_arc(
                x0, y0, x1, y1,
                start=start_angle,
                extent=-extent,
                fill=color,
                outline=bg_card,
                width=1.5,
            )

            self.slices_meta.append({
                "label": label,
                "value": val,
                "pct": pct,
                "start": start_angle,
                "end": start_angle - extent,
                "cx": cx,
                "cy": cy,
                "outer_r": outer_r,
                "inner_r": inner_r,
            })
            start_angle -= extent

        # Inner cutout circle (Donut effect)
        self.create_oval(
            cx - inner_r, cy - inner_r,
            cx + inner_r, cy + inner_r,
            fill=bg_card,
            outline="",
        )

        # Center Total text
        self.create_text(
            cx, cy - 6,
            text=f"{int(total)}",
            font=("Segoe UI", 12, "bold"),
            fill=fg_text,
            anchor="center",
        )
        self.create_text(
            cx, cy + 10,
            text=self.center_label or "TOTAL",
            font=("Segoe UI", 7, "bold"),
            fill=fg_muted,
            anchor="center",
        )

        # Legend on the right
        leg_x = cx + outer_r + 28
        leg_y = max(24, cy - (len(self.slices_data) * 12))

        for label, val, color in self.slices_data:
            pct = (val / total) * 100.0
            # Color swatch
            self.create_rectangle(
                leg_x, leg_y, leg_x + 10, leg_y + 10,
                fill=color, outline="",
            )
            # Text
            self.create_text(
                leg_x + 16, leg_y + 5,
                text=f"{label}: {int(val)} ({pct:.1f}%)",
                font=("Segoe UI", 8, "bold"),
                fill=fg_text,
                anchor="w",
            )
            leg_y += 22

    def _on_mouse_move(self, event):
        mx, my = event.x, event.y
        for s in self.slices_meta:
            cx, cy = s["cx"], s["cy"]
            dx = mx - cx
            dy = my - cy
            dist = math.hypot(dx, dy)
            if s["inner_r"] <= dist <= s["outer_r"]:
                angle = math.degrees(math.atan2(-dy, dx))
                if angle < 0:
                    angle += 360.0
                # Normalizing angles
                # Show tooltip
                self.tooltip.show(mx, my, f"{s['label']}\nCount: {int(s['value'])}\nShare: {s['pct']:.1f}%")
                return
        self.tooltip.hide()


class CanvasLineChart(tk.Canvas):
    """
    Smooth trend line chart with dots and interactive tooltips.
    """
    def __init__(self, parent, bg=None, highlightthickness=0, **kwargs):
        palette = get_theme_palette()
        chart_bg = bg or palette.get("bg_card", "#FFFFFF")
        super().__init__(parent, bg=chart_bg, highlightthickness=highlightthickness, **kwargs)

        self.tooltip = TooltipPopup(self)
        self.points_meta: List[Dict[str, Any]] = []
        self.raw_data: List[Dict[str, Any]] = []
        self.x_key = "date"
        self.y_key = "value"
        self.line_color = "#0284C7"
        self.title_text = ""

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Leave>", lambda e: self.tooltip.hide())

    def set_data(
        self,
        data: List[Dict[str, Any]],
        x_key: str = "date",
        y_key: str = "value",
        title: str = "",
        line_color: str = "#0284C7",
    ):
        self.raw_data = data or []
        self.x_key = x_key
        self.y_key = y_key
        self.title_text = title
        self.line_color = line_color
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.points_meta.clear()

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50:
            return

        palette = get_theme_palette()
        fg_text = palette.get("fg_text", "#0F172A")
        fg_muted = palette.get("fg_muted", "#64748B")
        border_c = palette.get("border", "#E2E8F0")

        if not self.raw_data:
            self.create_text(
                w / 2, h / 2,
                text="📈 No trend data recorded",
                font=("Segoe UI", 9, "italic"),
                fill=fg_muted,
                anchor="center",
            )
            return

        pad_left = 60
        pad_right = 24
        pad_top = 34 if self.title_text else 20
        pad_bottom = 36

        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bottom
        if chart_w <= 10 or chart_h <= 10:
            return

        if self.title_text:
            self.create_text(
                pad_left, 14,
                text=self.title_text,
                font=("Segoe UI", 10, "bold"),
                fill=fg_text,
                anchor="w",
            )

        max_val = max((float(d.get(self.y_key, 0) or 0) for d in self.raw_data), default=1.0)
        if max_val <= 0:
            max_val = 1.0

        # Draw grid
        for i in range(5):
            y_tick = (max_val / 4.0) * i
            y_pos = pad_top + chart_h - (i * (chart_h / 4.0))
            self.create_line(pad_left, y_pos, pad_left + chart_w, y_pos, fill=border_c, dash=(3, 3) if i > 0 else ())
            tick_fmt = f"₹{y_tick:,.0f}" if y_tick >= 1000 else f"{y_tick:.0f}"
            self.create_text(pad_left - 8, y_pos, text=tick_fmt, font=("Segoe UI", 8), fill=fg_muted, anchor="e")

        n = len(self.raw_data)
        col_w = chart_w / max(1, n - 1) if n > 1 else chart_w
        coords = []

        for idx, item in enumerate(self.raw_data):
            px = pad_left + idx * col_w if n > 1 else pad_left + (chart_w / 2)
            vy = float(item.get(self.y_key, 0) or 0)
            py = pad_top + chart_h - (vy / max_val * chart_h)
            coords.extend([px, py])

            self.points_meta.append({
                "x": px,
                "y": py,
                "text": f"{item.get(self.x_key)}\nAmount: ₹{vy:,.2f}",
            })

            # X label
            if n <= 10 or idx % max(1, int(n / 6)) == 0:
                lbl = str(item.get(self.x_key, ""))
                if len(lbl) >= 10:
                    lbl = lbl[5:]
                self.create_text(px, pad_top + chart_h + 8, text=lbl, font=("Segoe UI", 8), fill=fg_muted, anchor="n")

        if len(coords) >= 4:
            self.create_line(*coords, fill=self.line_color, width=2.5, smooth=True)

        for pt in self.points_meta:
            px, py = pt["x"], pt["y"]
            self.create_oval(px - 3.5, py - 3.5, px + 3.5, py + 3.5, fill=self.line_color, outline="#FFFFFF", width=1.5)

    def _on_mouse_move(self, event):
        mx, my = event.x, event.y
        for pt in self.points_meta:
            if math.hypot(mx - pt["x"], my - pt["y"]) <= 8:
                self.tooltip.show(mx, my, pt["text"])
                return
        self.tooltip.hide()
