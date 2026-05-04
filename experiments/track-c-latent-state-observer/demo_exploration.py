"""Scripted Track C latent-state observer exploration.

The demo runs a fixed ten-event counter sequence over the 8-byte
``LatentCounterRuntime``, prints a probe timeline, exercises perturbation
resilience, reports event-inference accuracy, and summarizes what changes when
``OpaqueLatentState`` is replaced by actual model-internal snapshots.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from experiment_harness import ProbeTimeline, run_full_experiment
from prototype import (
    EnsembleProbeDecoder,
    LatentCounterRuntime,
    LatentEventTracker,
    PerturbationReport,
    ResilienceTester,
    default_probe_suite,
)


EVENTS: Tuple[str, ...] = (
    "increment",
    "increment",
    "increment",
    "decrement",
    "reset",
    "increment",
    "increment",
    "decrement",
    "increment",
    "reset",
)


def build_timeline(events: Iterable[str]) -> Tuple[ProbeTimeline, List[str]]:
    """Run events once and capture timeline rows plus inferred event labels."""

    runtime = LatentCounterRuntime()
    decoders = tuple(default_probe_suite())
    ensemble = EnsembleProbeDecoder(decoders)
    tracker = LatentEventTracker(runtime, decoders)
    timeline = ProbeTimeline()
    inferred_types: List[str] = []

    for step, event in enumerate(events, start=1):
        transition = tracker.apply(event)
        inferred_types.append(transition.inferred_event_type)
        decoder_results = {decoder.name: runtime.probe(decoder) for decoder in decoders}
        ensemble_result = runtime.probe(ensemble)
        timeline.record(
            step=step,
            event=event,
            decoder_results=decoder_results,
            ensemble_result=ensemble_result,
        )

    return timeline, inferred_types


def print_timeline(timeline: ProbeTimeline, inferred_types: List[str]) -> None:
    """Print one compact row per event step."""

    print("Probe Timeline")
    for entry, inferred_type in zip(timeline.entries, inferred_types):
        values = ", ".join(
            f"{name}={decoder['value']}@{decoder['confidence']:.2f}"
            for name, decoder in entry["decoders"].items()
        )
        print(
            f"  step={entry['step']:02d} event={entry['event']:<9} "
            f"consensus={entry['consensus']:.2f} "
            f"ensemble_conf={entry['ensemble_conf']:.3f} "
            f"inferred={inferred_type} values=[{values}]"
        )
    print()


def print_resilience(reports: List[PerturbationReport]) -> None:
    """Print perturbation sensitivity across the standard probe suite."""

    print("Perturbation Resilience")
    for report in reports:
        changed = sum(
            1 for decoder_report in report.decoder_reports if decoder_report.changed
        )
        print(
            f"  amount={report.amount:<2} kind={report.kind:<14} "
            f"changed_decoders={changed}/4 "
            f"mean_confidence_decay={report.confidence_decay:.3f}"
        )
    print()


def run_demo() -> None:
    """Execute the scripted demo and print a diagnostic report."""

    print("Track C Latent-State Observer Demo")
    print("Runtime: LatentCounterRuntime with an 8-byte OpaqueLatentState")
    print()

    timeline, inferred_types = build_timeline(EVENTS)
    print_timeline(timeline, inferred_types)

    tester = ResilienceTester(default_probe_suite())
    reports = tester.run(LatentCounterRuntime(), events=("increment",), amounts=(1, 7))
    print_resilience(reports)

    result = run_full_experiment(
        EVENTS,
        perturb_every=2,
        perturbation_amounts=(1, 7),
    )

    print("Event Inference")
    print(f"  accuracy={result.event_inference_accuracy:.3f}")
    print()

    print("ExperimentResult Summary")
    print(f"  probe_consistency_over_time={result.probe_consistency_over_time}")
    print(f"  confidence_trajectory={result.confidence_trajectory}")
    print(f"  perturbation_recovery_rate={result.perturbation_recovery_rate:.3f}")
    print(f"  recovery_checks={len(result.recovery_checks)}")
    print(
        "  decoded_changed_after_perturbation="
        f"{sum(1 for check in result.recovery_checks if check.decoded_changed)}"
    )
    print()

    print("Replacing OpaqueLatentState With Real Model Internals")
    print("  The snapshot payload becomes a real KV-cache or activation capture.")
    print("  Perturbations become tensor edits, masking, ablations, or cache swaps.")
    print("  Probe decoders must be trained or validated against held-out tasks.")
    print("  Recovery must restore model-internal tensors, not mock byte arrays.")
    print("  Stronger claims require stable independent probes without a symbolic app store.")


if __name__ == "__main__":
    run_demo()
