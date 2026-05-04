"""End-to-end tests for the refactored weak SLOP projection loop."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionRouter  # noqa: E402
from model_adapter import DeterministicAdapter, OpenAIAdapter  # noqa: E402
from prompt_builder import EphemeralTailPromptBuilder  # noqa: E402
from slop_assembler import SlopAssembler  # noqa: E402
from state_tree import TodoApp, to_slop_tree  # noqa: E402


class EndToEndProjectionTests(unittest.TestCase):
    """Verify state to tree to prompt to action to state update."""

    def test_create_item_full_flow_with_sdk_assembler(self) -> None:
        app = TodoApp()
        assembler = SlopAssembler()
        builder = EphemeralTailPromptBuilder(renderer=assembler)
        adapter = DeterministicAdapter()
        router = ActionRouter(app)

        user_text = "create Ship real model adapter"
        tree = assembler.assemble(app, to_slop_tree)
        prompt = builder.build_request([{"role": "user", "content": user_text}], tree)
        invocation = adapter.choose_action(user_text, tree)
        router.apply(invocation)

        self.assertIn("<slop-state", prompt)
        self.assertIn("[collection] todos: Todos", prompt)
        self.assertEqual(
            app.snapshot(),
            [
                {
                    "id": "todo-1",
                    "title": "Ship real model adapter",
                    "completed": False,
                }
            ],
        )

    def test_complete_item_full_flow_with_sdk_assembler(self) -> None:
        app = TodoApp()
        app.create_item("Wire SLOP assembler")
        assembler = SlopAssembler()
        adapter = DeterministicAdapter()
        router = ActionRouter(app)

        tree = assembler.assemble(app, to_slop_tree)
        rendered = assembler.render_tail(tree)
        invocation = adapter.choose_action("complete the current todo", tree)
        router.apply(invocation)

        self.assertIn("actions: {complete_item(id: string)}", rendered)
        self.assertEqual(app.snapshot()[0]["completed"], True)

    def test_openai_adapter_extracts_chat_completion_tool_calls(self) -> None:
        adapter = OpenAIAdapter(api_key="test-key")

        tool_name, arguments = adapter._extract_tool_call(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "todos__create_item",
                                        "arguments": '{"title": "Write tests"}',
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.assertEqual(tool_name, "todos__create_item")
        self.assertEqual(arguments, {"title": "Write tests"})

    def test_openai_adapter_extracts_responses_tool_calls(self) -> None:
        adapter = OpenAIAdapter(api_key="test-key")

        tool_name, arguments = adapter._extract_tool_call(
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "todo_1__complete_item",
                        "arguments": {"id": "todo-1"},
                    }
                ]
            }
        )

        self.assertEqual(tool_name, "todo_1__complete_item")
        self.assertEqual(arguments, {"id": "todo-1"})


if __name__ == "__main__":
    unittest.main()
