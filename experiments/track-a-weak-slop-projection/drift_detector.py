"""Deterministic state-drift detection for weak projection experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


EXPECTED = "expected"
UNEXPECTED_ADD = "unexpected_add"
UNEXPECTED_REMOVE = "unexpected_remove"
PROPERTY_SHIFT = "property_shift"


@dataclass(frozen=True)
class DriftEvent:
    """One observed state change between two app snapshots."""

    item_id: str
    classification: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    changed_properties: tuple[str, ...] = ()
    reason: str = ""

    @property
    def is_drift(self) -> bool:
        """Return true when the change did not match inferred user intent."""
        return self.classification != EXPECTED


@dataclass(frozen=True)
class DriftReport:
    """Summary of expected changes and drift events for one turn."""

    events: tuple[DriftEvent, ...]

    @property
    def total_changes(self) -> int:
        """Return all item-level changes seen in the snapshot diff."""
        return len(self.events)

    @property
    def drift_count(self) -> int:
        """Return the count of unexpected state changes."""
        return sum(1 for event in self.events if event.is_drift)

    @property
    def drift_percentage(self) -> float:
        """Return unexpected changes as a percentage of all changes."""
        if not self.events:
            return 0.0
        return self.drift_count / len(self.events) * 100.0

    @property
    def per_item_breakdown(self) -> dict[str, list[str]]:
        """Return classifications grouped by item id."""
        breakdown: dict[str, list[str]] = {}
        for event in self.events:
            breakdown.setdefault(event.item_id, []).append(event.classification)
        return breakdown


@dataclass(frozen=True)
class _ExpectedChange:
    action: str
    title: str | None = None
    item_id: str | None = None


def detect_drift(
    previous_snapshot: Iterable[dict[str, Any]],
    current_snapshot: Iterable[dict[str, Any]],
    user_text: str,
    invocation: Any | None = None,
) -> DriftReport:
    """Compare snapshots and classify changes against inferred user intent.

    Snapshots are JSON-like lists of dictionaries with stable ``id`` fields.
    ``invocation`` is optional context from the selected affordance; the user
    command remains the authority for whether a state movement was intended.
    """
    previous = _index_snapshot(previous_snapshot)
    current = _index_snapshot(current_snapshot)
    expected = _infer_expected_change(user_text, previous.values(), invocation)
    events: list[DriftEvent] = []

    expected_add_consumed = False
    for item_id in sorted(current.keys() - previous.keys()):
        item = current[item_id]
        if (
            expected.action == "add"
            and not expected_add_consumed
            and _matches_title(item, expected.title)
        ):
            expected_add_consumed = True
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=EXPECTED,
                    before=None,
                    after=item,
                    reason="new item matches create/add intent",
                )
            )
        else:
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=UNEXPECTED_ADD,
                    before=None,
                    after=item,
                    reason="item appeared without create/add intent",
                )
            )

    for item_id in sorted(previous.keys() - current.keys()):
        item = previous[item_id]
        if expected.action == "remove" and _matches_target(item, expected):
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=EXPECTED,
                    before=item,
                    after=None,
                    reason="removed item matches remove/delete intent",
                )
            )
        else:
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=UNEXPECTED_REMOVE,
                    before=item,
                    after=None,
                    reason="item disappeared without remove/delete intent",
                )
            )

    for item_id in sorted(previous.keys() & current.keys()):
        before = previous[item_id]
        after = current[item_id]
        changed = tuple(
            key
            for key in sorted(set(before) | set(after))
            if key != "id" and before.get(key) != after.get(key)
        )
        if not changed:
            continue

        expected_properties = _expected_property_changes(before, after, expected)
        expected_changed = tuple(key for key in changed if key in expected_properties)
        unexpected_changed = tuple(key for key in changed if key not in expected_properties)

        if expected_changed:
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=EXPECTED,
                    before=before,
                    after=after,
                    changed_properties=expected_changed,
                    reason="property change matches user intent",
                )
            )
        if unexpected_changed:
            events.append(
                DriftEvent(
                    item_id=item_id,
                    classification=PROPERTY_SHIFT,
                    before=before,
                    after=after,
                    changed_properties=unexpected_changed,
                    reason="property changed without matching user intent",
                )
            )

    return DriftReport(events=tuple(events))


def _index_snapshot(snapshot: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in snapshot:
        item_id = str(item["id"])
        indexed[item_id] = dict(item)
    return indexed


def _infer_expected_change(
    user_text: str,
    previous_items: Iterable[dict[str, Any]],
    invocation: Any | None,
) -> _ExpectedChange:
    normalized = " ".join(user_text.strip().lower().split())
    if not normalized:
        return _ExpectedChange("none")

    invocation_action = str(getattr(invocation, "action", "") or "")
    invocation_params = dict(getattr(invocation, "params", {}) or {})

    if _looks_like_add(normalized):
        return _ExpectedChange(
            "add",
            title=_expected_title(user_text, invocation_action, invocation_params),
        )
    if _looks_like_complete(normalized):
        return _ExpectedChange(
            "complete",
            item_id=_expected_item_id(previous_items, invocation_params),
        )
    if _looks_like_remove(normalized):
        return _ExpectedChange(
            "remove",
            title=_remove_target_text(user_text),
            item_id=_target_id_from_text(normalized),
        )
    return _ExpectedChange("none")


def _looks_like_add(normalized: str) -> bool:
    return (
        normalized.startswith("create ")
        or normalized.startswith("add ")
        or normalized.startswith("new ")
        or normalized.startswith("todo ")
        or normalized.startswith("remind me to ")
    )


def _looks_like_complete(normalized: str) -> bool:
    complete_words = (
        "complete",
        "completed",
        "done",
        "finish",
        "finished",
        "check off",
        "mark off",
    )
    return any(word in normalized for word in complete_words)


def _looks_like_remove(normalized: str) -> bool:
    return (
        normalized.startswith("delete ")
        or normalized.startswith("remove ")
        or normalized.startswith("drop ")
    )


def _expected_title(
    user_text: str,
    invocation_action: str,
    invocation_params: dict[str, Any],
) -> str | None:
    stripped = user_text.strip()
    lowered = stripped.lower()
    prefixes = ("create ", "add ", "new ", "todo ", "remind me to ")
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return stripped[len(prefix) :].strip()
    if invocation_action == "create_item" and invocation_params.get("title"):
        return str(invocation_params["title"]).strip()
    return None


def _expected_item_id(
    previous_items: Iterable[dict[str, Any]],
    invocation_params: dict[str, Any],
) -> str | None:
    if invocation_params.get("id"):
        return str(invocation_params["id"])
    for item in previous_items:
        if not bool(item.get("completed")):
            return str(item["id"])
    return None


def _remove_target_text(user_text: str) -> str | None:
    stripped = user_text.strip()
    lowered = stripped.lower()
    for prefix in ("delete ", "remove ", "drop "):
        if lowered.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def _target_id_from_text(normalized: str) -> str | None:
    for token in normalized.replace(",", " ").split():
        if token.startswith("todo-"):
            return token
    return None


def _matches_title(item: dict[str, Any], expected_title: str | None) -> bool:
    if expected_title is None:
        return True
    item_title = item.get("title", item.get("label"))
    return str(item_title or "").strip().lower() == expected_title.strip().lower()


def _matches_target(item: dict[str, Any], expected: _ExpectedChange) -> bool:
    if expected.item_id and str(item.get("id")) == expected.item_id:
        return True
    return _matches_title(item, expected.title)


def _expected_property_changes(
    before: dict[str, Any],
    after: dict[str, Any],
    expected: _ExpectedChange,
) -> set[str]:
    if expected.action != "complete":
        return set()
    if expected.item_id and str(before.get("id")) != expected.item_id:
        return set()
    if before.get("completed") is False and after.get("completed") is True:
        return {"completed"}
    return set()
