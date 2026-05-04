"""Interactive CLI app-builder for the Track B hybrid SLOP runtime.

The CLI keeps all authoritative state inside ``HybridRuntime`` and turns user
commands into constrained proposals. Invalid proposals are rejected by the same
deterministic validation path used by the prototype tests.
"""

from __future__ import annotations

import json
import shlex
import sys
from typing import Any, Dict, Iterable, List, TextIO

from prototype import (
    AdminRole,
    DesignRole,
    HybridRuntime,
    Proposal,
    SUPPORTED_FIELD_TYPES,
    SUPPORTED_VIEW_TYPES,
    UserRole,
    compute_state_diff,
)


class CommandError(ValueError):
    """Raised when a CLI command cannot be parsed into a proposal."""


class InteractiveBuilder:
    """Small command interpreter for building app state interactively."""

    def __init__(self, runtime: HybridRuntime | None = None) -> None:
        self.runtime = runtime if runtime is not None else HybridRuntime()
        self._initial_state = self.runtime.state.clone()

    def run_command(self, line: str) -> str:
        """Parse and run one command, returning user-facing output text."""

        stripped = line.strip()
        if not stripped:
            return ""
        try:
            parts = shlex.split(stripped)
        except ValueError as exc:
            return f"parse error: {exc}"
        if not parts:
            return ""

        command = parts[0].lower()
        try:
            if command == "show":
                return self.render_tree()
            if command == "history":
                return self.render_history()
            if command == "diff":
                return self.render_diff()
            if command == "export":
                return self.render_schema()
            if command == "help":
                return help_text()
            if command in {"quit", "exit"}:
                return "bye"
            proposal, role = self._proposal_for(parts)
        except CommandError as exc:
            return f"error: {exc}"

        accepted = self.runtime.apply(proposal, role=role)
        if accepted:
            actions = ", ".join(operation.action for operation in proposal.operations)
            return f"accepted: {actions}"

        entry = self.runtime.state.audit_log[-1]
        return f"rejected: {entry['reason']}"

    def render_tree(self) -> str:
        """Return the current SLOP-style text projection."""

        _, text = self.runtime.render_slop_tree(role=AdminRole)
        return text

    def render_history(self, limit: int = 10) -> str:
        """Return the most recent audit entries."""

        entries = self.runtime.state.audit_log[-limit:]
        if not entries:
            return "history: no audit entries"
        lines = []
        start = len(self.runtime.state.audit_log) - len(entries) + 1
        for offset, entry in enumerate(entries):
            actions = ", ".join(
                operation["action"]
                for operation in entry.get("proposal", {}).get("operations", [])
            )
            status = entry.get("status", "unknown")
            role = entry.get("role", "unknown")
            reason = entry.get("reason") or "ok"
            lines.append(f"{start + offset:02d}. {status} role={role} actions={actions} reason={reason}")
        return "\n".join(lines)

    def render_diff(self) -> str:
        """Return a JSON diff from the start of the CLI session to now."""

        diff = compute_state_diff(self._initial_state, self.runtime.state)
        return json.dumps(diff, indent=2, sort_keys=True)

    def render_schema(self) -> str:
        """Return the current exported JSON Schema."""

        return json.dumps(self.runtime.export_json_schema(), indent=2, sort_keys=True)

    def _proposal_for(self, parts: List[str]) -> tuple[Proposal, Any]:
        verb = parts[0].lower()
        if verb == "create" and len(parts) >= 2:
            noun = parts[1].lower()
            if noun == "entity":
                return self._create_entity(parts), DesignRole
            if noun == "view":
                return self._create_view(parts), DesignRole
            if noun == "record":
                return self._create_record(parts), UserRole
        if verb == "add" and len(parts) >= 2 and parts[1].lower() == "field":
            return self._add_field(parts), DesignRole
        if verb == "delete" and len(parts) >= 2:
            noun = parts[1].lower()
            if noun == "view":
                return self._delete_view(parts), AdminRole
            if noun == "entity":
                return self._delete_entity(parts), AdminRole
            if noun == "record":
                return self._delete_record(parts), AdminRole
        raise CommandError(f"unknown command: {' '.join(parts)}")

    def _create_entity(self, parts: List[str]) -> Proposal:
        if len(parts) != 3:
            raise CommandError("usage: create entity NAME")
        return _proposal("cli", [("create_entity", {"name": parts[2]})])

    def _add_field(self, parts: List[str]) -> Proposal:
        if len(parts) != 5:
            raise CommandError("usage: add field ENTITY FIELD TYPE")
        field_type, reference = _parse_field_type(parts[4])
        args: Dict[str, Any] = {
            "entity": parts[2],
            "field": parts[3],
            "field_type": field_type,
        }
        if reference is not None:
            args["reference"] = reference
        return _proposal("cli", [("add_field", args)])

    def _create_view(self, parts: List[str]) -> Proposal:
        if len(parts) != 5:
            raise CommandError("usage: create view NAME ENTITY VIEW_TYPE")
        view_type = parts[4]
        if view_type not in SUPPORTED_VIEW_TYPES:
            raise CommandError(f"unsupported view type: {view_type}")
        return _proposal(
            "cli",
            [("create_view", {"name": parts[2], "entity": parts[3], "view_type": view_type})],
        )

    def _create_record(self, parts: List[str]) -> Proposal:
        if len(parts) < 4:
            raise CommandError("usage: create record ENTITY KEY=VALUE...")
        entity = parts[2]
        record_id: str | None = None
        values: Dict[str, Any] = {}
        field_schemas = self.runtime.state.fields.get(entity, {})
        for token in parts[3:]:
            key, value = _split_assignment(token)
            if key == "id":
                record_id = value
                continue
            field_type = field_schemas.get(key, {}).get("type", "text")
            values[key] = _coerce_value(value, field_type)

        args: Dict[str, Any] = {"entity": entity, "values": values}
        if record_id is not None:
            args["id"] = record_id
        return _proposal("cli", [("create_record", args)])

    def _delete_view(self, parts: List[str]) -> Proposal:
        if len(parts) != 3:
            raise CommandError("usage: delete view NAME")
        return _proposal("cli", [("delete_view", {"name": parts[2]})])

    def _delete_entity(self, parts: List[str]) -> Proposal:
        if len(parts) not in {3, 4}:
            raise CommandError("usage: delete entity NAME [cascade]")
        args: Dict[str, Any] = {"name": parts[2]}
        if len(parts) == 4:
            if parts[3].lower() != "cascade":
                raise CommandError("usage: delete entity NAME [cascade]")
            args["cascade_delete"] = True
        return _proposal("cli", [("delete_entity", args)])

    def _delete_record(self, parts: List[str]) -> Proposal:
        if len(parts) != 4:
            raise CommandError("usage: delete record ENTITY ID")
        return _proposal("cli", [("delete_record", {"entity": parts[2], "id": parts[3]})])


def main(argv: List[str] | None = None, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Run the interactive command loop."""

    _ = argv
    builder = InteractiveBuilder()
    print("Hybrid SLOP interactive app builder", file=stdout)
    print("Type 'help' for commands. Type 'quit' to exit.", file=stdout)
    print(builder.render_tree(), file=stdout)
    while True:
        print("> ", end="", file=stdout, flush=True)
        line = stdin.readline()
        if line == "":
            print(file=stdout)
            return 0
        output = builder.run_command(line)
        if output:
            print(output, file=stdout)
        if output == "bye":
            return 0


def help_text() -> str:
    """Return the command help shown by the CLI."""

    return "\n".join(
        [
            "create entity NAME",
            "add field ENTITY FIELD TYPE",
            "  TYPE: text, email, number, date, boolean, entity_ref:ENTITY",
            "create view NAME ENTITY VIEW_TYPE",
            "  VIEW_TYPE: list, detail, table",
            "create record ENTITY KEY=VALUE...",
            "delete view NAME",
            "delete entity NAME [cascade]",
            "delete record ENTITY ID",
            "show",
            "history",
            "diff",
            "export",
        ]
    )


def _proposal(proposed_by: str, operations: Iterable[tuple[str, Dict[str, Any]]]) -> Proposal:
    return Proposal.from_operations(proposed_by=proposed_by, operations=operations)


def _parse_field_type(raw: str) -> tuple[str, str | None]:
    if raw.startswith("entity_ref:"):
        reference = raw.split(":", 1)[1]
        if not reference:
            raise CommandError("entity_ref fields must include a target entity")
        return "entity_ref", reference
    if raw not in SUPPORTED_FIELD_TYPES:
        raise CommandError(f"unsupported field type: {raw}")
    return raw, None


def _split_assignment(token: str) -> tuple[str, str]:
    if "=" not in token:
        raise CommandError(f"expected KEY=VALUE assignment: {token}")
    key, value = token.split("=", 1)
    if not key:
        raise CommandError(f"expected KEY=VALUE assignment: {token}")
    return key, value


def _coerce_value(raw: str, field_type: str) -> Any:
    if field_type == "number":
        try:
            return int(raw)
        except ValueError:
            try:
                return float(raw)
            except ValueError as exc:
                raise CommandError(f"number field value is invalid: {raw}") from exc
    if field_type == "boolean":
        lowered = raw.lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
        raise CommandError(f"boolean field value is invalid: {raw}")
    return raw


if __name__ == "__main__":
    raise SystemExit(main())
