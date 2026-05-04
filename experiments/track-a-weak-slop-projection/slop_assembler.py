"""SLOP SDK-backed tree assembly for weak projection experiments."""

from __future__ import annotations

import html
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from slop_tree import Affordance as LocalAffordance
from slop_tree import SlopNode, render_tree


SDK_SRC = Path.home() / "dev/slop/packages/python/slop-ai/src"
if SDK_SRC.exists() and str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

try:
    from slop_ai import Affordance as SdkAffordance  # type: ignore  # noqa: E402
    from slop_ai import NodeMeta  # type: ignore  # noqa: E402
    from slop_ai import SlopNode as SdkSlopNode  # type: ignore  # noqa: E402
    from slop_ai import affordances_to_tools, format_tree  # type: ignore  # noqa: E402
except (ImportError, ModuleNotFoundError, TypeError):
    from slop_fallback import SdkSlopNode, affordances_to_tools, format_tree

    SdkAffordance = LocalAffordance
    NodeMeta = None
    _SDK_AVAILABLE = False
else:
    _SDK_AVAILABLE = True


class SlopAssembler:
    """Projection backend that accepts domain state plus a SLOP projection."""

    def assemble(
        self,
        state_source: Any,
        project_fn: Callable[[Any], SlopNode] | None = None,
    ) -> SdkSlopNode:
        """Project arbitrary app state into a renderable SLOP tree."""
        projector = project_fn or getattr(state_source, "to_slop_tree")
        local_tree = projector(state_source) if project_fn else projector()
        if not _SDK_AVAILABLE:
            return local_tree
        return _to_sdk_node(local_tree)

    def render_text(self, tree: SdkSlopNode) -> str:
        """Render a SLOP tree with the SDK canonical formatter when available."""
        if not _SDK_AVAILABLE:
            return render_tree(tree)
        return format_tree(tree)

    def render_tail(
        self,
        tree: SdkSlopNode,
        generated_at: datetime | None = None,
    ) -> str:
        """Render a canonical ephemeral ``<slop-state>`` block."""
        when = generated_at or datetime.now(timezone.utc)
        return (
            f'<slop-state generated_at="{html.escape(when.isoformat(), quote=True)}">\n'
            f"{self.render_text(tree)}\n"
            "</slop-state>"
        )

    def tools_for_tree(self, tree: SdkSlopNode) -> Any:
        """Return OpenAI-compatible tools and SLOP tool-name resolution."""
        return affordances_to_tools(tree)


def _to_sdk_node(node: SlopNode) -> SdkSlopNode:
    return SdkSlopNode(
        id=node.id,
        type=node.type,
        properties=dict(node.properties),
        children=[_to_sdk_node(child) for child in node.children],
        affordances=[_to_sdk_affordance(affordance) for affordance in node.affordances],
        meta=_to_sdk_meta(node.meta),
    )


def _to_sdk_affordance(affordance: LocalAffordance) -> SdkAffordance:
    return SdkAffordance(
        action=affordance.action,
        params={
            "type": "object",
            "properties": {
                name: {"type": param_type}
                for name, param_type in affordance.params.items()
            },
            "required": sorted(affordance.params),
        },
    )


def _to_sdk_meta(meta: dict[str, Any]) -> Any:
    if not meta or NodeMeta is None:
        return None
    allowed = {
        "summary",
        "salience",
        "pinned",
        "changed",
        "focus",
        "urgency",
        "reason",
        "total_children",
        "window",
        "created",
        "updated",
    }
    return NodeMeta(**{key: value for key, value in meta.items() if key in allowed})
