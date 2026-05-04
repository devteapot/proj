"""Prompt builder that appends a fresh ephemeral SLOP state tail per request."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

from slop_tree import SlopNode


class TextTreeRenderer(Protocol):
    """Protocol for projection backends that can render a SLOP state tail."""

    def render_tail(self, tree: Any, generated_at: datetime | None = None) -> str:
        """Render a complete ``<slop-state>`` block."""


class EphemeralTailPromptBuilder:
    """Stores stable messages while appending one fresh state tail per request."""

    def __init__(self, clock=None, renderer: TextTreeRenderer | None = None) -> None:
        self._stable_messages: list[dict[str, str]] = []
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._renderer = renderer

    @property
    def stable_messages(self) -> tuple[dict[str, str], ...]:
        """Return stored stable conversation messages without state tails."""
        return tuple(dict(message) for message in self._stable_messages)

    def add_message(self, role: str, content: str) -> None:
        """Append a stable message, rejecting persisted state-tail text."""
        if "<slop-state" in content or "</slop-state>" in content:
            raise ValueError("stable conversation history must not contain state tails")
        self._stable_messages.append({"role": role, "content": content})

    def build_request(
        self,
        messages: Sequence[dict[str, str]] | None,
        tree: Any,
    ) -> str:
        """Render stable messages plus one regenerated state tail."""
        stable = list(messages) if messages is not None else list(self._stable_messages)
        rendered_messages = [
            f"{message['role']}: {message['content']}" for message in stable
        ]
        generated_at = self._clock()
        tail = self._render_tail(tree, generated_at)
        return "\n\n".join(rendered_messages + [tail])

    def _render_tail(self, tree: Any, generated_at: datetime) -> str:
        if self._renderer is not None:
            return self._renderer.render_tail(tree, generated_at)
        if isinstance(tree, SlopNode):
            return (
                f'<slop-state generated_at="{html.escape(generated_at.isoformat(), quote=True)}">\n'
                f"{tree.render_tree()}\n"
                "</slop-state>"
            )
        if hasattr(tree, "render_tree"):
            return (
                f'<slop-state generated_at="{html.escape(generated_at.isoformat(), quote=True)}">\n'
                f"{tree.render_tree()}\n"
                "</slop-state>"
            )
        raise TypeError("tree requires a renderer or render_tree() method")
