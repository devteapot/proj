"""Scripted 15-step app-builder workflow for the hybrid SLOP runtime.

The demo exercises a realistic design session through proposal application,
including linked records, an invalid reference, view deletion, schema export,
snapshot/restore, and consistency checks.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
from typing import Any, Dict, List, TextIO

from prototype import AdminRole, DesignRole, HybridRuntime, Proposal, Role, UserRole


@dataclass(frozen=True)
class WorkflowStep:
    """One named proposal in the scripted workflow."""

    label: str
    proposal: Proposal
    role: Role


def build_workflow() -> List[WorkflowStep]:
    """Return the 15 proposal steps for the app-builder session."""

    return [
        _step("Create Contact entity", DesignRole, [("create_entity", {"name": "Contact"})]),
        _step("Add Contact.name", DesignRole, [("add_field", {"entity": "Contact", "field": "name", "field_type": "text"})]),
        _step("Add Contact.email", DesignRole, [("add_field", {"entity": "Contact", "field": "email", "field_type": "email"})]),
        _step("Create Deal entity", DesignRole, [("create_entity", {"name": "Deal"})]),
        _step("Add Deal.title", DesignRole, [("add_field", {"entity": "Deal", "field": "title", "field_type": "text"})]),
        _step("Add Deal.value", DesignRole, [("add_field", {"entity": "Deal", "field": "value", "field_type": "number"})]),
        _step(
            "Add Deal.contact_ref",
            DesignRole,
            [("add_field", {"entity": "Deal", "field": "contact_ref", "field_type": "entity_ref", "reference": "Contact"})],
        ),
        _step("Create Task entity", DesignRole, [("create_entity", {"name": "Task"})]),
        _step("Add Task.title", DesignRole, [("add_field", {"entity": "Task", "field": "title", "field_type": "text"})]),
        _step("Add Task.done", DesignRole, [("add_field", {"entity": "Task", "field": "done", "field_type": "boolean"})]),
        _step(
            "Add Task.deal_ref",
            DesignRole,
            [("add_field", {"entity": "Task", "field": "deal_ref", "field_type": "entity_ref", "reference": "Deal"})],
        ),
        _step(
            "Create entity views",
            DesignRole,
            [
                ("create_view", {"name": "Contacts", "entity": "Contact", "view_type": "list"}),
                ("create_view", {"name": "Pipeline", "entity": "Deal", "view_type": "table"}),
                ("create_view", {"name": "Tasks", "entity": "Task", "view_type": "detail"}),
            ],
        ),
        _step(
            "Create linked records",
            UserRole,
            [
                (
                    "create_record",
                    {
                        "entity": "Contact",
                        "id": "contact-1",
                        "values": {"name": "Ada Lovelace", "email": "ada@example.com"},
                    },
                ),
                (
                    "create_record",
                    {
                        "entity": "Deal",
                        "id": "deal-1",
                        "values": {"title": "Pilot", "value": 12000, "contact_ref": "contact-1"},
                    },
                ),
                (
                    "create_record",
                    {
                        "entity": "Task",
                        "id": "task-1",
                        "values": {"title": "Send proposal", "done": False, "deal_ref": "deal-1"},
                    },
                ),
            ],
        ),
        _step(
            "Reject missing reference",
            DesignRole,
            [("add_field", {"entity": "Deal", "field": "account_ref", "field_type": "entity_ref", "reference": "Account"})],
        ),
        _step("Delete Tasks view", AdminRole, [("delete_view", {"name": "Tasks"})]),
    ]


def run_demo(stdout: TextIO = sys.stdout) -> HybridRuntime:
    """Execute the workflow and print a concise audit-oriented report."""

    runtime = HybridRuntime()
    accepted = 0
    rejected = 0

    print("Hybrid projection app-builder workflow", file=stdout)
    print("Scripted proposals: 15", file=stdout)
    for index, step in enumerate(build_workflow(), start=1):
        did_accept = runtime.apply(step.proposal, role=step.role)
        if did_accept:
            accepted += 1
            status = "ACCEPTED"
        else:
            rejected += 1
            status = "REJECTED"
        print(f"{index:02d}. {status} {step.label}", file=stdout)
        if not did_accept:
            print(f"    reason: {runtime.state.audit_log[-1]['reason']}", file=stdout)

    schema = runtime.export_json_schema()
    restored = HybridRuntime()
    restored.restore(runtime.snapshot())
    schema_summary = {
        entity: sorted(definition["properties"])
        for entity, definition in sorted(schema["$defs"].items())
    }
    records_summary = {
        entity: [record["id"] for record in records]
        for entity, records in sorted(runtime.state.records.items())
    }

    print("", file=stdout)
    print(f"Accepted proposals: {accepted}", file=stdout)
    print(f"Rejected proposals: {rejected}", file=stdout)
    print(f"Final entities: {', '.join(sorted(runtime.state.entities))}", file=stdout)
    print(f"Final views: {', '.join(sorted(runtime.state.views))}", file=stdout)
    print(f"Records: {json.dumps(records_summary, sort_keys=True)}", file=stdout)
    print(f"Exported schema fields: {json.dumps(schema_summary, sort_keys=True)}", file=stdout)
    print(f"Replay consistency: {runtime.validate_consistency()}", file=stdout)
    print(f"Snapshot restore consistency: {restored.validate_consistency() and restored.state.to_dict() == runtime.state.to_dict()}", file=stdout)

    runtime.schema_validator.validate(runtime.state)
    assert accepted == 14
    assert rejected == 1
    assert runtime.validate_consistency()
    assert restored.validate_consistency()
    assert restored.state.to_dict() == runtime.state.to_dict()
    assert "Tasks" not in runtime.state.views

    print("", file=stdout)
    print("Audit trail:", file=stdout)
    for index, entry in enumerate(runtime.state.audit_log, start=1):
        actions = "+".join(
            operation["action"]
            for operation in entry.get("proposal", {}).get("operations", [])
        )
        print(
            f"{index:02d}. {entry['status']} role={entry['role']} actions={actions}",
            file=stdout,
        )
        if entry["status"] == "rejected":
            print(f"    {entry['reason']}", file=stdout)

    return runtime


def _step(label: str, role: Role, operations: List[tuple[str, Dict[str, Any]]]) -> WorkflowStep:
    return WorkflowStep(
        label=label,
        role=role,
        proposal=Proposal.from_operations("scripted-demo", operations, intent=label),
    )


if __name__ == "__main__":
    run_demo()
