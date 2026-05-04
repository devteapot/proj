import importlib.util
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from contextlib import redirect_stdout
import unittest


MODULE_PATH = Path(__file__).with_name("prototype.py")
SPEC = importlib.util.spec_from_file_location("track_a_prototype", MODULE_PATH)
prototype = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prototype
SPEC.loader.exec_module(prototype)


class FixedClock:
    def __init__(self) -> None:
        self._ticks = [
            datetime(2026, 4, 30, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 30, 10, 1, 0, tzinfo=timezone.utc),
        ]

    def __call__(self):
        return self._ticks.pop(0)


class WeakSlopProjectionTests(unittest.TestCase):
    def test_current_state_appears_in_prompt_tail(self):
        app = prototype.TodoApp()
        app.create_item("Write projection notes")
        builder = prototype.EphemeralTailPromptBuilder(clock=FixedClock())
        builder.add_message("user", "show my todos")

        prompt = builder.build_request(None, app.to_slop_tree())

        self.assertEqual(prompt.count("<slop-state"), 1)
        self.assertIn('generated_at="2026-04-30T10:00:00+00:00"', prompt)
        self.assertIn("[todo] todo-1: Write projection notes (completed=false)", prompt)

    def test_previous_state_tails_are_not_persisted(self):
        app = prototype.TodoApp()
        builder = prototype.EphemeralTailPromptBuilder(clock=FixedClock())
        builder.add_message("user", "create First")
        first_prompt = builder.build_request(None, app.to_slop_tree())

        app.create_item("First")
        builder.add_message("assistant", "invoked create_item")
        second_prompt = builder.build_request(None, app.to_slop_tree())

        stable_text = "\n".join(
            message["content"] for message in builder.stable_messages
        )
        self.assertIn("item_count=0", first_prompt)
        self.assertIn("item_count=1", second_prompt)
        self.assertNotIn("<slop-state", stable_text)
        self.assertNotIn("</slop-state>", stable_text)
        self.assertEqual(second_prompt.count("<slop-state"), 1)

    def test_affordances_are_visible_next_to_relevant_nodes(self):
        app = prototype.TodoApp()
        app.create_item("Pay invoice")

        rendered = app.to_slop_tree().render_tree()

        self.assertIn(
            "[app] todo-app: Todo App (item_count=1) actions: "
            "{create_item(title: string)}",
            rendered,
        )
        self.assertIn(
            "[todo] todo-1: Pay invoice (completed=false) actions: "
            "{complete_item(id: string)}",
            rendered,
        )

    def test_demo_reaches_expected_final_app_state(self):
        output = io.StringIO()
        with redirect_stdout(output):
            final_state = prototype.run_demo()

        self.assertEqual(
            final_state,
            [
                {
                    "id": "todo-1",
                    "title": "Draft Track A README",
                    "completed": True,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
