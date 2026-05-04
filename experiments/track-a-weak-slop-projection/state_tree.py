"""Todo domain state and projection into weak SLOP state trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from slop_tree import Affordance, SlopNode


@dataclass
class TodoItem:
    """A single todo item owned by the explicit Python application state."""

    id: str
    title: str
    completed: bool = False


class TodoApp:
    """A tiny todo application used by the weak projection experiment."""

    def __init__(self) -> None:
        self._items: list[TodoItem] = []
        self._next_id = 1

    @property
    def items(self) -> tuple[TodoItem, ...]:
        """Return an immutable view of current todo items."""
        return tuple(self._items)

    def create_item(self, title: str) -> TodoItem:
        """Create a todo item with a stable SLOP-safe id."""
        normalized = title.strip()
        if not normalized:
            raise ValueError("todo title cannot be empty")

        item = TodoItem(id=f"todo-{self._next_id}", title=normalized)
        self._next_id += 1
        self._items.append(item)
        return item

    def complete_item(self, item_id: str) -> TodoItem:
        """Mark an existing todo item as completed."""
        for item in self._items:
            if item.id == item_id:
                item.completed = True
                return item
        raise KeyError(f"unknown todo item: {item_id}")

    def to_slop_tree(self) -> SlopNode:
        """Project explicit app state into the local SLOP tree facade."""
        return to_slop_tree(self)

    def snapshot(self) -> list[dict[str, Any]]:
        """Return a JSON-like state snapshot for tests and demo output."""
        return [
            {"id": item.id, "title": item.title, "completed": item.completed}
            for item in self._items
        ]


def to_slop_tree(app: TodoApp) -> SlopNode:
    """Project the todo app into a SLOP-like tree with contextual affordances."""
    root = SlopNode(
        id="todo-app",
        type="app",
        properties={"label": "Todo App", "item_count": len(app.items)},
        affordances=[
            Affordance("create_item", {"title": "string"}),
        ],
        meta={
            "projection": "weak",
            "state_authority": "explicit-python-object",
        },
    )

    todo_list = SlopNode(
        id="todos",
        type="collection",
        properties={"label": "Todos", "count": len(app.items)},
        meta={"salience": 1.0},
    )
    root.children.append(todo_list)

    for item in app.items:
        affordances = []
        if not item.completed:
            affordances.append(Affordance("complete_item", {"id": "string"}))
        todo_list.children.append(
            SlopNode(
                id=item.id,
                type="todo",
                properties={
                    "label": item.title,
                    "completed": item.completed,
                },
                affordances=affordances,
                meta={"salience": 0.9 if not item.completed else 0.4},
            )
        )
    return root
