"""Tests for the reusable weak-projection interactive loop."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionInvocation
from interactive_loop import WeakProjectionLoop, choose_default_adapter
from model_adapter import DeterministicAdapter


class WrongCreateAdapter:
    """Adapter that intentionally creates when the user asked to complete."""

    def choose_action(self, user_text, tree):
        return ActionInvocation("create_item", {"title": "Surprise"})


class InteractiveLoopTests(unittest.TestCase):
    """Verify loop state mutation, metrics, and fallback behavior."""

    def test_default_adapter_falls_back_without_api_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            adapter, name = choose_default_adapter()

        self.assertIsInstance(adapter, DeterministicAdapter)
        self.assertEqual(name, "deterministic")

    def test_create_turn_applies_action_and_records_metrics(self) -> None:
        loop = WeakProjectionLoop(
            adapter=DeterministicAdapter(),
            adapter_name="deterministic",
        )

        result = loop.process_turn("create Ship MVP loop")

        self.assertEqual(result.turn_index, 1)
        self.assertEqual(loop.app.snapshot()[0]["title"], "Ship MVP loop")
        self.assertGreater(result.prompt_size, 0)
        self.assertGreater(result.tail_size, 0)
        self.assertEqual(loop.metrics.total_turns, 1)
        self.assertEqual(loop.metrics.accumulated_prompt_size, result.prompt_size)
        self.assertEqual(loop.metrics.drift_events, 0)

    def test_prompt_tail_size_grows_as_state_grows(self) -> None:
        loop = WeakProjectionLoop(
            adapter=DeterministicAdapter(),
            adapter_name="deterministic",
        )

        first = loop.process_turn("create First")
        second = loop.process_turn("create Second")

        self.assertGreater(second.tail_size, first.tail_size)
        self.assertEqual(loop.metrics.prompt_tail_growth, second.tail_size - first.tail_size)

    def test_complete_turn_is_expected_property_change(self) -> None:
        loop = WeakProjectionLoop(
            adapter=DeterministicAdapter(),
            adapter_name="deterministic",
        )
        loop.process_turn("create Finish this")

        result = loop.process_turn("complete current todo")

        self.assertTrue(result.snapshot[0]["completed"])
        self.assertEqual(result.drift_report.drift_count, 0)
        self.assertEqual(result.drift_report.events[0].classification, "expected")

    def test_wrong_model_action_is_counted_as_drift(self) -> None:
        loop = WeakProjectionLoop(
            adapter=WrongCreateAdapter(),
            adapter_name="wrong",
        )

        result = loop.process_turn("complete current todo")

        self.assertEqual(result.drift_report.drift_count, 1)
        self.assertEqual(
            result.drift_report.events[0].classification,
            "unexpected_add",
        )
        self.assertEqual(loop.metrics.drift_events, 1)


if __name__ == "__main__":
    unittest.main()
