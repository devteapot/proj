"""Tests for the Track C probe experiment suite."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from prototype import (  # noqa: E402
    ChecksumProbeDecoder,
    CounterProbeDecoder,
    CrossDecoderAnalyzer,
    EnsembleProbeDecoder,
    LatentCounterRuntime,
    LatentEventTracker,
    LatentVectorRuntime,
    OpaqueLatentState,
    PrefixProbeDecoder,
    ResilienceTester,
    SlopObserver,
    XORProbeDecoder,
    default_probe_suite,
)


class ProbeSuiteTests(unittest.TestCase):
    """Covers probe comparison, perturbation, and event-tracking behavior."""

    def test_independent_probes_decode_different_signals_after_event(self) -> None:
        runtime = LatentCounterRuntime()
        runtime.apply("increment")
        values = {
            decoder.name: runtime.probe(decoder).candidate_state["value"]
            for decoder in default_probe_suite()
        }

        self.assertEqual(1, values["mock-counter-byte-probe"])
        self.assertEqual(76, values["checksum-mod-256-probe"])
        self.assertEqual(4, values["xor-reduction-probe"])
        self.assertEqual(769, values["prefix-little-endian-probe"])

    def test_ensemble_flags_disagreement_among_member_probes(self) -> None:
        runtime = LatentCounterRuntime()
        runtime.apply("increment")
        ensemble = EnsembleProbeDecoder(default_probe_suite())
        result = runtime.probe(ensemble)

        self.assertFalse(result.candidate_state["ensemble_agreement"])
        self.assertFalse(result.diagnostics["agreement"])
        self.assertEqual(4, len(result.diagnostics["members"]))
        self.assertEqual("mock-counter-byte-probe", result.candidate_state["selected_decoder"])
        self.assertLess(result.confidence, runtime.probe(CounterProbeDecoder()).confidence)

    def test_perturbation_changes_multiple_decoder_outputs(self) -> None:
        runtime = LatentCounterRuntime()
        tester = ResilienceTester(default_probe_suite())
        reports = tester.run(runtime, events=("increment",), amounts=(4,))
        changed_decoders = {
            decoder_report.decoder
            for report in reports
            for decoder_report in report.decoder_reports
            if decoder_report.changed
        }

        self.assertGreaterEqual(len(changed_decoders), 3)
        self.assertIn("checksum-mod-256-probe", changed_decoders)
        self.assertIn("prefix-little-endian-probe", changed_decoders)

    def test_resilience_confidence_decay_uses_actual_probe_outputs(self) -> None:
        runtime = LatentCounterRuntime()
        tester = ResilienceTester(default_probe_suite())
        reports = tester.run(runtime, events=("increment",), amounts=(4,))
        byte_increment = next(report for report in reports if report.kind == "byte_increment")
        counter_report = next(
            report
            for report in byte_increment.decoder_reports
            if report.decoder == "mock-counter-byte-probe"
        )

        self.assertEqual(1, counter_report.baseline_value)
        self.assertEqual(5, counter_report.perturbed_value)
        self.assertEqual(1.0, counter_report.baseline_confidence)
        self.assertEqual(0.0, counter_report.perturbed_confidence)
        self.assertEqual(1.0, counter_report.confidence_decay)

    def test_cross_decoder_analyzer_reports_correlation_and_sensitivity(self) -> None:
        runtime = LatentCounterRuntime()
        tester = ResilienceTester(default_probe_suite())
        reports = tester.run(runtime, events=("increment",), amounts=(1, 4, 8))
        analysis = CrossDecoderAnalyzer().analyze(reports)

        self.assertEqual(6, len(analysis.pairwise_correlations))
        self.assertEqual(4, len(analysis.sensitivities))
        self.assertEqual([1, 4, 8], [agreement.amount for agreement in analysis.agreements])
        self.assertIn("mock-counter-byte-probe", analysis.amount_correlations)
        self.assertTrue(
            all(
                sensitivity.classification in {"stable", "sensitive"}
                for sensitivity in analysis.sensitivities
            )
        )

    def test_vector_runtime_exercises_same_probe_suite(self) -> None:
        runtime = LatentVectorRuntime(seed=7)
        tester = ResilienceTester(default_probe_suite())
        reports = tester.run(runtime, events=("increment", "decrement"), amounts=(2,))
        changed_decoders = {
            decoder_report.decoder
            for report in reports
            for decoder_report in report.decoder_reports
            if decoder_report.changed
        }

        self.assertGreaterEqual(len(reports), 3)
        self.assertGreaterEqual(len(changed_decoders), 2)

    def test_event_tracker_reports_consensus_and_divergence(self) -> None:
        runtime = LatentCounterRuntime()
        tracker = LatentEventTracker(runtime, default_probe_suite())
        runtime.perturb(index=0, amount=255)
        transition = tracker.apply("increment")
        report = tracker.report()

        self.assertFalse(transition.consensus)
        self.assertIn(
            transition.inferred_event_type,
            {"confirmed_increment", "confirmed_decrement", "ambiguous", "uncertain"},
        )
        self.assertEqual(1, report["total_events"])
        self.assertEqual(["increment"], report["divergent_events"])

    def test_observer_tree_marks_every_node_diagnostic(self) -> None:
        runtime = LatentCounterRuntime()
        observer = SlopObserver(EnsembleProbeDecoder(default_probe_suite()))
        tree = observer.project(runtime)

        nodes = [tree, *tree["children"]]
        self.assertTrue(all(node["meta"]["diagnostic"] for node in nodes))
        self.assertTrue(all("confidence" in node["meta"] for node in nodes))
        self.assertTrue(all(node["meta"]["authority"] == "diagnostic_projection" for node in nodes))

    def test_runtime_and_latent_contracts_remain_opaque(self) -> None:
        runtime = LatentCounterRuntime()
        latent = OpaqueLatentState.from_bytes([1, 2, 3, 4])

        for name in ("counter", "counter_value", "todos", "state"):
            self.assertFalse(hasattr(runtime, name))
            self.assertFalse(hasattr(latent, name))

    def test_probe_decoder_constructors_validate_inputs(self) -> None:
        with self.assertRaises(ValueError):
            PrefixProbeDecoder(width=0)
        with self.assertRaises(ValueError):
            EnsembleProbeDecoder([])
        with self.assertRaises(ValueError):
            ResilienceTester([])

    def test_named_probe_decoders_are_available(self) -> None:
        decoders = [CounterProbeDecoder(), ChecksumProbeDecoder(), XORProbeDecoder()]
        self.assertEqual(
            [
                "mock-counter-byte-probe",
                "checksum-mod-256-probe",
                "xor-reduction-probe",
            ],
            [decoder.name for decoder in decoders],
        )


if __name__ == "__main__":
    unittest.main()
