"""Public rendering API: spec -> SVG -> HTML page for the web view."""
from __future__ import annotations

from diagram.svg_renderer import build_svg

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;height:100%;background:#0F1420;overflow:hidden}}
svg{{width:100%;height:100%;display:block}}
.msg{{font:18px 'Segoe UI',Arial,sans-serif;color:#94A3B8;height:100%;display:flex;align-items:center;justify-content:center;
text-align:center;padding:24px;white-space:pre-line;box-sizing:border-box;line-height:1.5}}
</style></head><body>{content}</body></html>"""


def render_svg(spec) -> str:
    return build_svg(spec)


def svg_page(svg: str) -> str:
    return PAGE.format(content=svg)


def message_page(message: str) -> str:
    from diagram.templates import esc
    return PAGE.format(content=f'<div class="msg">{esc(message)}</div>')
