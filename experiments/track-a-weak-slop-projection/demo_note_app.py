"""Second weak SLOP projection demo for notes, tags, and searches."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionInvocation
from prompt_builder import EphemeralTailPromptBuilder
from slop_assembler import SlopAssembler
from slop_tree import Affordance, SlopNode


@dataclass
class Note:
    """A single note with lightweight tag metadata."""

    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)


class NoteApp:
    """Tiny note app used to prove the assembler is domain-generic."""

    def __init__(self) -> None:
        self._notes: list[Note] = []
        self._search_queries: list[str] = []
        self._next_id = 1

    @property
    def notes(self) -> tuple[Note, ...]:
        return tuple(self._notes)

    @property
    def search_queries(self) -> tuple[str, ...]:
        return tuple(self._search_queries)

    def create_note(self, title: str, body: str = "") -> Note:
        note = Note(id=f"note-{self._next_id}", title=title.strip(), body=body.strip())
        if not note.title:
            raise ValueError("note title cannot be empty")
        self._next_id += 1
        self._notes.append(note)
        return note

    def add_tag(self, note_id: str, tag: str) -> Note:
        normalized = tag.strip().lower()
        if not normalized:
            raise ValueError("tag cannot be empty")
        for note in self._notes:
            if note.id == note_id:
                if normalized not in note.tags:
                    note.tags.append(normalized)
                return note
        raise KeyError(f"unknown note: {note_id}")

    def search(self, query: str) -> list[Note]:
        normalized = query.strip().lower()
        if normalized:
            self._search_queries.append(normalized)
        return [
            note
            for note in self._notes
            if normalized in note.title.lower()
            or normalized in note.body.lower()
            or normalized in note.tags
        ]

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"id": note.id, "title": note.title, "body": note.body, "tags": list(note.tags)}
            for note in self._notes
        ]


def to_slop_tree(app: NoteApp) -> SlopNode:
    """Project note app state into the local SLOP tree facade."""
    root = SlopNode(
        id="note-app",
        type="app",
        properties={"label": "Note App", "note_count": len(app.notes)},
        affordances=[
            Affordance("create_note", {"title": "string", "body": "string"}),
            Affordance("search_notes", {"query": "string"}),
        ],
        meta={"summary": "Weak projection from explicit Python note state"},
    )
    notes = SlopNode(
        id="notes",
        type="collection",
        properties={"label": "Notes", "count": len(app.notes)},
        meta={"salience": 1.0},
    )
    root.children.append(notes)
    for note in app.notes:
        notes.children.append(
            SlopNode(
                id=note.id,
                type="note",
                properties={
                    "label": note.title,
                    "body": note.body,
                    "tags": ",".join(note.tags) if note.tags else "none",
                },
                affordances=[Affordance("add_tag", {"note_id": "string", "tag": "string"})],
                meta={"salience": 0.8},
            )
        )
    if app.search_queries:
        root.children.append(
            SlopNode(
                id="recent-searches",
                type="collection",
                properties={"label": "Recent Searches", "queries": ", ".join(app.search_queries)},
            )
        )
    return root


class NoteDemoAdapter:
    """Deterministic selector for the note prompt-tail demo."""

    def choose_action(self, user_text: str, tree: Any) -> ActionInvocation:
        normalized = user_text.strip().lower()
        if normalized.startswith("create "):
            title = user_text.strip()[len("create ") :].strip()
            return ActionInvocation("create_note", {"title": title, "body": ""})
        if normalized.startswith("tag "):
            note = _first_note(tree)
            if note is None:
                raise ValueError("no note is available to tag")
            tag = user_text.strip().split(" ", 1)[1]
            return ActionInvocation("add_tag", {"note_id": note.id, "tag": tag})
        if normalized.startswith("search "):
            return ActionInvocation("search_notes", {"query": user_text.strip()[len("search ") :]})
        raise ValueError(f"note demo cannot choose an action for: {user_text!r}")


def apply_invocation(app: NoteApp, invocation: ActionInvocation) -> None:
    """Apply a model-selected invocation to note app state."""
    if invocation.action == "create_note":
        app.create_note(invocation.params["title"], invocation.params.get("body", ""))
        return
    if invocation.action == "add_tag":
        app.add_tag(invocation.params["note_id"], invocation.params["tag"])
        return
    if invocation.action == "search_notes":
        app.search(invocation.params["query"])
        return
    raise ValueError(f"unknown action: {invocation.action}")


def run_demo() -> list[dict[str, Any]]:
    """Run a prompt-tail loop with note creation, tagging, and search."""
    app = NoteApp()
    assembler = SlopAssembler()
    builder = EphemeralTailPromptBuilder(renderer=assembler)
    model = NoteDemoAdapter()

    for index, user_text in enumerate(["create Track A learnings", "tag architecture", "search architecture"], start=1):
        builder.add_message("user", user_text)
        tree = assembler.assemble(app, to_slop_tree)
        prompt = builder.build_request(None, tree)
        print(f"--- note turn {index} prompt tail ---")
        print(prompt[prompt.index("<slop-state") :])
        invocation = model.choose_action(user_text, tree)
        apply_invocation(app, invocation)
        builder.add_message("assistant", f"invoked {invocation.action} with {invocation.params}")
    return app.snapshot()


def _first_note(tree: Any) -> Any | None:
    nodes = [tree]
    while nodes:
        node = nodes.pop(0)
        if node.type == "note":
            return node
        nodes.extend(getattr(node, "children", None) or [])
    return None


if __name__ == "__main__":
    run_demo()
