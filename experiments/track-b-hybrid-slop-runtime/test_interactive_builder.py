"""Tests for the Track B interactive builder CLI wrapper."""

from __future__ import annotations

from io import StringIO
import json
import unittest

import interactive_builder


class InteractiveBuilderTest(unittest.TestCase):
    """Verify that CLI commands become validated runtime proposals."""

    def test_create_entity_and_add_field_commands_mutate_state(self) -> None:
        builder = interactive_builder.InteractiveBuilder()

        self.assertEqual("accepted: create_entity", builder.run_command("create entity Contact"))
        self.assertEqual("accepted: add_field", builder.run_command("add field Contact email email"))

        self.assertIn("Contact", builder.runtime.state.entities)
        self.assertEqual(
            {"name": "email", "type": "email"},
            builder.runtime.state.fields["Contact"]["email"],
        )
        self.assertEqual(["accepted", "accepted"], [entry["status"] for entry in builder.runtime.state.audit_log])

    def test_entity_ref_field_type_is_parsed(self) -> None:
        builder = interactive_builder.InteractiveBuilder()
        builder.run_command("create entity Contact")
        builder.run_command("create entity Deal")

        output = builder.run_command("add field Deal contact_ref entity_ref:Contact")

        self.assertEqual("accepted: add_field", output)
        self.assertEqual(
            {"name": "contact_ref", "type": "entity_ref", "reference": "Contact"},
            builder.runtime.state.fields["Deal"]["contact_ref"],
        )

    def test_invalid_runtime_proposal_reports_rejection(self) -> None:
        builder = interactive_builder.InteractiveBuilder()

        output = builder.run_command("add field Missing name text")

        self.assertIn("rejected:", output)
        self.assertIn("unknown entity", output)
        self.assertEqual({}, builder.runtime.state.entities)
        self.assertEqual("rejected", builder.runtime.state.audit_log[-1]["status"])

    def test_create_record_coerces_known_field_values(self) -> None:
        builder = interactive_builder.InteractiveBuilder()
        builder.run_command("create entity Contact")
        builder.run_command("add field Contact name text")
        builder.run_command("add field Contact score number")
        builder.run_command("add field Contact active boolean")

        output = builder.run_command("create record Contact id=contact-1 name=Ada score=42 active=true")

        self.assertEqual("accepted: create_record", output)
        record = builder.runtime.state.records["Contact"][0]
        self.assertEqual("contact-1", record["id"])
        self.assertEqual({"name": "Ada", "score": 42, "active": True}, record["values"])

    def test_show_history_diff_and_export_commands_render_state(self) -> None:
        builder = interactive_builder.InteractiveBuilder()
        builder.run_command("create entity Contact")
        builder.run_command("add field Contact email email")
        builder.run_command("create view Contacts Contact list")

        self.assertIn("[entity] entity:Contact", builder.run_command("show"))
        self.assertIn("create_view", builder.run_command("history"))
        diff = json.loads(builder.run_command("diff"))
        self.assertIn("Contact", diff["entities"]["added"])
        schema = json.loads(builder.run_command("export"))
        self.assertEqual("email", schema["$defs"]["Contact"]["properties"]["email"]["format"])

    def test_main_loop_exits_on_quit(self) -> None:
        stdin = StringIO("quit\n")
        stdout = StringIO()

        exit_code = interactive_builder.main(stdin=stdin, stdout=stdout)

        self.assertEqual(0, exit_code)
        self.assertIn("Hybrid SLOP interactive app builder", stdout.getvalue())
        self.assertIn("bye", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
