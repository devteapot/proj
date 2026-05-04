"""Compatibility SLOP tree primitives and canonical text rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Affordance:
    """A contextual action attached to a projected state node."""

    action: str
    params: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        """Render the affordance in the compact text-tree action form."""
        if not self.params:
            return self.action
        params = ", ".join(
            f"{name}: {param_type}" for name, param_type in sorted(self.params.items())
        )
        return f"{self.action}({params})"


@dataclass
class SlopNode:
    """A small local representation of the SLOP node schema."""

    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    children: list["SlopNode"] = field(default_factory=list)
    affordances: list[Affordance] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def render_tree(self, indent: int = 0) -> str:
        """Render this node and its children as canonical text."""
        return render_tree(self, indent=indent)


def _render_value(value: object) -> str:
    """Render scalar property values using the prototype's stable spelling."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def render_tree(node: SlopNode, indent: int = 0) -> str:
    """Render a local SLOP tree in the compact text-tree format."""
    prefix = "  " * indent
    label = node.properties.get("label", "")
    pieces = [f"{prefix}[{node.type}] {node.id}:"]
    if label:
        pieces.append(f" {label}")

    rendered_properties = _render_properties(node)
    if rendered_properties:
        pieces.append(f" ({rendered_properties})")

    if node.affordances:
        actions = ", ".join(affordance.render() for affordance in node.affordances)
        pieces.append(f" actions: {{{actions}}}")

    if node.meta:
        meta = ", ".join(
            f"meta.{key}={_render_value(value)}"
            for key, value in sorted(node.meta.items())
        )
        pieces.append(f" ({meta})")

    lines = ["".join(pieces)]
    for child in node.children:
        lines.append(render_tree(child, indent + 1))
    return "\n".join(lines)


def render_text(node: SlopNode) -> str:
    """Render the full tree as text."""
    return render_tree(node)


def _render_properties(node: SlopNode) -> str:
    rendered = []
    for key, value in sorted(node.properties.items()):
        if key == "label":
            continue
        rendered.append(f"{key}={_render_value(value)}")
    return ", ".join(rendered)
