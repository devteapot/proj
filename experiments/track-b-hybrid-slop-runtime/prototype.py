"""Track B: schema-enforced hybrid explicit-state projection runtime.

This prototype keeps authoritative application state in explicit
Python/JSON-serializable data structures plus an audit log. Model-like proposals
can request SLOP-style affordances, but deterministic proposal, role, and schema
validation decide whether they become state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


FieldSchema = Dict[str, Any]

FIELD_TYPE_SCHEMAS: Dict[str, FieldSchema] = {
    "text": {"type": "string"},
    "email": {"type": "string", "format": "email"},
    "number": {"type": "number"},
    "date": {"type": "string", "format": "date"},
    "boolean": {"type": "boolean"},
    "entity_ref": {"type": "string"},
}
SUPPORTED_FIELD_TYPES = set(FIELD_TYPE_SCHEMAS)
SUPPORTED_VIEW_TYPES = {"list", "detail", "table"}
SUPPORTED_OPERATIONS = {
    "create_entity",
    "add_field",
    "create_view",
    "create_record",
    "delete_entity",
    "delete_field",
    "delete_view",
    "delete_record",
}


@dataclass(frozen=True)
class ValidationIssue:
    """Structured deterministic validation failure."""

    code: str
    message: str
    path: Tuple[str, ...] = ()
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable issue payload."""

        issue = {
            "code": self.code,
            "message": self.message,
            "path": list(self.path),
        }
        if self.value is not None:
            issue["value"] = self.value
        return issue


class ValidationError(Exception):
    """Raised when a proposal cannot be applied deterministically."""

    def __init__(self, issues: Sequence[ValidationIssue] | ValidationIssue | str) -> None:
        if isinstance(issues, str):
            issues = [ValidationIssue("validation_error", issues)]
        elif isinstance(issues, ValidationIssue):
            issues = [issues]
        self.issues = list(issues)
        super().__init__("; ".join(issue.message for issue in self.issues))

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Return all validation issues as structured dictionaries."""

        return [issue.to_dict() for issue in self.issues]


@dataclass(frozen=True)
class RuntimeLimits:
    """Configurable limits for model-like proposal batches."""

    max_operations_per_proposal: int = 50
    max_fields_per_entity: int = 20
    max_views_per_entity: int = 10


@dataclass(frozen=True)
class Role:
    """Role-based affordance filter."""

    name: str
    allowed_actions: frozenset[str]

    def allows(self, action: str) -> bool:
        """Return whether this role may invoke an affordance action."""

        return action in self.allowed_actions


UserRole = Role("user", frozenset({"create_record"}))
DesignRole = Role("design", frozenset({"create_entity", "add_field", "create_view"}))
AdminRole = Role("admin", frozenset(SUPPORTED_OPERATIONS))


@dataclass(frozen=True)
class Operation:
    """One model-like request to invoke a constrained affordance."""

    action: str
    args: Dict[str, Any]


@dataclass(frozen=True)
class Proposal:
    """A batch of operations representing what a model would suggest."""

    proposed_by: str
    operations: Tuple[Operation, ...]
    intent: str = ""

    @classmethod
    def from_operations(
        cls,
        proposed_by: str,
        operations: Iterable[Tuple[str, Dict[str, Any]]],
        intent: str = "",
    ) -> "Proposal":
        return cls(
            proposed_by=proposed_by,
            operations=tuple(Operation(action, dict(args)) for action, args in operations),
            intent=intent,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposed_by": self.proposed_by,
            "intent": self.intent,
            "operations": [
                {"action": operation.action, "args": dict(operation.args)}
                for operation in self.operations
            ],
        }


@dataclass(frozen=True)
class SlopEvent:
    """Append-only record of an accepted state transition."""

    operation: str
    timestamp: str
    proposal: Dict[str, Any]
    before_state: Dict[str, Any] | None
    after_state: Dict[str, Any] | None
    diff: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "timestamp": self.timestamp,
            "proposal": deepcopy(self.proposal),
            "before_state": deepcopy(self.before_state),
            "after_state": deepcopy(self.after_state),
            "diff": deepcopy(self.diff),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SlopEvent":
        return cls(
            operation=str(data["operation"]),
            timestamp=str(data["timestamp"]),
            proposal=deepcopy(data["proposal"]),
            before_state=deepcopy(data.get("before_state")),
            after_state=deepcopy(data.get("after_state")),
            diff=deepcopy(data.get("diff", {})),
        )


@dataclass
class AppBuilderState:
    """Authoritative explicit app-builder state."""

    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fields: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    views: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    records: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def clone(self) -> "AppBuilderState":
        return deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": deepcopy(self.entities),
            "fields": deepcopy(self.fields),
            "views": deepcopy(self.views),
            "records": deepcopy(self.records),
            "audit_log": deepcopy(self.audit_log),
        }


class ProposalValidator:
    """Validate proposal envelope and size constraints before state mutation."""

    def __init__(self, limits: RuntimeLimits | None = None) -> None:
        self.limits = limits if limits is not None else RuntimeLimits()

    def validate(self, proposal: Proposal, role: Role) -> None:
        """Raise if a proposal exceeds limits or contains disallowed actions."""

        issues: List[ValidationIssue] = []
        if len(proposal.operations) > self.limits.max_operations_per_proposal:
            issues.append(
                ValidationIssue(
                    "proposal_too_large",
                    "proposal exceeds max_operations_per_proposal",
                    ("operations",),
                    len(proposal.operations),
                )
            )
        for index, operation in enumerate(proposal.operations):
            path = ("operations", str(index), "action")
            if operation.action not in SUPPORTED_OPERATIONS:
                issues.append(
                    ValidationIssue(
                        "unsupported_operation",
                        f"unknown operation rejected: {operation.action}",
                        path,
                        operation.action,
                    )
                )
            elif not role.allows(operation.action):
                issues.append(
                    ValidationIssue(
                        "operation_not_allowed",
                        f"{role.name} role cannot invoke {operation.action}",
                        path,
                        operation.action,
                    )
                )
        if issues:
            raise ValidationError(issues)


class SchemaValidator:
    """Validate state-level schema, field types, and cross references."""

    def __init__(self, limits: RuntimeLimits | None = None) -> None:
        self.limits = limits if limits is not None else RuntimeLimits()

    def validate(self, state: AppBuilderState) -> None:
        """Raise with structured issues if the state violates the schema."""

        issues: List[ValidationIssue] = []
        self._validate_entities(state, issues)
        self._validate_fields(state, issues)
        self._validate_views(state, issues)
        self._validate_records(state, issues)
        if issues:
            raise ValidationError(issues)

    def _validate_entities(
        self, state: AppBuilderState, issues: List[ValidationIssue]
    ) -> None:
        seen = set()
        for entity_name, entity in state.entities.items():
            if entity_name in seen:
                issues.append(
                    ValidationIssue(
                        "duplicate_entity",
                        f"entity name is duplicated: {entity_name}",
                        ("entities", entity_name),
                        entity_name,
                    )
                )
            seen.add(entity_name)
            if entity.get("name") != entity_name:
                issues.append(
                    ValidationIssue(
                        "entity_name_mismatch",
                        f"entity key/name mismatch: {entity_name}",
                        ("entities", entity_name, "name"),
                        entity.get("name"),
                    )
                )

    def _validate_fields(self, state: AppBuilderState, issues: List[ValidationIssue]) -> None:
        for entity_name, fields in state.fields.items():
            if entity_name not in state.entities:
                issues.append(
                    ValidationIssue(
                        "field_unknown_entity",
                        f"fields reference unknown entity: {entity_name}",
                        ("fields", entity_name),
                        entity_name,
                    )
                )
                continue
            if len(fields) > self.limits.max_fields_per_entity:
                issues.append(
                    ValidationIssue(
                        "too_many_fields",
                        f"{entity_name} exceeds max_fields_per_entity",
                        ("fields", entity_name),
                        len(fields),
                    )
                )
            seen = set()
            for field_name, field_data in fields.items():
                if field_name in seen:
                    issues.append(
                        ValidationIssue(
                            "duplicate_field",
                            f"field name is duplicated on {entity_name}: {field_name}",
                            ("fields", entity_name, field_name),
                            field_name,
                        )
                    )
                seen.add(field_name)
                if field_data.get("name") != field_name:
                    issues.append(
                        ValidationIssue(
                            "field_name_mismatch",
                            f"field key/name mismatch on {entity_name}: {field_name}",
                            ("fields", entity_name, field_name, "name"),
                            field_data.get("name"),
                        )
                    )
                field_type = field_data.get("type")
                if field_type not in FIELD_TYPE_SCHEMAS:
                    issues.append(
                        ValidationIssue(
                            "unsupported_field_type",
                            f"unsupported field type: {field_type}",
                            ("fields", entity_name, field_name, "type"),
                            field_type,
                        )
                    )
                reference = field_data.get("reference")
                if field_type == "entity_ref" and reference not in state.entities:
                    issues.append(
                        ValidationIssue(
                            "unknown_entity_reference",
                            f"{entity_name}.{field_name} references unknown entity: {reference}",
                            ("fields", entity_name, field_name, "reference"),
                            reference,
                        )
                    )

    def _validate_views(self, state: AppBuilderState, issues: List[ValidationIssue]) -> None:
        counts: Dict[str, int] = {}
        for view_name, view in state.views.items():
            entity = view.get("entity")
            counts[entity] = counts.get(entity, 0) + 1
            if view.get("name") != view_name:
                issues.append(
                    ValidationIssue(
                        "view_name_mismatch",
                        f"view key/name mismatch: {view_name}",
                        ("views", view_name, "name"),
                        view.get("name"),
                    )
                )
            if entity not in state.entities:
                issues.append(
                    ValidationIssue(
                        "view_unknown_entity",
                        f"view references unknown entity: {entity}",
                        ("views", view_name, "entity"),
                        entity,
                    )
                )
            if view.get("type") not in SUPPORTED_VIEW_TYPES:
                issues.append(
                    ValidationIssue(
                        "unsupported_view_type",
                        f"unsupported view type: {view.get('type')}",
                        ("views", view_name, "type"),
                        view.get("type"),
                    )
                )
        for entity, count in counts.items():
            if count > self.limits.max_views_per_entity:
                issues.append(
                    ValidationIssue(
                        "too_many_views",
                        f"{entity} exceeds max_views_per_entity",
                        ("views",),
                        count,
                    )
                )

    def _validate_records(self, state: AppBuilderState, issues: List[ValidationIssue]) -> None:
        for entity_name, records in state.records.items():
            if entity_name not in state.entities:
                issues.append(
                    ValidationIssue(
                        "records_unknown_entity",
                        f"records reference unknown entity: {entity_name}",
                        ("records", entity_name),
                        entity_name,
                    )
                )
                continue
            fields = state.fields.get(entity_name, {})
            for index, record in enumerate(records):
                for field_name, value in record.get("values", {}).items():
                    field_data = fields.get(field_name)
                    if field_data is None:
                        issues.append(
                            ValidationIssue(
                                "record_unknown_field",
                                f"record references unknown field: {entity_name}.{field_name}",
                                ("records", entity_name, str(index), "values", field_name),
                                field_name,
                            )
                        )
                        continue
                    if not _value_matches_type(value, field_data["type"]):
                        issues.append(
                            ValidationIssue(
                                "record_field_type_mismatch",
                                f"record value does not match {field_data['type']}: {field_name}",
                                ("records", entity_name, str(index), "values", field_name),
                                value,
                            )
                        )
                    reference = field_data.get("reference")
                    if field_data["type"] == "entity_ref" and reference in state.entities:
                        if not _record_id_exists(state.records.get(reference, []), value):
                            issues.append(
                                ValidationIssue(
                                    "record_reference_not_found",
                                    f"record references missing {reference} record: {value}",
                                    ("records", entity_name, str(index), "values", field_name),
                                    value,
                                )
                            )


class HybridRuntime:
    """Validates and applies model-like proposals to explicit state."""

    def __init__(
        self,
        state: AppBuilderState | None = None,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self.state = state if state is not None else AppBuilderState()
        self.limits = limits if limits is not None else RuntimeLimits()
        self.proposal_validator = ProposalValidator(self.limits)
        self.schema_validator = SchemaValidator(self.limits)
        self._event_log: List[SlopEvent] = []

    def create_entity(self, name: str, target: AppBuilderState | None = None) -> None:
        target_state = target or self.state
        self._require_name(name, "entity name")
        if name in target_state.entities:
            raise ValidationError(
                ValidationIssue(
                    "duplicate_entity",
                    f"entity already exists: {name}",
                    ("entities", name),
                    name,
                )
            )
        target_state.entities[name] = {"name": name}
        target_state.fields[name] = {}
        target_state.records[name] = []

    def add_field(
        self,
        entity: str,
        field: str,
        field_type: str,
        reference: str | None = None,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        self._require_name(entity, "entity")
        self._require_name(field, "field")
        if entity not in target_state.entities:
            raise ValidationError(
                ValidationIssue(
                    "field_unknown_entity",
                    f"field references unknown entity: {entity}",
                    ("fields", entity),
                    entity,
                )
            )
        if field in target_state.fields[entity]:
            raise ValidationError(
                ValidationIssue(
                    "duplicate_field",
                    f"field already exists on {entity}: {field}",
                    ("fields", entity, field),
                    field,
                )
            )
        field_data = {"name": field, "type": field_type}
        if reference is not None:
            field_data["reference"] = reference
        target_state.fields[entity][field] = field_data

    def create_view(
        self,
        name: str,
        entity: str,
        view_type: str,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        self._require_name(name, "view name")
        self._require_name(entity, "entity")
        if name in target_state.views:
            raise ValidationError(
                ValidationIssue(
                    "duplicate_view",
                    f"view already exists: {name}",
                    ("views", name),
                    name,
                )
            )
        target_state.views[name] = {"name": name, "entity": entity, "type": view_type}

    def create_record(
        self,
        entity: str,
        values: Mapping[str, Any],
        record_id: str | None = None,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        self._require_name(entity, "entity")
        if entity not in target_state.entities:
            raise ValidationError(
                ValidationIssue(
                    "records_unknown_entity",
                    f"record references unknown entity: {entity}",
                    ("records", entity),
                    entity,
                )
            )
        if not isinstance(values, Mapping):
            raise ValidationError(
                ValidationIssue(
                    "record_values_invalid",
                    "record values must be an object",
                    ("records", entity),
                    values,
                )
            )
        next_id = record_id or f"{entity.lower()}-{len(target_state.records[entity]) + 1}"
        self._require_name(next_id, "record id")
        if _record_id_exists(target_state.records[entity], next_id):
            raise ValidationError(
                ValidationIssue(
                    "duplicate_record",
                    f"record already exists on {entity}: {next_id}",
                    ("records", entity),
                    next_id,
                )
            )
        target_state.records[entity].append({"id": next_id, "values": dict(values)})

    def delete_entity(
        self,
        name: str,
        cascade_delete: bool = False,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        self._require_name(name, "entity name")
        if name not in target_state.entities:
            raise ValidationError(
                ValidationIssue(
                    "entity_not_found",
                    f"entity does not exist: {name}",
                    ("entities", name),
                    name,
                )
            )
        dangling_records = self._records_referencing_entity(target_state, name)
        if dangling_records and not cascade_delete:
            raise ValidationError(
                ValidationIssue(
                    "dangling_references",
                    f"entity is referenced by records: {name}",
                    ("records",),
                    dangling_records,
                )
            )
        if cascade_delete:
            self._cascade_delete_entity_references(target_state, name)
        del target_state.entities[name]
        target_state.fields.pop(name, None)
        target_state.records.pop(name, None)
        for view_name in [
            view_name for view_name, view in target_state.views.items() if view["entity"] == name
        ]:
            del target_state.views[view_name]

    def delete_field(
        self,
        entity: str,
        field_name: str,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        if entity not in target_state.fields or field_name not in target_state.fields[entity]:
            raise ValidationError(
                ValidationIssue(
                    "field_not_found",
                    f"field does not exist: {entity}.{field_name}",
                    ("fields", entity, field_name),
                    field_name,
                )
            )
        del target_state.fields[entity][field_name]

    def delete_view(self, name: str, target: AppBuilderState | None = None) -> None:
        target_state = target or self.state
        if name not in target_state.views:
            raise ValidationError(
                ValidationIssue("view_not_found", f"view does not exist: {name}", ("views", name), name)
            )
        del target_state.views[name]

    def delete_record(
        self,
        entity: str,
        record_id: str,
        target: AppBuilderState | None = None,
    ) -> None:
        target_state = target or self.state
        records = target_state.records.get(entity)
        if records is None or not _record_id_exists(records, record_id):
            raise ValidationError(
                ValidationIssue(
                    "record_not_found",
                    f"record does not exist: {entity}.{record_id}",
                    ("records", entity),
                    record_id,
                )
            )
        record = next(record for record in records if record["id"] == record_id)
        self._validate_record_entity_refs_for_delete(target_state, entity, record)
        target_state.records[entity] = [record for record in records if record["id"] != record_id]

    def validate(self, proposal: Proposal, role: Role = DesignRole) -> AppBuilderState:
        """Return the post-proposal state if valid, without mutating live state."""

        self.proposal_validator.validate(proposal, role)
        candidate = self.state.clone()
        for operation in proposal.operations:
            self._apply_operation(candidate, operation)
            self.schema_validator.validate(candidate)
        self.schema_validator.validate(candidate)
        return candidate

    def apply(self, proposal: Proposal, role: Role = DesignRole) -> bool:
        """Atomically apply a valid proposal batch and audit accepted/rejected result."""

        before_state = self.state.clone()
        before_dict = before_state.to_dict()
        try:
            candidate = self.validate(proposal, role=role)
        except ValidationError as exc:
            diff = compute_state_diff(before_state, self.state)
            self.state.audit_log.append(
                {
                    "status": "rejected",
                    "reason": str(exc),
                    "errors": exc.to_dicts(),
                    "role": role.name,
                    "proposal": proposal.to_dict(),
                    "diff": diff,
                }
            )
            return False

        after_without_audit = candidate.clone()
        diff = compute_state_diff(before_state, after_without_audit)
        candidate.audit_log.append(
            {
                "status": "accepted",
                "reason": "",
                "errors": [],
                "role": role.name,
                "proposal": proposal.to_dict(),
                "diff": diff,
            }
        )
        after_dict = candidate.to_dict()
        self._event_log.append(
            SlopEvent(
                operation="+".join(operation.action for operation in proposal.operations),
                timestamp=_utc_timestamp(),
                proposal=proposal.to_dict(),
                before_state=before_dict,
                after_state=after_dict,
                diff=diff,
            )
        )
        self.state = candidate
        return True

    @property
    def event_log(self) -> Tuple[SlopEvent, ...]:
        """Return the append-only accepted event log."""

        return tuple(self._event_log)

    def replay_events(self, up_to: int = -1) -> AppBuilderState:
        """Rebuild state by replaying accepted events from the append-only log."""

        replayed = AppBuilderState()
        events = self._event_log if up_to < 0 else self._event_log[:up_to]
        for event in events:
            proposal = _proposal_from_dict(event.proposal)
            before_state = replayed.clone()
            for operation in proposal.operations:
                self._apply_operation(replayed, operation)
                self.schema_validator.validate(replayed)
            self.schema_validator.validate(replayed)
            replayed.audit_log.append(
                {
                    "status": "accepted",
                    "reason": "",
                    "errors": [],
                    "role": event.proposal.get("role", "replay"),
                    "proposal": event.proposal,
                    "diff": compute_state_diff(before_state, replayed),
                }
            )
        return replayed

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of state plus event log."""

        return {
            "state": self.state.to_dict(),
            "event_log": [event.to_dict() for event in self._event_log],
        }

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Restore state plus event log from a snapshot."""

        state_data = snapshot["state"]
        self.state = AppBuilderState(
            entities=deepcopy(state_data.get("entities", {})),
            fields=deepcopy(state_data.get("fields", {})),
            views=deepcopy(state_data.get("views", {})),
            records=deepcopy(state_data.get("records", {})),
            audit_log=deepcopy(state_data.get("audit_log", [])),
        )
        self._event_log = [
            SlopEvent.from_dict(event_data)
            for event_data in snapshot.get("event_log", [])
        ]

    def validate_consistency(self) -> bool:
        """Return whether current state matches replayed accepted events."""

        replayed = self.replay_events()
        return _state_data_without_audit(self.state) == _state_data_without_audit(replayed)

    def export_json_schema(self) -> Dict[str, Any]:
        """Serialize current app state to a JSON Schema document."""

        definitions: Dict[str, Any] = {}
        for entity_name in sorted(self.state.entities):
            properties = {
                "id": {"type": "string"},
            }
            for field_name, field_data in sorted(self.state.fields.get(entity_name, {}).items()):
                field_schema = dict(FIELD_TYPE_SCHEMAS[field_data["type"]])
                if field_data["type"] == "entity_ref":
                    field_schema = {
                        **field_schema,
                        "description": f"Reference to {field_data['reference']}",
                    }
                properties[field_name] = field_schema
            definitions[entity_name] = {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": ["id"],
            }
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.invalid/hybrid-slop-runtime.schema.json",
            "title": "Hybrid SLOP Runtime State",
            "type": "object",
            "$defs": definitions,
            "properties": {
                entity_name: {
                    "type": "array",
                    "items": {"$ref": f"#/$defs/{entity_name}"},
                }
                for entity_name in sorted(self.state.entities)
            },
            "additionalProperties": False,
        }

    def render_slop_tree(self, role: Role = DesignRole) -> Tuple[Dict[str, Any], str]:
        """Project explicit state into a semantic SLOP-style tree and text view."""

        tree = {
            "id": "app-builder",
            "type": "application",
            "properties": {
                "label": "Hybrid App Builder",
                "state_authority": "explicit-json-event-log",
            },
            "affordances": self._filter_affordances(
                [{"action": "create_entity", "args": {"name": "string"}}],
                role,
            ),
            "meta": {
                "summary": "Hybrid explicit-state projection; the model is not the app.",
                "salience": 1.0,
            },
            "children": [
                {
                    "id": "entities",
                    "type": "collection",
                    "properties": {"label": "Entities", "count": len(self.state.entities)},
                    "affordances": self._filter_affordances(
                        [{"action": "create_entity", "args": {"name": "string"}}],
                        role,
                    ),
                    "meta": {"salience": 0.95},
                    "children": [
                        self._entity_node(entity_name, role)
                        for entity_name in sorted(self.state.entities)
                    ],
                },
                {
                    "id": "views",
                    "type": "collection",
                    "properties": {"label": "Views", "count": len(self.state.views)},
                    "affordances": [],
                    "meta": {"salience": 0.75},
                    "children": [
                        self._view_node(view_name, role) for view_name in sorted(self.state.views)
                    ],
                },
                {
                    "id": "audit-log",
                    "type": "log",
                    "properties": {"label": "Audit Log", "entries": len(self.state.audit_log)},
                    "affordances": [],
                    "meta": {"salience": 0.5},
                    "children": [],
                },
            ],
        }
        return tree, render_text_tree(tree)

    def _entity_node(self, entity_name: str, role: Role) -> Dict[str, Any]:
        fields = self.state.fields.get(entity_name, {})
        return {
            "id": f"entity:{entity_name}",
            "type": "entity",
            "properties": {"name": entity_name, "field_count": len(fields)},
            "affordances": self._filter_affordances(
                [
                    {
                        "action": "add_field",
                        "args": {
                            "entity": entity_name,
                            "field": "string",
                            "field_type": sorted(SUPPORTED_FIELD_TYPES),
                            "reference": sorted(self.state.entities),
                        },
                    },
                    {
                        "action": "create_view",
                        "args": {
                            "name": "string",
                            "entity": entity_name,
                            "view_type": sorted(SUPPORTED_VIEW_TYPES),
                        },
                    },
                    {
                        "action": "create_record",
                        "args": {
                            "entity": entity_name,
                            "values": {
                                field_name: field_data["type"]
                                for field_name, field_data in sorted(fields.items())
                            },
                        },
                    },
                    {"action": "delete_entity", "args": {"name": entity_name}},
                ],
                role,
            ),
            "meta": {"salience": 0.9},
            "children": [
                {
                    "id": f"field:{entity_name}.{field_name}",
                    "type": "field",
                    "properties": {
                        "entity": entity_name,
                        "name": field_name,
                        "field_type": field_data["type"],
                    },
                    "affordances": self._filter_affordances(
                        [
                            {
                                "action": "delete_field",
                                "args": {"entity": entity_name, "field_name": field_name},
                            }
                        ],
                        role,
                    ),
                    "meta": {"salience": 0.7},
                    "children": [],
                }
                for field_name, field_data in sorted(fields.items())
            ],
        }

    def _view_node(self, view_name: str, role: Role) -> Dict[str, Any]:
        view = self.state.views[view_name]
        return {
            "id": f"view:{view_name}",
            "type": "view",
            "properties": {
                "name": view_name,
                "entity": view["entity"],
                "view_type": view["type"],
            },
            "affordances": self._filter_affordances(
                [{"action": "delete_view", "args": {"name": view_name}}],
                role,
            ),
            "meta": {"salience": 0.7},
            "children": [],
        }

    def _apply_operation(self, target: AppBuilderState, operation: Operation) -> None:
        if operation.action == "create_entity":
            self.create_entity(operation.args.get("name"), target=target)
        elif operation.action == "add_field":
            self.add_field(
                operation.args.get("entity"),
                operation.args.get("field"),
                operation.args.get("field_type"),
                reference=operation.args.get("reference"),
                target=target,
            )
        elif operation.action == "create_view":
            self.create_view(
                operation.args.get("name"),
                operation.args.get("entity"),
                operation.args.get("view_type"),
                target=target,
            )
        elif operation.action == "create_record":
            self.create_record(
                operation.args.get("entity"),
                operation.args.get("values"),
                record_id=operation.args.get("id"),
                target=target,
            )
        elif operation.action == "delete_entity":
            self.delete_entity(
                operation.args.get("name"),
                cascade_delete=bool(operation.args.get("cascade_delete", False)),
                target=target,
            )
        elif operation.action == "delete_field":
            self.delete_field(
                operation.args.get("entity"),
                operation.args.get("field_name"),
                target=target,
            )
        elif operation.action == "delete_view":
            self.delete_view(operation.args.get("name"), target=target)
        elif operation.action == "delete_record":
            self.delete_record(
                operation.args.get("entity"),
                operation.args.get("id"),
                target=target,
            )

    def _filter_affordances(
        self,
        affordances: Sequence[Dict[str, Any]],
        role: Role,
    ) -> List[Dict[str, Any]]:
        return [
            affordance
            for affordance in affordances
            if role.allows(str(affordance["action"]))
        ]

    def _records_referencing_entity(
        self,
        state: AppBuilderState,
        referenced_entity: str,
    ) -> List[Dict[str, Any]]:
        affected: List[Dict[str, Any]] = []
        for entity_name, fields in state.fields.items():
            for field_name, field_data in fields.items():
                if field_data.get("type") != "entity_ref":
                    continue
                if field_data.get("reference") != referenced_entity:
                    continue
                for record in state.records.get(entity_name, []):
                    if field_name in record.get("values", {}):
                        affected.append(
                            {
                                "entity": entity_name,
                                "record_id": record.get("id"),
                                "field": field_name,
                                "value": record.get("values", {}).get(field_name),
                            }
                        )
        return affected

    def _cascade_delete_entity_references(
        self,
        state: AppBuilderState,
        referenced_entity: str,
    ) -> None:
        for entity_name, fields in list(state.fields.items()):
            for field_name, field_data in list(fields.items()):
                if (
                    field_data.get("type") == "entity_ref"
                    and field_data.get("reference") == referenced_entity
                ):
                    del fields[field_name]
                    for record in state.records.get(entity_name, []):
                        record.get("values", {}).pop(field_name, None)

    def _validate_record_entity_refs_for_delete(
        self,
        state: AppBuilderState,
        entity: str,
        record: Mapping[str, Any],
    ) -> None:
        issues: List[ValidationIssue] = []
        fields = state.fields.get(entity, {})
        for field_name, value in record.get("values", {}).items():
            field_data = fields.get(field_name)
            if field_data is None or field_data.get("type") != "entity_ref":
                continue
            reference = field_data.get("reference")
            if reference not in state.entities:
                issues.append(
                    ValidationIssue(
                        "unknown_entity_reference",
                        f"{entity}.{field_name} references unknown entity: {reference}",
                        ("fields", entity, field_name, "reference"),
                        reference,
                    )
                )
                continue
            if not _record_id_exists(state.records.get(reference, []), value):
                issues.append(
                    ValidationIssue(
                        "record_reference_not_found",
                        f"record references missing {reference} record: {value}",
                        ("records", entity, str(record.get("id")), "values", field_name),
                        value,
                    )
                )
        if issues:
            raise ValidationError(issues)

    @staticmethod
    def _require_name(value: Any, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                ValidationIssue(
                    "invalid_name",
                    f"{label} must be a non-empty string",
                    (),
                    value,
                )
            )


def render_text_tree(node: Dict[str, Any], depth: int = 0) -> str:
    """Render a compact text view of a SLOP-style semantic tree."""

    indent = "  " * depth
    properties = node.get("properties", {})
    label = properties.get("label") or properties.get("name") or node["id"]
    rendered_properties = ", ".join(
        f"{key}={value}" for key, value in properties.items() if key not in {"label", "name"}
    )
    actions = ", ".join(
        affordance["action"] for affordance in node.get("affordances", [])
    )

    suffix_parts = []
    if rendered_properties:
        suffix_parts.append(f"({rendered_properties})")
    if actions:
        suffix_parts.append(f"actions: {{{actions}}}")
    suffix = " " + " ".join(suffix_parts) if suffix_parts else ""

    lines = [f"{indent}[{node['type']}] {node['id']}: {label}{suffix}"]
    for child in node.get("children", []):
        lines.append(render_text_tree(child, depth + 1))
    return "\n".join(lines)


def compute_state_diff(before: AppBuilderState, after: AppBuilderState) -> Dict[str, Any]:
    """Return structured differences between two explicit app states."""

    return {
        "entities": _mapping_diff(before.entities, after.entities),
        "fields": {
            entity: _mapping_diff(
                before.fields.get(entity, {}),
                after.fields.get(entity, {}),
            )
            for entity in sorted(set(before.fields) | set(after.fields))
            if _mapping_diff(before.fields.get(entity, {}), after.fields.get(entity, {}))
        },
        "views": _mapping_diff(before.views, after.views),
        "records": {
            entity: _record_diff(
                before.records.get(entity, []),
                after.records.get(entity, []),
            )
            for entity in sorted(set(before.records) | set(after.records))
            if _record_diff(before.records.get(entity, []), after.records.get(entity, []))
        },
    }


def _mapping_diff(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> Dict[str, Any]:
    added = {
        key: deepcopy(after[key])
        for key in sorted(set(after) - set(before))
    }
    removed = {
        key: deepcopy(before[key])
        for key in sorted(set(before) - set(after))
    }
    changed = {
        key: {"before": deepcopy(before[key]), "after": deepcopy(after[key])}
        for key in sorted(set(before) & set(after))
        if before[key] != after[key]
    }
    diff: Dict[str, Any] = {}
    if added:
        diff["added"] = added
    if removed:
        diff["removed"] = removed
    if changed:
        diff["changed"] = changed
    return diff


def _record_diff(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    before_by_id = {str(record.get("id")): record for record in before}
    after_by_id = {str(record.get("id")): record for record in after}
    return _mapping_diff(before_by_id, after_by_id)


def crm_proposal() -> Proposal:
    """Return a realistic multi-entity CRM proposal."""

    return Proposal.from_operations(
        proposed_by="mock-model",
        intent="Turn an empty app into a small CRM with contacts, deals, and tasks.",
        operations=[
            ("create_entity", {"name": "Contact"}),
            ("add_field", {"entity": "Contact", "field": "name", "field_type": "text"}),
            ("add_field", {"entity": "Contact", "field": "email", "field_type": "email"}),
            ("create_entity", {"name": "Deal"}),
            ("add_field", {"entity": "Deal", "field": "title", "field_type": "text"}),
            ("add_field", {"entity": "Deal", "field": "value", "field_type": "number"}),
            (
                "add_field",
                {
                    "entity": "Deal",
                    "field": "contact",
                    "field_type": "entity_ref",
                    "reference": "Contact",
                },
            ),
            ("create_entity", {"name": "Task"}),
            ("add_field", {"entity": "Task", "field": "title", "field_type": "text"}),
            ("add_field", {"entity": "Task", "field": "due_date", "field_type": "date"}),
            ("add_field", {"entity": "Task", "field": "done", "field_type": "boolean"}),
            (
                "add_field",
                {
                    "entity": "Task",
                    "field": "deal",
                    "field_type": "entity_ref",
                    "reference": "Deal",
                },
            ),
            ("create_view", {"name": "Contacts", "entity": "Contact", "view_type": "list"}),
            ("create_view", {"name": "Pipeline", "entity": "Deal", "view_type": "table"}),
            ("create_view", {"name": "Tasks", "entity": "Task", "view_type": "list"}),
        ],
    )


def invalid_cross_reference_proposal() -> Proposal:
    """Return a proposal with an invalid view cross-reference."""

    return Proposal.from_operations(
        proposed_by="mock-model",
        intent="Create a view for an entity that does not exist.",
        operations=[
            ("create_view", {"name": "Companies", "entity": "Company", "view_type": "list"}),
        ],
    )


def demo() -> AppBuilderState:
    """Run a multi-entity demonstration with accepted and rejected proposals."""

    runtime = HybridRuntime()
    print("Track B hybrid explicit-state projection demo")
    print("Authoritative state: explicit JSON/event log, not model internals.")
    print()

    initial_tree, initial_text = runtime.render_slop_tree(role=DesignRole)
    print("Initial SLOP-style projection:")
    print(initial_text)
    print()

    rejected = invalid_cross_reference_proposal()
    print("Rejected proposal:")
    print(json.dumps(rejected.to_dict(), indent=2, sort_keys=True))
    print(f"Proposal accepted: {runtime.apply(rejected, role=DesignRole)}")
    print(json.dumps(runtime.state.audit_log[-1], indent=2, sort_keys=True))
    print()

    proposal = crm_proposal()
    print("Accepted proposal:")
    print(json.dumps(proposal.to_dict(), indent=2, sort_keys=True))
    print(f"Proposal accepted: {runtime.apply(proposal, role=DesignRole)}")
    print()

    records = Proposal.from_operations(
        proposed_by="user",
        intent="Create a contact and a deal that references it.",
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
    )
    print("Create linked Contact + Deal records:")
    print(f"Proposal accepted: {runtime.apply(records, role=AdminRole)}")
    print()

    blocked_delete = Proposal.from_operations(
        proposed_by="admin",
        intent="Attempt to delete a referenced entity.",
        operations=[("delete_entity", {"name": "Contact"})],
    )
    print("Delete Contact without cascade:")
    print(f"Proposal accepted: {runtime.apply(blocked_delete, role=AdminRole)}")
    print(json.dumps(runtime.state.audit_log[-1], indent=2, sort_keys=True))
    print()

    cascade_delete = Proposal.from_operations(
        proposed_by="admin",
        intent="Cascade delete Contact and fields, records, and views referencing it.",
        operations=[("delete_entity", {"name": "Contact", "cascade_delete": True})],
    )
    print("Delete Contact with cascade:")
    print(f"Proposal accepted: {runtime.apply(cascade_delete, role=AdminRole)}")
    print(f"Replay matches current state: {runtime.validate_consistency()}")
    print(f"Accepted event count: {len(runtime.event_log)}")
    print()

    final_tree, final_text = runtime.render_slop_tree(role=DesignRole)
    print("Final SLOP-style projection:")
    print(final_text)
    print()
    print("JSON Schema export:")
    print(json.dumps(runtime.export_json_schema(), indent=2, sort_keys=True))
    print()
    print("Final explicit state:")
    print(json.dumps(runtime.state.to_dict(), indent=2, sort_keys=True))

    assert initial_tree["id"] == final_tree["id"]
    return runtime.state


def _record_id_exists(records: Sequence[Dict[str, Any]], record_id: Any) -> bool:
    return any(record.get("id") == record_id for record in records)


def _proposal_from_dict(data: Mapping[str, Any]) -> Proposal:
    return Proposal.from_operations(
        proposed_by=str(data.get("proposed_by", "event-log")),
        intent=str(data.get("intent", "")),
        operations=[
            (str(operation["action"]), dict(operation.get("args", {})))
            for operation in data.get("operations", [])
        ],
    )


def _state_data_without_audit(state: AppBuilderState) -> Dict[str, Any]:
    return {
        "entities": deepcopy(state.entities),
        "fields": deepcopy(state.fields),
        "views": deepcopy(state.views),
        "records": deepcopy(state.records),
    }


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value_matches_type(value: Any, field_type: str) -> bool:
    if field_type in {"text", "email", "date", "entity_ref"}:
        return isinstance(value, str)
    if field_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if field_type == "boolean":
        return isinstance(value, bool)
    return False


if __name__ == "__main__":
    demo()
