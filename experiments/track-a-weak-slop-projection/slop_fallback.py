from __future__ import annotations
from types import SimpleNamespace
from typing import Any
from slop_tree import SlopNode as SdkSlopNode
from slop_tree import render_tree as format_tree

class ToolSet:
    def __init__(self) -> None:
        self.tools: list[dict[str, Any]] = []
        self._resolve_map: dict[str, Any] = {}

    def resolve(self, tool_name: str) -> Any | None:
        return self._resolve_map.get(tool_name)

def affordances_to_tools(node: SdkSlopNode, path: str = "") -> ToolSet:
    tool_set = ToolSet()
    for aff in node.affordances:
        name = f"{node.id.replace('-', '_')}__{aff.action}"
        props = {key: {"type": value} for key, value in aff.params.items()}
        parameters = {"type": "object", "properties": props, "required": sorted(props)}
        function = {"name": name, "description": f"{aff.action} (on {path or '/'})", "parameters": parameters}
        tool_set.tools.append({"type": "function", "function": function})
        tool_set._resolve_map[name] = SimpleNamespace(path=path or "/", action=aff.action)
    for child in node.children:
        child_path = f"{path}/{child.id}" if path else f"/{child.id}"
        child_tools = affordances_to_tools(child, child_path)
        tool_set.tools.extend(child_tools.tools)
        tool_set._resolve_map.update(child_tools._resolve_map)
    return tool_set
