"""Schema evolution tests for the Track B hybrid SLOP runtime.

These tests exercise realistic app-builder migration patterns: additive schema
changes, rejected duplicate or dangling references, view deletion, cascade
delete, and replay/snapshot consistency after evolution.
"""

from __future__ import annotations

import unittest

import prototype


class SchemaEvolutionTest(unittest.TestCase):
    """Validate schema migration behavior through public runtime proposals."""

    def test_duplicate_field_addition_is_rejected_atomically(self) -> None:
        runtime = prototype.HybridRuntime()
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "designer",
                    [
                        ("create_entity", {"name": "Contact"}),
                        ("add_field", {"entity": "Contact", "field": "email", "field_type": "email"}),
                    ],
                ),
                role=prototype.DesignRole,
            )
        )

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "designer",
                [("add_field", {"entity": "Contact", "field": "email", "field_type": "email"})],
            ),
            role=prototype.DesignRole,
        )

        self.assertFalse(accepted)
        self.assertEqual("duplicate_field", runtime.state.audit_log[-1]["errors"][0]["code"])
        self.assertEqual(["email"], sorted(runtime.state.fields["Contact"]))

    def test_add_field_after_view_and_record_preserves_existing_record(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_with_record(runtime)

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "designer",
                [("add_field", {"entity": "Contact", "field": "email", "field_type": "email"})],
            ),
            role=prototype.DesignRole,
        )

        self.assertTrue(accepted)
        self.assertEqual("Ada", runtime.state.records["Contact"][0]["values"]["name"])
        self.assertEqual({"name": "email", "type": "email"}, runtime.state.fields["Contact"]["email"])
        self.assertTrue(runtime.validate_consistency())

    def test_delete_view_keeps_remaining_state_consistent(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_with_record(runtime)

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "admin",
                [("delete_view", {"name": "Contacts"})],
            ),
            role=prototype.AdminRole,
        )

        self.assertTrue(accepted)
        self.assertNotIn("Contacts", runtime.state.views)
        self.assertIn("Contact", runtime.state.entities)
        self.assertEqual(1, len(runtime.state.records["Contact"]))
        self.assertTrue(runtime.validate_consistency())

    def test_cascade_delete_entity_removes_referencing_record_values(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_deal_with_records(runtime)

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "admin",
                [("delete_entity", {"name": "Contact", "cascade_delete": True})],
            ),
            role=prototype.AdminRole,
        )

        self.assertTrue(accepted)
        self.assertNotIn("Contact", runtime.state.entities)
        self.assertNotIn("Contact", runtime.state.records)
        self.assertNotIn("contact", runtime.state.fields["Deal"])
        self.assertNotIn("contact", runtime.state.records["Deal"][0]["values"])
        self.assertTrue(runtime.validate_consistency())

    def test_delete_field_with_existing_record_values_is_rejected(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_with_record(runtime)

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "admin",
                [("delete_field", {"entity": "Contact", "field_name": "name"})],
            ),
            role=prototype.AdminRole,
        )

        self.assertFalse(accepted)
        self.assertEqual("record_unknown_field", runtime.state.audit_log[-1]["errors"][0]["code"])
        self.assertIn("name", runtime.state.fields["Contact"])
        self.assertEqual("Ada", runtime.state.records["Contact"][0]["values"]["name"])

    def test_non_cascade_delete_referenced_entity_is_rejected(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_deal_with_records(runtime)

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                "admin",
                [("delete_entity", {"name": "Contact"})],
            ),
            role=prototype.AdminRole,
        )

        self.assertFalse(accepted)
        self.assertEqual("dangling_references", runtime.state.audit_log[-1]["errors"][0]["code"])
        self.assertIn("Contact", runtime.state.entities)
        self.assertIn("contact", runtime.state.fields["Deal"])

    def test_snapshot_restore_after_schema_evolution_matches_replay(self) -> None:
        runtime = prototype.HybridRuntime()
        self._build_contact_with_record(runtime)
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "designer",
                    [("add_field", {"entity": "Contact", "field": "last_seen", "field_type": "date"})],
                ),
                role=prototype.DesignRole,
            )
        )

        restored = prototype.HybridRuntime()
        restored.restore(runtime.snapshot())

        self.assertEqual(runtime.state.to_dict(), restored.state.to_dict())
        self.assertEqual(len(runtime.event_log), len(restored.event_log))
        self.assertTrue(restored.validate_consistency())

    def _build_contact_with_record(self, runtime: prototype.HybridRuntime) -> None:
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "designer",
                    [
                        ("create_entity", {"name": "Contact"}),
                        ("add_field", {"entity": "Contact", "field": "name", "field_type": "text"}),
                        ("create_view", {"name": "Contacts", "entity": "Contact", "view_type": "list"}),
                    ],
                ),
                role=prototype.DesignRole,
            )
        )
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "user",
                    [
                        (
                            "create_record",
                            {"entity": "Contact", "id": "contact-1", "values": {"name": "Ada"}},
                        )
                    ],
                ),
                role=prototype.UserRole,
            )
        )

    def _build_contact_deal_with_records(self, runtime: prototype.HybridRuntime) -> None:
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "designer",
                    [
                        ("create_entity", {"name": "Contact"}),
                        ("add_field", {"entity": "Contact", "field": "name", "field_type": "text"}),
                        ("create_entity", {"name": "Deal"}),
                        ("add_field", {"entity": "Deal", "field": "title", "field_type": "text"}),
                        ("add_field", {"entity": "Deal", "field": "contact", "field_type": "entity_ref", "reference": "Contact"}),
                    ],
                ),
                role=prototype.DesignRole,
            )
        )
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    "user",
                    [
                        (
                            "create_record",
                            {"entity": "Contact", "id": "contact-1", "values": {"name": "Ada"}},
                        ),
                        (
                            "create_record",
                            {
                                "entity": "Deal",
                                "id": "deal-1",
                                "values": {"title": "Pilot", "contact": "contact-1"},
                            },
                        ),
                    ],
                ),
                role=prototype.UserRole,
            )
        )


if __name__ == "__main__":
    unittest.main()
