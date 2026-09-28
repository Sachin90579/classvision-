"""Design tokens and SVG primitives shared by every layout."""
from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass
from xml.sax.saxutils import escape

FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
BG, INK, MUTED, EDGE = "#F8FAFC", "#0F172A", "#475569", "#64748B"
PALETTE = [("#2563EB", "#DBEAFE"), ("#7C3AED", "#EDE9FE"), ("#059669", "#D1FAE5"),
           ("#D97706", "#FEF3C7"), ("#DB2777", "#FCE7F3"), ("#0891B2", "#CFFAFE")]
DEFS = (f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE}"/></marker></defs>')


def esc(text: object) -> str:
    return escape(str(text), {'"': "&quot;"})


def wrap(text: str, width: int, max_lines: int | None = None) -> list[str]:
    lines = textwrap.wrap(text.strip(), width=width, break_long_words=True) if text else []
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip(" .,;") + "…"
    return lines


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def measure(label: str, desc: str, width: float) -> tuple[float, list[str], list[str]]:
    """Return (box height, label lines, description lines) for a node of the given width."""
    label_lines = wrap(label, max(8, int(width / 12.5)), 3)
    desc_lines = wrap(desc, max(10, int(width / 8.2)), 3) if desc else []
    height = 30 + 27 * len(label_lines) + (12 + 19 * len(desc_lines) if desc_lines else 0)
    return max(64.0, float(height)), label_lines, desc_lines


def text(x: float, y: float, content: str, size: int, fill: str = INK, weight: str = "400", anchor: str = "middle") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(content)}</text>')


def node_svg(box: Box, label_lines: list[str], desc_lines: list[str], idx: int,
             badge: int | None = None, emphasis: bool = False) -> str:
    stroke, fill = PALETTE[idx % len(PALETTE)]
    parts = [f'<rect x="{box.x:.1f}" y="{box.y:.1f}" width="{box.w:.1f}" height="{box.h:.1f}" rx="16" '
             f'fill="{fill}" stroke="{stroke}" stroke-width="{5 if emphasis else 3}"/>']
    block = 27 * len(label_lines) + (12 + 19 * len(desc_lines) if desc_lines else 0)
    y = box.cy - block / 2
    for i, line in enumerate(label_lines):
        parts.append(text(box.cx, y + 27 * i + 20, line, 22, INK, "700"))
    for j, line in enumerate(desc_lines):
        parts.append(text(box.cx, y + 27 * len(label_lines) + 12 + 15 + 19 * j, line, 15, MUTED))
    if badge is not None:
        parts.append(f'<circle cx="{box.x:.1f}" cy="{box.y:.1f}" r="16" fill="{stroke}"/>')
        parts.append(text(box.x, box.y + 6, str(badge), 17, "#FFFFFF", "700"))
    return "".join(parts)


def label_svg(x: float, y: float, content: str) -> str:
    if not content:
        return ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="16" font-weight="600" fill="{INK}" text-anchor="middle" '
            f'stroke="{BG}" stroke-width="6" paint-order="stroke">{esc(content)}</text>')


def clip(cx: float, cy: float, w: float, h: float, tx: float, ty: float, pad: float = 4) -> tuple[float, float]:
    """Point where the ray from a box centre toward (tx, ty) leaves the box border."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2 + pad) / abs(dx) if dx else math.inf
    sy = (h / 2 + pad) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def straight_edge(a: Box, b: Box, label: str = "", offset: float = 0.0, arrow: bool = True) -> str:
    dx, dy = b.cx - a.cx, b.cy - a.cy
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * offset, dx / length * offset
    acx, acy, bcx, bcy = a.cx + nx, a.cy + ny, b.cx + nx, b.cy + ny
    x1, y1 = clip(acx, acy, a.w, a.h, bcx, bcy)
    x2, y2 = clip(bcx, bcy, b.w, b.h, acx, acy)
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    line = (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{EDGE}" '
            f'stroke-width="3" stroke-linecap="round"{marker}/>')
    return line + label_svg((x1 + x2) / 2, (y1 + y2) / 2 - 8, label)


def curved_edge(a: Box, b: Box, ctrl: tuple[float, float], label: str = "") -> str:
    x1, y1 = clip(a.cx, a.cy, a.w, a.h, *ctrl)
    x2, y2 = clip(b.cx, b.cy, b.w, b.h, *ctrl)
    path = (f'<path d="M{x1:.1f},{y1:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {x2:.1f},{y2:.1f}" fill="none" '
            f'stroke="{EDGE}" stroke-width="3" stroke-linecap="round" marker-end="url(#arrow)"/>')
    lx, ly = 0.25 * x1 + 0.5 * ctrl[0] + 0.25 * x2, 0.25 * y1 + 0.5 * ctrl[1] + 0.25 * y2
    return path + label_svg(lx, ly - 6, label)
