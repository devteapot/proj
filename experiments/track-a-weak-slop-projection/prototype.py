"""Weak SLOP projection demo CLI.

The prototype keeps authoritative todo state in ordinary Python objects, then
projects that state into a prompt-visible ephemeral ``<slop-state>`` tail.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionInvocation, ActionRouter, apply_invocation
from model_adapter import DeterministicAdapter, MockModel, ModelAdapter, OpenAIAdapter
from prompt_builder import EphemeralTailPromptBuilder
from slop_assembler import SlopAssembler
from slop_tree import Affordance, SlopNode, _render_value, render_text, render_tree
from state_tree import TodoApp, TodoItem, to_slop_tree


def run_demo(adapter: ModelAdapter | None = None) -> list[dict[str, Any]]:
    """Run the deterministic demo loop and return the final todo snapshot."""
    app = TodoApp()
    assembler = SlopAssembler()
    builder = EphemeralTailPromptBuilder(renderer=assembler)
    model = adapter or DeterministicAdapter()
    router = ActionRouter(app)

    turns = [
        "create Draft Track A README",
        "complete the current todo",
    ]

    for index, user_text in enumerate(turns, start=1):
        builder.add_message("user", user_text)
        tree = assembler.assemble(app, to_slop_tree)
        prompt = builder.build_request(None, tree)
        tail = prompt[prompt.index("<slop-state") :]
        print(f"--- turn {index} prompt tail ---")
        print(tail)

        invocation = model.choose_action(user_text, tree)
        router.apply(invocation)
        builder.add_message(
            "assistant",
            f"invoked {invocation.action} with {invocation.params}",
        )

    final_tree = assembler.assemble(app, to_slop_tree)
    final_prompt = builder.build_request(None, final_tree)
    print("--- final prompt tail ---")
    print(final_prompt[final_prompt.index("<slop-state") :])
    print("--- final state ---")
    for item in app.snapshot():
        print(f"{item['id']}: {item['title']} completed={item['completed']}")
    return app.snapshot()


__all__ = [
    "ActionInvocation",
    "ActionRouter",
    "Affordance",
    "DeterministicAdapter",
    "EphemeralTailPromptBuilder",
    "MockModel",
    "ModelAdapter",
    "OpenAIAdapter",
    "SlopAssembler",
    "SlopNode",
    "TodoApp",
    "TodoItem",
    "_render_value",
    "apply_invocation",
    "render_text",
    "render_tree",
    "run_demo",
    "to_slop_tree",
]


if __name__ == "__main__":
    run_demo()
