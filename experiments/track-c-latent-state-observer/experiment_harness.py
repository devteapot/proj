"""End-to-end experiment harness for the Track C latent observer.

The harness keeps the same discipline as the prototype: the runtime source of
truth is an ``OpaqueLatentState`` byte payload, and every visible state value is
diagnostic probe output. The metrics produced here are useful for exercising
snapshot, perturbation, restore, and event-inference mechanics before replacing
the opaque mock latent with real model internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from prototype import (
    EnsembleProbeDecoder,
    EventTransition,
    LatentCounterRuntime,
    LatentEventTracker,
    LatentSnapshot,
    ProbeResult,
    default_probe_suite,
)


class ProbeTimeline:
    """Collect per-step decoder values, consensus, and ensemble confidence."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def record(
        self,
        *,
        step: int,
        event: str,
        decoder_results: Mapping[str, ProbeResult],
        ensemble_result: ProbeResult,
    ) -> Dict[str, Any]:
        """Append one timeline row and return the stored dictionary."""

        decoder_values = {
            name: {
                "value": _decoded_value(result),
                "confidence": float(result.confidence),
            }
            for name, result in decoder_results.items()
        }
        entry = {
            "step": int(step),
            "event": event,
            "decoders": decoder_values,
            "consensus": _consensus_score(
                [decoder["value"] for decoder in decoder_values.values()]
            ),
            "ensemble_conf": float(ensemble_result.confidence),
        }
        self.entries.append(entry)
        return entry

    def consistency_over_time(self) -> List[float]:
        """Return the consensus score for every recorded step."""

        return [float(entry["consensus"]) for entry in self.entries]

    def confidence_trajectory(self) -> List[float]:
        """Return the ensemble confidence for every recorded step."""

        return [float(entry["ensemble_conf"]) for entry in self.entries]


@dataclass(frozen=True)
class RecoveryCheck:
    """Result of perturbing and restoring one latent snapshot."""

    baseline_snapshot: LatentSnapshot
    perturbed_snapshot: LatentSnapshot
    recovered: bool
    decoded_changed: bool


@dataclass(frozen=True)
class ExperimentResult:
    """Summary metrics from a complete latent observer experiment run."""

    probe_consistency_over_time: List[float]
    perturbation_recovery_rate: float
    event_inference_accuracy: float
    confidence_trajectory: List[float]
    recovery_checks: List[RecoveryCheck]


def run_full_experiment(
    events: Tuple[str, ...],
    perturb_every: int = 0,
    perturbation_amounts: Tuple[int, ...] = (1, 7),
) -> ExperimentResult:
    """Run events, log probe outputs, and optionally test recovery.

    ``perturb_every`` is step-based and one-indexed: ``2`` perturbs after steps
    2, 4, 6, and so on. A recovery check counts as recovered only when both the
    opaque bytes and the ensemble-decoded value return to the baseline after
    restoring the snapshot.
    """

    if perturb_every < 0:
        raise ValueError("perturb_every must be non-negative")

    decoders = tuple(default_probe_suite())
    runtime = LatentCounterRuntime()
    ensemble = EnsembleProbeDecoder(decoders)
    tracker = LatentEventTracker(runtime, decoders)
    timeline = ProbeTimeline()
    recovery_checks: List[RecoveryCheck] = []
    correct_events = 0

    for step, event in enumerate(events, start=1):
        transition = tracker.apply(event)
        if _event_correctly_inferred(event, transition):
            correct_events += 1

        decoder_results = {decoder.name: runtime.probe(decoder) for decoder in decoders}
        ensemble_result = runtime.probe(ensemble)
        timeline.record(
            step=step,
            event=event,
            decoder_results=decoder_results,
            ensemble_result=ensemble_result,
        )

        if perturb_every > 0 and step % perturb_every == 0:
            recovery_checks.extend(
                _run_recovery_checks(runtime, ensemble, perturbation_amounts)
            )

    return ExperimentResult(
        probe_consistency_over_time=timeline.consistency_over_time(),
        perturbation_recovery_rate=_recovery_rate(recovery_checks),
        event_inference_accuracy=(
            correct_events / len(events) if events else 0.0
        ),
        confidence_trajectory=timeline.confidence_trajectory(),
        recovery_checks=recovery_checks,
    )


def _run_recovery_checks(
    runtime: LatentCounterRuntime,
    ensemble: EnsembleProbeDecoder,
    perturbation_amounts: Sequence[int],
) -> List[RecoveryCheck]:
    checks: List[RecoveryCheck] = []
    baseline_snapshot = runtime.snapshot()
    baseline_value = _decoded_value(runtime.probe(ensemble))

    for amount in perturbation_amounts:
        runtime.perturb(index=0, amount=amount)
        perturbed_snapshot = runtime.snapshot()
        perturbed_value = _decoded_value(runtime.probe(ensemble))
        decoded_changed = perturbed_value != baseline_value

        runtime.restore(baseline_snapshot)
        restored_snapshot = runtime.snapshot()
        restored_value = _decoded_value(runtime.probe(ensemble))
        checks.append(
            RecoveryCheck(
                baseline_snapshot=baseline_snapshot,
                perturbed_snapshot=perturbed_snapshot,
                recovered=(
                    restored_snapshot.payload == baseline_snapshot.payload
                    and restored_value == baseline_value
                ),
                decoded_changed=decoded_changed,
            )
        )

    return checks


def _decoded_value(result: ProbeResult) -> int:
    return int(result.candidate_state.get("value", 0))


def _consensus_score(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    majority_count = max(values.count(value) for value in set(values))
    return majority_count / len(values)


def _event_correctly_inferred(event: str, transition: EventTransition) -> bool:
    if event == "reset":
        return all(value == 0 for value in transition.decoded_after.values())
    expected_motion = {
        "increment": "increment-like",
        "decrement": "decrement-like",
    }.get(event)
    if expected_motion is None:
        return False
    votes = list(transition.inferred_events.values())
    majority_motion = max(set(votes), key=votes.count) if votes else ""
    return majority_motion == expected_motion


def _recovery_rate(checks: Sequence[RecoveryCheck]) -> float:
    if not checks:
        return 0.0
    return sum(1 for check in checks if check.recovered) / len(checks)
