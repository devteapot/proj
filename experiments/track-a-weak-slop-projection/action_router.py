"""Action invocation types and concrete dispatch for todo affordances."""

from __future__ import annotations

from dataclasses import dataclass

from state_tree import TodoApp


@dataclass(frozen=True)
class ActionInvocation:
    """A model-selected affordance invocation."""

    action: str
    params: dict[str, str]


def apply_invocation(app: TodoApp, invocation: ActionInvocation) -> None:
    """Apply a model-selected invocation to the explicit todo app state."""
    if invocation.action == "create_item":
        app.create_item(invocation.params["title"])
        return
    if invocation.action == "complete_item":
        app.complete_item(invocation.params["id"])
        return
    raise ValueError(f"unknown action: {invocation.action}")


class ActionRouter:
    """Concrete dispatch layer for SLOP affordance invocations."""

    def __init__(self, app: TodoApp) -> None:
        self._app = app

    def apply(self, invocation: ActionInvocation) -> None:
        """Dispatch an invocation to the owning application object."""
        apply_invocation(self._app, invocation)
