"""Tests for deterministic weak-projection drift detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionInvocation
from drift_detector import (
    EXPECTED,
    PROPERTY_SHIFT,
    UNEXPECTED_ADD,
    UNEXPECTED_REMOVE,
    detect_drift,
)


class DriftDetectorTests(unittest.TestCase):
    """Verify expected and unexpected snapshot changes."""

    def test_expected_create_has_zero_drift(self) -> None:
        report = detect_drift(
            [],
            [{"id": "todo-1", "title": "Write tests", "completed": False}],
            "create Write tests",
            ActionInvocation("create_item", {"title": "Write tests"}),
        )

        self.assertEqual(report.drift_count, 0)
        self.assertEqual(report.drift_percentage, 0.0)
        self.assertEqual(report.events[0].classification, EXPECTED)

    def test_unexpected_add_is_drift(self) -> None:
        report = detect_drift(
            [],
            [{"id": "todo-1", "title": "Surprise", "completed": False}],
            "complete current todo",
            ActionInvocation("create_item", {"title": "Surprise"}),
        )

        self.assertEqual(report.drift_count, 1)
        self.assertEqual(report.drift_percentage, 100.0)
        self.assertEqual(report.events[0].classification, UNEXPECTED_ADD)

    def test_unexpected_remove_is_drift(self) -> None:
        previous = [{"id": "todo-1", "title": "Keep me", "completed": False}]

        report = detect_drift(previous, [], "complete current todo")

        self.assertEqual(report.drift_count, 1)
        self.assertEqual(report.events[0].classification, UNEXPECTED_REMOVE)

    def test_expected_complete_and_unexpected_title_shift_are_split(self) -> None:
        previous = [{"id": "todo-1", "title": "Draft", "completed": False}]
        current = [{"id": "todo-1", "title": "Renamed", "completed": True}]

        report = detect_drift(
            previous,
            current,
            "complete current todo",
            ActionInvocation("complete_item", {"id": "todo-1"}),
        )

        self.assertEqual(report.total_changes, 2)
        self.assertEqual(report.drift_count, 1)
        self.assertEqual(report.drift_percentage, 50.0)
        self.assertEqual(
            [event.classification for event in report.events],
            [EXPECTED, PROPERTY_SHIFT],
        )
        self.assertEqual(report.per_item_breakdown["todo-1"], [EXPECTED, PROPERTY_SHIFT])


if __name__ == "__main__":
    unittest.main()
