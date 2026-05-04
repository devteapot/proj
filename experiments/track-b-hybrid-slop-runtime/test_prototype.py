"""Tests for the Track B schema-enforced hybrid SLOP runtime."""

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("prototype.py")
SPEC = importlib.util.spec_from_file_location("track_b_prototype", MODULE_PATH)
prototype = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prototype
SPEC.loader.exec_module(prototype)


class HybridRuntimeTest(unittest.TestCase):
    def test_valid_proposals_mutate_state(self):
        runtime = prototype.HybridRuntime()
        proposal = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                (
                    "add_field",
                    {"entity": "Contact", "field": "email", "field_type": "email"},
                ),
            ],
        )

        accepted = runtime.apply(proposal)

        self.assertTrue(accepted)
        self.assertIn("Contact", runtime.state.entities)
        self.assertEqual(
            {"name": "email", "type": "email"},
            runtime.state.fields["Contact"]["email"],
        )

    def test_invalid_proposals_are_rejected_without_partial_mutation(self):
        runtime = prototype.HybridRuntime()
        proposal = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                (
                    "add_field",
                    {"entity": "Contact", "field": "payload", "field_type": "script"},
                ),
            ],
        )

        before = runtime.state.to_dict()
        accepted = runtime.apply(proposal)

        self.assertFalse(accepted)
        self.assertEqual(before["entities"], runtime.state.entities)
        self.assertEqual(before["fields"], runtime.state.fields)
        self.assertEqual(before["views"], runtime.state.views)
        self.assertEqual(1, len(runtime.state.audit_log))
        self.assertEqual("rejected", runtime.state.audit_log[0]["status"])
        self.assertIn("unsupported field type", runtime.state.audit_log[0]["reason"])

    def test_unknown_and_destructive_operations_are_rejected(self):
        runtime = prototype.HybridRuntime()
        proposal = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[("delete_entity", {"name": "Contact"})],
        )

        self.assertFalse(runtime.apply(proposal))
        self.assertEqual({}, runtime.state.entities)
        self.assertIn("design role cannot invoke delete_entity", runtime.state.audit_log[0]["reason"])
        self.assertEqual("operation_not_allowed", runtime.state.audit_log[0]["errors"][0]["code"])

    def test_audit_log_records_accepted_and_rejected_proposals(self):
        runtime = prototype.HybridRuntime()
        valid = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[("create_entity", {"name": "Contact"})],
        )
        invalid = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[("create_entity", {"name": "Contact"})],
        )

        self.assertTrue(runtime.apply(valid))
        self.assertFalse(runtime.apply(invalid))

        self.assertEqual(["accepted", "rejected"], [e["status"] for e in runtime.state.audit_log])
        self.assertEqual("create_entity", runtime.state.audit_log[0]["proposal"]["operations"][0]["action"])

    def test_rendered_tree_contains_contextual_affordances(self):
        runtime = prototype.HybridRuntime()
        runtime.apply(
            prototype.Proposal.from_operations(
                proposed_by="mock-model",
                operations=[("create_entity", {"name": "Contact"})],
            )
        )

        tree, text = runtime.render_slop_tree()
        entity_node = tree["children"][0]["children"][0]
        entity_actions = {action["action"] for action in entity_node["affordances"]}

        self.assertIn("create_entity", text)
        self.assertIn("add_field", entity_actions)
        self.assertIn("create_view", entity_actions)
        self.assertIn("[entity] entity:Contact", text)

    def test_final_crm_state_matches_expectations(self):
        runtime = prototype.HybridRuntime()

        self.assertTrue(runtime.apply(prototype.crm_proposal()))

        self.assertEqual(["Contact", "Deal", "Task"], sorted(runtime.state.entities))
        self.assertEqual(
            {"name": "email", "type": "email"},
            runtime.state.fields["Contact"]["email"],
        )
        self.assertEqual(
            {"name": "Contacts", "entity": "Contact", "type": "list"},
            runtime.state.views["Contacts"],
        )
        self.assertEqual(
            {"name": "contact", "type": "entity_ref", "reference": "Contact"},
            runtime.state.fields["Deal"]["contact"],
        )
        self.assertEqual("accepted", runtime.state.audit_log[-1]["status"])

    def test_invalid_cross_reference_returns_structured_errors(self):
        runtime = prototype.HybridRuntime()

        accepted = runtime.apply(prototype.invalid_cross_reference_proposal())

        self.assertFalse(accepted)
        self.assertEqual({}, runtime.state.views)
        self.assertEqual("view_unknown_entity", runtime.state.audit_log[0]["errors"][0]["code"])
        self.assertEqual(
            ["views", "Companies", "entity"],
            runtime.state.audit_log[0]["errors"][0]["path"],
        )

    def test_proposal_size_limit_is_enforced_before_mutation(self):
        runtime = prototype.HybridRuntime(
            limits=prototype.RuntimeLimits(max_operations_per_proposal=1)
        )
        proposal = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                ("create_entity", {"name": "Deal"}),
            ],
        )

        self.assertFalse(runtime.apply(proposal))
        self.assertEqual({}, runtime.state.entities)
        self.assertEqual("proposal_too_large", runtime.state.audit_log[0]["errors"][0]["code"])

    def test_field_and_view_limits_are_schema_enforced(self):
        field_limited = prototype.HybridRuntime(
            limits=prototype.RuntimeLimits(max_fields_per_entity=1)
        )
        too_many_fields = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                ("add_field", {"entity": "Contact", "field": "name", "field_type": "text"}),
                ("add_field", {"entity": "Contact", "field": "email", "field_type": "email"}),
            ],
        )

        self.assertFalse(field_limited.apply(too_many_fields))
        self.assertEqual("too_many_fields", field_limited.state.audit_log[0]["errors"][0]["code"])

        view_limited = prototype.HybridRuntime(
            limits=prototype.RuntimeLimits(max_views_per_entity=1)
        )
        too_many_views = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                ("create_view", {"name": "Contacts", "entity": "Contact", "view_type": "list"}),
                ("create_view", {"name": "Contact Detail", "entity": "Contact", "view_type": "detail"}),
            ],
        )

        self.assertFalse(view_limited.apply(too_many_views))
        self.assertEqual("too_many_views", view_limited.state.audit_log[0]["errors"][0]["code"])

    def test_role_based_affordance_filtering_and_apply(self):
        runtime = prototype.HybridRuntime()
        design_proposal = prototype.Proposal.from_operations(
            proposed_by="mock-model",
            operations=[
                ("create_entity", {"name": "Contact"}),
                ("add_field", {"entity": "Contact", "field": "name", "field_type": "text"}),
            ],
        )

        self.assertFalse(runtime.apply(design_proposal, role=prototype.UserRole))
        self.assertTrue(runtime.apply(design_proposal, role=prototype.DesignRole))

        tree, _ = runtime.render_slop_tree(role=prototype.UserRole)
        root_actions = {action["action"] for action in tree["affordances"]}
        entity_actions = {action["action"] for action in tree["children"][0]["children"][0]["affordances"]}

        self.assertNotIn("create_entity", root_actions)
        self.assertEqual({"create_record"}, entity_actions)

        record_proposal = prototype.Proposal.from_operations(
            proposed_by="user",
            operations=[
                (
                    "create_record",
                    {"entity": "Contact", "id": "contact-1", "values": {"name": "Ada"}},
                ),
            ],
        )

        self.assertTrue(runtime.apply(record_proposal, role=prototype.UserRole))
        self.assertEqual("Ada", runtime.state.records["Contact"][0]["values"]["name"])

    def test_admin_can_delete_entities(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))
        delete = prototype.Proposal.from_operations(
            proposed_by="admin",
            operations=[("delete_entity", {"name": "Task"})],
        )

        self.assertTrue(runtime.apply(delete, role=prototype.AdminRole))
        self.assertNotIn("Task", runtime.state.entities)
        self.assertNotIn("Tasks", runtime.state.views)

    def test_delete_entity_rejects_dangling_record_references(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    proposed_by="user",
                    operations=[
                        (
                            "create_record",
                            {
                                "entity": "Contact",
                                "id": "contact-1",
                                "values": {"name": "Ada", "email": "ada@example.com"},
                            },
                        ),
                        (
                            "create_record",
                            {
                                "entity": "Deal",
                                "id": "deal-1",
                                "values": {
                                    "title": "Pilot",
                                    "value": 1000,
                                    "contact": "contact-1",
                                },
                            },
                        ),
                    ],
                ),
                role=prototype.AdminRole,
            )
        )

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                proposed_by="admin",
                operations=[("delete_entity", {"name": "Contact"})],
            ),
            role=prototype.AdminRole,
        )

        self.assertFalse(accepted)
        error = runtime.state.audit_log[-1]["errors"][0]
        self.assertEqual("dangling_references", error["code"])
        self.assertEqual(
            [{"entity": "Deal", "record_id": "deal-1", "field": "contact", "value": "contact-1"}],
            error["value"],
        )
        self.assertIn("Contact", runtime.state.entities)

    def test_cascade_delete_removes_referencing_fields_records_and_views(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    proposed_by="admin",
                    operations=[
                        (
                            "create_record",
                            {
                                "entity": "Contact",
                                "id": "contact-1",
                                "values": {"name": "Ada", "email": "ada@example.com"},
                            },
                        ),
                        (
                            "create_record",
                            {
                                "entity": "Deal",
                                "id": "deal-1",
                                "values": {
                                    "title": "Pilot",
                                    "value": 1000,
                                    "contact": "contact-1",
                                },
                            },
                        ),
                    ],
                ),
                role=prototype.AdminRole,
            )
        )

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                proposed_by="admin",
                operations=[("delete_entity", {"name": "Contact", "cascade_delete": True})],
            ),
            role=prototype.AdminRole,
        )

        self.assertTrue(accepted)
        self.assertNotIn("Contact", runtime.state.entities)
        self.assertNotIn("Contact", runtime.state.fields)
        self.assertNotIn("Contact", runtime.state.records)
        self.assertNotIn("Contacts", runtime.state.views)
        self.assertNotIn("contact", runtime.state.fields["Deal"])
        self.assertNotIn("contact", runtime.state.records["Deal"][0]["values"])
        self.assertTrue(runtime.validate_consistency())

    def test_event_replay_snapshot_restore_consistency(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))
        self.assertTrue(
            runtime.apply(
                prototype.Proposal.from_operations(
                    proposed_by="user",
                    operations=[
                        (
                            "create_record",
                            {"entity": "Contact", "id": "contact-1", "values": {"name": "Ada"}},
                        )
                    ],
                ),
                role=prototype.UserRole,
            )
        )

        replayed = runtime.replay_events()
        self.assertEqual(runtime.state.entities, replayed.entities)
        self.assertEqual(runtime.state.fields, replayed.fields)
        self.assertEqual(runtime.state.views, replayed.views)
        self.assertEqual(runtime.state.records, replayed.records)
        self.assertTrue(runtime.validate_consistency())

        restored = prototype.HybridRuntime()
        restored.restore(runtime.snapshot())
        self.assertEqual(len(runtime.event_log), len(restored.event_log))
        self.assertTrue(restored.validate_consistency())

    def test_state_diff_reports_added_and_removed_state(self):
        before = prototype.AppBuilderState()
        after = before.clone()
        after.entities["Contact"] = {"name": "Contact"}
        after.fields["Contact"] = {"name": {"name": "name", "type": "text"}}
        after.views["Contacts"] = {"name": "Contacts", "entity": "Contact", "type": "list"}
        after.records["Contact"] = [{"id": "contact-1", "values": {"name": "Ada"}}]

        diff = prototype.compute_state_diff(before, after)

        self.assertEqual({"name": "Contact"}, diff["entities"]["added"]["Contact"])
        self.assertEqual(
            {"name": "name", "type": "text"},
            diff["fields"]["Contact"]["added"]["name"],
        )
        self.assertEqual(
            {"name": "Contacts", "entity": "Contact", "type": "list"},
            diff["views"]["added"]["Contacts"],
        )
        self.assertEqual(
            {"id": "contact-1", "values": {"name": "Ada"}},
            diff["records"]["Contact"]["added"]["contact-1"],
        )
        reverse = prototype.compute_state_diff(after, before)
        self.assertIn("Contact", reverse["entities"]["removed"])

    def test_record_creation_rejects_missing_entity_ref_target_record(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))

        accepted = runtime.apply(
            prototype.Proposal.from_operations(
                proposed_by="user",
                operations=[
                    (
                        "create_record",
                        {
                            "entity": "Deal",
                            "id": "deal-1",
                            "values": {
                                "title": "Pilot",
                                "value": 1000,
                                "contact": "missing-contact",
                            },
                        },
                    )
                ],
            ),
            role=prototype.UserRole,
        )

        self.assertFalse(accepted)
        self.assertEqual("record_reference_not_found", runtime.state.audit_log[-1]["errors"][0]["code"])
        self.assertEqual([], runtime.state.records["Deal"])

    def test_delete_record_validates_entity_ref_fields_before_deletion(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))
        runtime.state.records["Deal"].append(
            {
                "id": "deal-1",
                "values": {"title": "Pilot", "value": 1000, "contact": "missing-contact"},
            }
        )

        with self.assertRaises(prototype.ValidationError) as raised:
            runtime.delete_record("Deal", "deal-1")

        self.assertEqual("record_reference_not_found", raised.exception.to_dicts()[0]["code"])
        self.assertTrue(prototype._record_id_exists(runtime.state.records["Deal"], "deal-1"))

    def test_export_json_schema_contains_entity_definitions(self):
        runtime = prototype.HybridRuntime()
        self.assertTrue(runtime.apply(prototype.crm_proposal()))

        schema = runtime.export_json_schema()

        self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        self.assertEqual("object", schema["$defs"]["Contact"]["type"])
        self.assertEqual("email", schema["$defs"]["Contact"]["properties"]["email"]["format"])
        self.assertEqual(
            "#/$defs/Deal",
            schema["properties"]["Deal"]["items"]["$ref"],
        )


if __name__ == "__main__":
    unittest.main()
