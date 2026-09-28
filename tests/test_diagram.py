import xml.etree.ElementTree as ET

from ai.diagram_schema import DIAGRAM_TYPES, DiagramError, parse_diagram
from diagram.renderer import render_svg

VALID = """{"title": "HTTP Request Flow", "diagram_type": "sequence", "description": "Basic request/response",
 "nodes": [{"id": "browser", "label": "Browser", "description": "Client"},
           {"id": "server", "label": "Web Server", "description": "Processes request"}],
 "connections": [{"from": "browser", "to": "server", "label": "HTTP Request"},
                 {"from": "server", "to": "browser", "label": "HTTP Response"}]}"""


def _spec(kind, n=5, with_conns=True):
    nodes = [{"id": f"n{i}", "label": f"Step {i} <&> label", "description": "Some description text here"} for i in range(n)]
    conns = [{"from": f"n{i}", "to": f"n{(i + 1) % n}", "label": "go"} for i in range(n)] if with_conns else []
    import json
    return parse_diagram(json.dumps({"title": "T & <b>", "diagram_type": kind, "nodes": nodes, "connections": conns}))


def test_valid_json_and_code_fences():
    assert parse_diagram(VALID).diagram_type == "sequence"
    assert len(parse_diagram("```json\n" + VALID + "\n```").connections) == 2


def test_unsupported_type_falls_back():
    assert parse_diagram('{"title":"x","diagram_type":"pie chart","nodes":[{"id":"a","label":"A"}]}').diagram_type == "concept_map"


def test_bad_connections_dropped():
    spec = parse_diagram('{"title":"x","nodes":[{"id":"a","label":"A"}],"connections":[{"from":"a","to":"zzz"}]}')
    assert spec.connections == []


def test_invalid_responses_raise():
    for bad in ("not json at all", '{"title": "x"}', '{"title":"x","nodes":[]}', '{"nodes":[{"id":"a","label":"A"}]}'):
        try:
            parse_diagram(bad)
        except DiagramError:
            continue
        raise AssertionError(f"should have failed: {bad}")


def test_every_diagram_type_renders_valid_svg():
    for kind in DIAGRAM_TYPES:
        for n, conns in ((1, False), (2, True), (5, True), (9, False)):
            svg = render_svg(_spec(kind, n, conns))
            root = ET.fromstring(svg)  # raises if not well-formed XML
            assert root.tag.endswith("svg")
