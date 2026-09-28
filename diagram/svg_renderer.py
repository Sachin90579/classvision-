"""Turns a validated DiagramSpec into a clean SVG. One layout function per diagram type."""
from __future__ import annotations

import math
from typing import NamedTuple

from diagram.templates import (BG, DEFS, EDGE, FONT, INK, MUTED, PALETTE, Box, curved_edge, esc, measure,
                               node_svg, straight_edge, text, wrap)

NODE_W, GAP_X, GAP_Y, MAX_PER_ROW = 230, 60, 100, 3


class Layout(NamedTuple):
    body: str
    w: float
    h: float


# ---------- helpers ----------
def _connections(spec, sequential: bool) -> list[tuple[str, str, str]]:
    conns = [(c.from_, c.to, c.label) for c in spec.connections]
    if not conns and sequential:
        conns = [(a.id, b.id, "") for a, b in zip(spec.nodes, spec.nodes[1:])]
    return conns


def _depths(ids: list[str], conns) -> dict[str, int]:
    depth = {i: 0 for i in ids}
    limit = len(ids) - 1
    for _ in range(len(ids)):
        changed = False
        for a, b, _l in conns:
            if a != b and depth[b] < depth[a] + 1 <= limit:
                depth[b] = depth[a] + 1
                changed = True
        if not changed:
            break
    return depth


def _edges(conns, boxes: dict[str, Box]) -> str:
    pairs = {(a, b) for a, b, _ in conns}
    out = []
    for a, b, label in conns:
        if a != b and a in boxes and b in boxes:
            out.append(straight_edge(boxes[a], boxes[b], label, 11 if (b, a) in pairs else 0))
    return "".join(out)


# ---------- layouts ----------
def layered(spec, numbered: bool = False) -> Layout:
    nodes = spec.nodes
    conns = _connections(spec, sequential=spec.diagram_type in ("flowchart", "process"))
    depth = _depths([n.id for n in nodes], conns)
    info = {n.id: measure(n.label, n.description, NODE_W) for n in nodes}
    rows: list[list] = []
    for d in sorted(set(depth.values())):
        row = [n for n in nodes if depth[n.id] == d]
        rows += [row[i:i + MAX_PER_ROW] for i in range(0, len(row), MAX_PER_ROW)]
    width_of = lambda r: len(r) * NODE_W + (len(r) - 1) * GAP_X  # noqa: E731
    cw = max(width_of(r) for r in rows)
    boxes: dict[str, Box] = {}
    y = 0.0
    for row in rows:
        row_h = max(info[n.id][0] for n in row)
        x = (cw - width_of(row)) / 2
        for n in row:
            h = info[n.id][0]
            boxes[n.id] = Box(x, y + (row_h - h) / 2, NODE_W, h)
            x += NODE_W + GAP_X
        y += row_h + GAP_Y
    body = _edges(conns, boxes)
    for i, n in enumerate(nodes):
        body += node_svg(boxes[n.id], info[n.id][1], info[n.id][2], i, badge=i + 1 if numbered else None)
    return Layout(body, cw, y - GAP_Y)


def process(spec) -> Layout:
    return layered(spec, numbered=True)


def timeline(spec) -> Layout:
    x_line, card_x, card_w = 40, 100, 760
    y, items, marks = 10.0, [], []
    for i, n in enumerate(spec.nodes):
        ll, dl = wrap(n.label, 42, 2), wrap(n.description, 64, 3)
        h = max(72.0, 24 + 27 * len(ll) + (10 + 21 * len(dl) if dl else 0))
        stroke, fill = PALETTE[i % len(PALETTE)]
        card = (f'<rect x="{card_x}" y="{y:.1f}" width="{card_w}" height="{h:.1f}" rx="14" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="3"/>')
        ty = y + 12
        for line in ll:
            ty += 27
            card += text(card_x + 24, ty - 5, line, 22, INK, "700", "start")
        for line in dl:
            ty += 21
            card += text(card_x + 24, ty + 1, line, 17, MUTED, "400", "start")
        cy = y + h / 2
        marks.append((cy, stroke, i + 1))
        items.append(card)
        y += h + 30
    line = (f'<line x1="{x_line}" y1="{marks[0][0]:.1f}" x2="{x_line}" y2="{marks[-1][0]:.1f}" '
            f'stroke="{EDGE}" stroke-width="5" stroke-linecap="round"/>') if len(marks) > 1 else ""
    dots = "".join(f'<circle cx="{x_line}" cy="{cy:.1f}" r="20" fill="{c}"/>' + text(x_line, cy + 7, str(n), 20, "#FFFFFF", "700")
                   for cy, c, n in marks)
    return Layout(line + "".join(items) + dots, card_x + card_w, y - 30)


def cycle(spec) -> Layout:
    nodes, n, w = spec.nodes, len(spec.nodes), 210
    info = [measure(nd.label, nd.description, w) for nd in nodes]
    hmax = max(i[0] for i in info)
    radius = max(170, 48 * n)
    cw, ch = 2 * radius + w + 60, 2 * radius + hmax + 60
    cx, cy = cw / 2, ch / 2
    boxes: dict[str, Box] = {}
    for i, nd in enumerate(nodes):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        h = info[i][0]
        boxes[nd.id] = Box(cx + radius * math.cos(ang) - w / 2, cy + radius * math.sin(ang) - h / 2, w, h)
    conns = _connections(spec, sequential=False) or ([(nodes[i].id, nodes[(i + 1) % n].id, "") for i in range(n)] if n > 1 else [])
    body = ""
    for a, b, label in conns:
        if a == b:
            continue
        A, B = boxes[a], boxes[b]
        mx, my = (A.cx + B.cx) / 2, (A.cy + B.cy) / 2
        if math.hypot(mx - cx, my - cy) < 1:  # two nodes: bow the arrows sideways
            dx, dy = B.cx - A.cx, B.cy - A.cy
            length = math.hypot(dx, dy) or 1
            ctrl = (mx - dy / length * 90, my + dx / length * 90)
        else:
            ctrl = (cx + (mx - cx) * 1.35, cy + (my - cy) * 1.35)
        body += curved_edge(A, B, ctrl, label)
    for i, nd in enumerate(nodes):
        body += node_svg(boxes[nd.id], info[i][1], info[i][2], i)
    return Layout(body, cw, ch)


def comparison(spec) -> Layout:
    card_w, gap, per_row = 290, 30, 3
    nodes = spec.nodes
    body, y = "", 0.0
    for start in range(0, len(nodes), per_row):
        row = nodes[start:start + per_row]
        descs = [wrap(n.description, 30, 9) for n in row]
        head_h = 76.0
        card_h = head_h + 28 + 24 * max([len(d) for d in descs] + [1]) + 20
        for j, n in enumerate(row):
            x = j * (card_w + gap)
            stroke, fill = PALETTE[(start + j) % len(PALETTE)]
            body += f'<rect x="{x}" y="{y:.1f}" width="{card_w}" height="{card_h:.1f}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
            body += (f'<path d="M{x},{y + head_h:.1f} V{y + 16:.1f} Q{x},{y:.1f} {x + 16},{y:.1f} H{x + card_w - 16} '
                     f'Q{x + card_w},{y:.1f} {x + card_w},{y + 16:.1f} V{y + head_h:.1f} Z" fill="{stroke}"/>')
            ll = wrap(n.label, 22, 2)
            ty = y + head_h / 2 - 13.5 * (len(ll) - 1) + 8
            for k, line in enumerate(ll):
                body += text(x + card_w / 2, ty + 27 * k, line, 22, "#FFFFFF", "700")
            for k, line in enumerate(descs[j]):
                body += text(x + card_w / 2, y + head_h + 38 + 24 * k, line, 17, INK)
        y += card_h + 30
    per = min(per_row, len(nodes))
    return Layout(body, per * card_w + (per - 1) * gap, y - 30)


def concept_map(spec) -> Layout:
    nodes, n, w = spec.nodes, len(spec.nodes), 210
    info = [measure(nd.label, nd.description, w) for nd in nodes]
    hmax = max(i[0] for i in info)
    rx, ry = 330, 240
    cw, ch = 2 * rx + w + 40, 2 * ry + hmax + 40
    cx, cy = cw / 2, ch / 2
    boxes = {}
    for i, nd in enumerate(nodes):
        h = info[i][0]
        if i == 0:
            boxes[nd.id] = Box(cx - w / 2, cy - h / 2, w, h)
        else:
            ang = -math.pi / 2 + 2 * math.pi * (i - 1) / (n - 1)
            boxes[nd.id] = Box(cx + rx * math.cos(ang) - w / 2, cy + ry * math.sin(ang) - h / 2, w, h)
    conns = _connections(spec, False) or [(nodes[0].id, nd.id, "") for nd in nodes[1:]]
    body = _edges(conns, boxes)
    for i, nd in enumerate(nodes):
        body += node_svg(boxes[nd.id], info[i][1], info[i][2], i, emphasis=(i == 0))
    return Layout(body, cw, ch)


def labeled_diagram(spec) -> Layout:
    nodes = spec.nodes
    col_w, center_w, gap = 230, 300, 120
    cw = 2 * col_w + center_w + 2 * gap
    center = nodes[0]
    parts = nodes[1:]
    left, right = parts[0::2], parts[1::2]
    info = {n.id: measure(n.label, n.description, col_w if n is not center else center_w) for n in nodes}
    row_h = max([info[n.id][0] for n in parts] + [64]) + 40
    ch = max(len(left), len(right), 1) * row_h - 40
    ch = max(ch, info[center.id][0] + 40)
    boxes = {center.id: Box(col_w + gap, (ch - max(info[center.id][0], 150)) / 2, center_w, max(info[center.id][0], 150))}
    for column, x in ((left, 0), (right, col_w + gap + center_w + gap)):
        span = len(column) * row_h - 40
        for k, n in enumerate(column):
            h = info[n.id][0]
            boxes[n.id] = Box(x, (ch - span) / 2 + k * row_h + (row_h - 40 - h) / 2, col_w, h)
    labels = {(c.from_, c.to): c.label for c in spec.connections}
    body = ""
    for n in parts:
        label = labels.get((center.id, n.id)) or labels.get((n.id, center.id), "")
        body += straight_edge(boxes[center.id], boxes[n.id], label, arrow=False)
    for i, n in enumerate(nodes):
        body += node_svg(boxes[n.id], info[n.id][1], info[n.id][2], i, emphasis=(n is center))
    return Layout(body, cw, ch)


def sequence(spec) -> Layout:
    nodes = spec.nodes[:6]
    n = len(nodes)
    col = 260 if n <= 3 else 220
    head_w = col - 40
    info = [measure(nd.label, nd.description, head_w) for nd in nodes]
    head_h = max(i[0] for i in info)
    xs = {nd.id: col / 2 + i * col for i, nd in enumerate(nodes)}
    msgs = [(a, b, l) for a, b, l in _connections(spec, False) if a in xs and b in xs]
    step, top = 80, head_h + 60
    ch = top + max(len(msgs), 1) * step
    body = ""
    for i, nd in enumerate(nodes):
        stroke, _ = PALETTE[i % len(PALETTE)]
        body += f'<line x1="{xs[nd.id]:.1f}" y1="{head_h}" x2="{xs[nd.id]:.1f}" y2="{ch}" stroke="{stroke}" stroke-width="3" stroke-dasharray="8 8"/>'
    for k, (a, b, label) in enumerate(msgs):
        y = top + k * step
        if a == b:
            x = xs[a]
            body += (f'<path d="M{x:.1f},{y - 10} h48 v34 h-48" fill="none" stroke="{EDGE}" stroke-width="3" marker-end="url(#arrow)"/>'
                     + text(x + 58, y + 12, label, 16, INK, "600", "start"))
        else:
            body += (f'<line x1="{xs[a]:.1f}" y1="{y}" x2="{xs[b]:.1f}" y2="{y}" stroke="{EDGE}" stroke-width="3" marker-end="url(#arrow)"/>'
                     + f'<text x="{(xs[a] + xs[b]) / 2:.1f}" y="{y - 12}" font-size="16" font-weight="600" fill="{INK}" text-anchor="middle" '
                       f'stroke="{BG}" stroke-width="6" paint-order="stroke">{esc(label)}</text>')
    for i, nd in enumerate(nodes):
        body += node_svg(Box(xs[nd.id] - head_w / 2, 0, head_w, head_h), info[i][1], info[i][2], i)
    return Layout(body, n * col, ch)


LAYOUTS = {
    "flowchart": layered, "process": process, "architecture": layered, "hierarchy": layered,
    "timeline": timeline, "cycle": cycle, "comparison": comparison, "concept_map": concept_map,
    "sequence": sequence, "labeled_diagram": labeled_diagram,
}


def build_svg(spec) -> str:
    layout = LAYOUTS.get(spec.diagram_type, concept_map)(spec)
    pad = 40
    title_lines, sub_lines = wrap(spec.title, 44, 2), wrap(spec.description, 80, 2)
    width = max(layout.w + 2 * pad, 900)
    y = 36 + 42 * len(title_lines)
    head = "".join(text(pad, 40 + 42 * i, line, 36, INK, "800", "start") for i, line in enumerate(title_lines))
    for line in sub_lines:
        head += text(pad, y, line, 19, MUTED, "400", "start")
        y += 26
    top = y + 30
    height = top + layout.h + pad
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" font-family="{FONT}" '
            f'role="img" aria-label="{esc(spec.title)}">{DEFS}<rect width="100%" height="100%" rx="24" fill="{BG}"/>{head}'
            f'<g transform="translate({(width - layout.w) / 2:.1f},{top:.1f})">{layout.body}</g></svg>')
