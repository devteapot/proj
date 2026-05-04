# Track B — Hybrid SLOP Runtime Prototype

This experiment demonstrates a hybrid projection loop for an app builder. The
authoritative runtime state is explicit JSON-serializable state plus an audit
log. A model-like proposal can suggest mutations, but those mutations pass
through constrained SLOP-style affordances and deterministic validation before
they are applied.

This is hybrid explicit-state projection. It is not proof that the model is the
app, and it does not test hidden-state persistence, KV-cache state, activation
state, or any other strong neural-runtime claim.

## What It Contains

- `AppBuilderState`: explicit app-builder store with `entities`, `fields`,
  `views`, `records`, and `audit_log`.
- `SlopEvent`: append-only accepted transition event with before/after state
  and a structured state diff.
- `Proposal`: a batch of operations representing what a model would suggest.
- `ProposalValidator`: checks role permissions and proposal size limits before
  candidate state validation.
- `SchemaValidator`: checks entity, field, view, record, and cross-reference
  consistency with structured error payloads.
- `HybridRuntime`: validates proposals on a copied state, then commits the
  whole batch atomically if valid, with replayable accepted events.
- `compute_state_diff()`: reports added, removed, and changed entities, fields,
  views, and records.
- `snapshot()` / `restore()` / `replay_events()` / `validate_consistency()`:
  persist and verify explicit state through the event log.
- `export_json_schema()`: exports the current entity model as a JSON Schema
  document.
- SLOP-style affordances:
  - `create_entity(name)`
  - `add_field(entity, field, field_type)`
  - `create_view(name, entity, view_type)`
  - `create_record(entity, values)`
  - `delete_record(entity, record_id)`
  - admin-only delete operations
- `render_slop_tree()`: renders current explicit state as both a semantic tree
  dictionary and canonical text tree with contextual role-filtered affordances.

## Validation Boundary

The runtime rejects proposal batches when:

- entity names are duplicated;
- field names are duplicated within an entity;
- fields reference missing entities;
- views reference missing entities;
- entity-reference fields point at missing entities;
- records contain entity references to missing records;
- entity deletion would leave records with dangling entity references, unless
  `cascade_delete=True` is supplied;
- field or view types are unsupported;
- operations exceed role permissions;
- proposal batches exceed configured size limits;
- entities exceed configured field or view limits;
- required names are missing or blank.

Validation runs against a deep copy of the current explicit state. Invalid
batches do not partially mutate `entities`, `fields`, `views`, or `records`;
only a rejected audit entry is appended.

Default limits:

- `max_operations_per_proposal`: 50
- `max_fields_per_entity`: 20
- `max_views_per_entity`: 10

Roles:

- `UserRole`: can create data records only.
- `DesignRole`: can create entities, add fields, and create views.
- `AdminRole`: can invoke all affordances, including destructive operations.

## Demo

Run:

```bash
python3 experiments/track-b-hybrid-slop-runtime/prototype.py
```

The demo starts from an empty app, rejects a proposal with an invalid
cross-reference, then accepts a multi-entity CRM proposal:

- entities `Contact`, `Deal`, and `Task`
- typed fields, including cross-entity references
- views `Contacts`, `Pipeline`, and `Tasks`
- linked `Contact` and `Deal` records
- rejection of a non-cascading delete that would leave a dangling reference
- cascading entity delete that removes referencing fields, records, and views
- event replay consistency verification
- JSON Schema export
- full audit trail with accepted and rejected proposals and state diffs

## Tests

Run:

```bash
python3 -m unittest experiments/track-b-hybrid-slop-runtime/test_prototype.py
```

The tests verify valid mutation, atomic rejection, structured validation errors,
limits, role-filtered affordances, admin delete behavior, referential integrity,
cascade deletion, event replay, state diffing, JSON Schema export, audit
logging, contextual affordance rendering, and the final CRM state.
