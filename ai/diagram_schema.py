"""Strict diagram specification. The AI returns JSON; we validate it, then render locally."""
from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from core.state import ClassVisionError

DIAGRAM_TYPES = (
    "flowchart", "process", "architecture", "timeline", "cycle",
    "comparison", "hierarchy", "concept_map", "sequence", "labeled_diagram",
)
FALLBACK_TYPE = "concept_map"
MAX_NODES = 12


class DiagramError(ClassVisionError):
    pass


class Node(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)
    id: str
    label: str
    description: str = ""


class Connection(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, populate_by_name=True)
    from_: str = Field(alias="from")
    to: str
    label: str = ""


class DiagramSpec(BaseModel):
    title: str
    diagram_type: str = FALLBACK_TYPE
    description: str = ""
    nodes: list[Node]
    connections: list[Connection] = Field(default_factory=list)

    @field_validator("diagram_type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> str:
        text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
        return text if text in DIAGRAM_TYPES else FALLBACK_TYPE  # unsupported -> concept_map

    @model_validator(mode="after")
    def _clean(self) -> "DiagramSpec":
        self.title = self.title.strip()[:80] or "Diagram"
        self.description = self.description.strip()[:160]
        seen: set[str] = set()
        nodes: list[Node] = []
        for node in self.nodes:
            node.id, node.label = node.id.strip(), node.label.strip()[:40]
            node.description = node.description.strip()[:120]
            if node.id and node.label and node.id not in seen:
                seen.add(node.id)
                nodes.append(node)
        self.nodes = nodes[:MAX_NODES]
        ids = {n.id for n in self.nodes}
        self.connections = [c for c in self.connections if c.from_ in ids and c.to in ids]
        for c in self.connections:
            c.label = c.label.strip()[:30]
        return self


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise DiagramError("The AI response did not contain a diagram.")
    return text[start:end + 1]


def parse_diagram(text: str) -> DiagramSpec:
    """Parse and validate raw model output. Raises DiagramError with a readable message."""
    try:
        data = json.loads(_extract_json(text))
    except json.JSONDecodeError as exc:
        raise DiagramError(f"The AI response was not valid JSON ({exc.msg}).") from exc
    try:
        spec = DiagramSpec.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise DiagramError(f"The AI response did not match the diagram format ({where}: {first['msg']}).") from exc
    if not spec.nodes:
        raise DiagramError("The AI diagram had no usable nodes.")
    return spec
