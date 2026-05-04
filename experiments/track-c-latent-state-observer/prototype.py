"""Track C latent-state observer scaffold.

This is a mock harness for a future strong-projection experiment. The
OpaqueLatentState below is an engineering stand-in for an actual open-model
KV-cache or activation snapshot. Decoded observer output is diagnostic and
probed; it is not authoritative explicit runtime state.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Protocol, Sequence, Tuple


ByteTuple = Tuple[int, ...]


@dataclass(frozen=True)
class OpaqueLatentState:
    """Opaque byte-backed latent state.

    The class intentionally stores uninterpreted bytes and exposes byte-level
    snapshot material only. It does not carry symbolic application fields such
    as ``counter`` or ``todos``.
    """

    _payload: ByteTuple

    @classmethod
    def from_bytes(cls, payload: bytes | bytearray | Iterable[int]) -> "OpaqueLatentState":
        values = tuple(int(value) for value in payload)
        if any(value < 0 or value > 255 for value in values):
            raise ValueError("opaque latent bytes must be in the range 0..255")
        return cls(values)

    @classmethod
    def zeroed(cls, width: int = 8) -> "OpaqueLatentState":
        if width <= 0:
            raise ValueError("width must be positive")
        return cls(tuple(0 for _ in range(width)))

    def to_bytes(self) -> bytes:
        return bytes(self._payload)

    def transformed(self, deltas: Iterable[int]) -> "OpaqueLatentState":
        delta_values = tuple(int(delta) for delta in deltas)
        if len(delta_values) != len(self._payload):
            raise ValueError("delta vector must match latent width")
        return OpaqueLatentState(
            tuple((value + delta) % 256 for value, delta in zip(self._payload, delta_values))
        )

    def with_perturbation(self, index: int, amount: int) -> "OpaqueLatentState":
        if index < 0 or index >= len(self._payload):
            raise IndexError("perturbation index is outside latent width")
        values = list(self._payload)
        values[index] = (values[index] + int(amount)) % 256
        return OpaqueLatentState(tuple(values))


@dataclass(frozen=True)
class LatentSnapshot:
    """Copyable snapshot of opaque latent bytes."""

    payload: bytes


@dataclass(frozen=True)
class ProbeResult:
    """Candidate state recovered by a probe decoder."""

    candidate_state: Dict[str, Any]
    confidence: float
    diagnostics: Dict[str, Any]


@dataclass(frozen=True)
class PerturbationCase:
    """A named byte-level perturbation applied to an opaque latent snapshot."""

    kind: str
    amount: int
    latent: OpaqueLatentState


@dataclass(frozen=True)
class DecoderPerturbationReport:
    """Perturbation response for one decoder at one perturbation amount."""

    decoder: str
    baseline_value: int
    perturbed_value: int
    delta: int
    changed: bool
    baseline_confidence: float
    perturbed_confidence: float
    confidence_decay: float


@dataclass(frozen=True)
class PerturbationReport:
    """Full decoder-suite report for a single perturbation case."""

    kind: str
    amount: int
    decoder_reports: List[DecoderPerturbationReport]
    confidence_decay: float


@dataclass(frozen=True)
class PairwiseCorrelation:
    """Correlation between two decoder output series."""

    left: str
    right: str
    correlation: float


@dataclass(frozen=True)
class DecoderSensitivity:
    """Variance summary for one decoder across perturbation reports."""

    decoder: str
    variance: float
    classification: str


@dataclass(frozen=True)
class PerturbationAgreement:
    """Cross-decoder agreement at one perturbation amount."""

    amount: int
    agreed_decoders: List[str]
    disagreed_decoders: List[str]
    agreement_ratio: float


@dataclass(frozen=True)
class CrossDecoderReport:
    """Correlation and stability summary across decoder perturbation outputs."""

    pairwise_correlations: List[PairwiseCorrelation]
    sensitivities: List[DecoderSensitivity]
    agreements: List[PerturbationAgreement]
    amount_correlations: Dict[str, float]


@dataclass(frozen=True)
class EventTransition:
    """Decoded before/after values for one latent runtime event."""

    event: str
    decoded_before: Dict[str, int]
    decoded_after: Dict[str, int]
    inferred_events: Dict[str, str]
    inferred_event_type: str
    consensus: bool


class LatentRuntime(Protocol):
    """Runtime API consumed by probe harness utilities."""

    def apply(self, event: str) -> None:
        """Apply one deterministic latent event."""

    def snapshot(self) -> LatentSnapshot:
        """Return a copyable latent snapshot."""

    def restore(self, snapshot: LatentSnapshot) -> None:
        """Restore a previous latent snapshot."""

    def perturb(self, index: int = 0, amount: int = 1) -> None:
        """Apply a byte-level perturbation."""

    def probe(self, decoder: ProbeDecoder) -> ProbeResult:
        """Decode the current latent with one probe."""


class ProbeDecoder(Protocol):
    """Interface for decoders that recover candidate app state from latents."""

    name: str

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        """Return a diagnostic candidate state inferred from opaque latent bytes."""


class CounterProbeDecoder:
    """Toy probe that maps latent bytes to a counter candidate.

    This decoder exists only to test harness mechanics. It should eventually be
    replaced with probes over real model internals.
    """

    name = "mock-counter-byte-probe"

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        payload = latent.to_bytes()
        checksum = sum(payload) % 256
        signal = payload[0] if payload else 0
        return ProbeResult(
            candidate_state={"kind": "counter", "value": signal},
            confidence=0.72 if len(payload) >= 4 else 0.4,
            diagnostics={
                "decoder": self.name,
                "latent_width": len(payload),
                "checksum_mod_256": checksum,
                "source": "opaque mock latent bytes",
                "authority": "diagnostic_probe_only",
            },
        )


class ChecksumProbeDecoder:
    """Probe that recovers a counter candidate from ``sum(payload) % 256``."""

    name = "checksum-mod-256-probe"

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        payload = latent.to_bytes()
        signal = sum(payload) % 256
        return ProbeResult(
            candidate_state={"kind": "counter", "value": signal},
            confidence=0.68 if payload else 0.25,
            diagnostics={
                "decoder": self.name,
                "latent_width": len(payload),
                "source": "sum(payload) % 256",
                "authority": "diagnostic_probe_only",
            },
        )


class XORProbeDecoder:
    """Probe that recovers a counter candidate from XOR reduction of bytes."""

    name = "xor-reduction-probe"

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        signal = 0
        payload = latent.to_bytes()
        for value in payload:
            signal ^= value
        return ProbeResult(
            candidate_state={"kind": "counter", "value": signal},
            confidence=0.62 if payload else 0.2,
            diagnostics={
                "decoder": self.name,
                "latent_width": len(payload),
                "source": "xor reduction of opaque bytes",
                "authority": "diagnostic_probe_only",
            },
        )


class PrefixProbeDecoder:
    """Probe that recovers a little-endian integer from the first N bytes."""

    name = "prefix-little-endian-probe"

    def __init__(self, width: int = 2) -> None:
        if width <= 0:
            raise ValueError("prefix width must be positive")
        self.width = width

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        payload = latent.to_bytes()
        prefix = payload[: self.width]
        signal = int.from_bytes(prefix, "little") if prefix else 0
        return ProbeResult(
            candidate_state={"kind": "counter", "value": signal},
            confidence=0.66 if len(prefix) == self.width else 0.35,
            diagnostics={
                "decoder": self.name,
                "latent_width": len(payload),
                "prefix_width": self.width,
                "source": "little-endian prefix of opaque bytes",
                "authority": "diagnostic_probe_only",
            },
        )


class EnsembleProbeDecoder:
    """Probe that selects the most confident candidate across decoders."""

    name = "ensemble-probe"

    def __init__(self, decoders: Sequence[ProbeDecoder]) -> None:
        if not decoders:
            raise ValueError("ensemble requires at least one decoder")
        self.decoders = tuple(decoders)

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        results = [(decoder.name, decoder.decode(latent)) for decoder in self.decoders]
        values = [int(result.candidate_state.get("value", 0)) for _, result in results]
        agreement = len(set(values)) == 1
        best_name, best_result = max(results, key=lambda item: item[1].confidence)
        confidence = best_result.confidence if agreement else best_result.confidence * 0.5
        return ProbeResult(
            candidate_state={
                **best_result.candidate_state,
                "ensemble_agreement": agreement,
                "selected_decoder": best_name,
            },
            confidence=confidence,
            diagnostics={
                "decoder": self.name,
                "authority": "diagnostic_probe_only",
                "agreement": agreement,
                "selected_decoder": best_name,
                "members": [
                    {
                        "decoder": name,
                        "candidate_state": result.candidate_state,
                        "confidence": result.confidence,
                    }
                    for name, result in results
                ],
            },
        )


def default_probe_suite() -> List[ProbeDecoder]:
    """Return the standard Track C decoder suite used by experiments."""

    return [
        CounterProbeDecoder(),
        ChecksumProbeDecoder(),
        XORProbeDecoder(),
        PrefixProbeDecoder(width=2),
    ]


class LatentCounterRuntime:
    """Tiny runtime whose only mutable source of truth is opaque latent bytes."""

    _INCREMENT_VECTOR = (1, 3, 5, 7, 11, 13, 17, 19)
    _DECREMENT_VECTOR = (-1, -3, -5, -7, -11, -13, -17, -19)

    def __init__(self, latent: OpaqueLatentState | None = None) -> None:
        self._latent = latent if latent is not None else OpaqueLatentState.zeroed(8)

    def apply(self, event: str) -> None:
        if event == "increment":
            self._latent = self._latent.transformed(self._INCREMENT_VECTOR)
        elif event == "decrement":
            self._latent = self._latent.transformed(self._DECREMENT_VECTOR)
        elif event == "reset":
            self._latent = OpaqueLatentState.zeroed(8)
        else:
            raise ValueError(f"unsupported latent runtime event: {event}")

    def snapshot(self) -> LatentSnapshot:
        return LatentSnapshot(payload=self._latent.to_bytes())

    def restore(self, snapshot: LatentSnapshot) -> None:
        self._latent = OpaqueLatentState.from_bytes(snapshot.payload)

    def perturb(self, index: int = 0, amount: int = 1) -> None:
        self._latent = self._latent.with_perturbation(index=index, amount=amount)

    def probe(self, decoder: ProbeDecoder) -> ProbeResult:
        return decoder.decode(self._latent)


class LatentVectorRuntime:
    """Runtime that mutates opaque bytes with deterministic event rotations."""

    _EVENTS = ("increment", "decrement", "reset")

    def __init__(
        self,
        latent: OpaqueLatentState | None = None,
        *,
        width: int = 8,
        seed: int = 1729,
    ) -> None:
        if width <= 0:
            raise ValueError("width must be positive")
        self.seed = seed
        self._latent = latent if latent is not None else OpaqueLatentState.zeroed(width)
        self._rotations = {
            event: self._rotation_vector(event, len(self._latent.to_bytes()))
            for event in self._EVENTS
            if event != "reset"
        }

    def apply(self, event: str) -> None:
        if event == "reset":
            self._latent = OpaqueLatentState.zeroed(len(self._latent.to_bytes()))
            return
        if event not in self._rotations:
            raise ValueError(f"unsupported latent runtime event: {event}")
        self._latent = self._latent.transformed(self._rotations[event])

    def snapshot(self) -> LatentSnapshot:
        return LatentSnapshot(payload=self._latent.to_bytes())

    def restore(self, snapshot: LatentSnapshot) -> None:
        self._latent = OpaqueLatentState.from_bytes(snapshot.payload)
        self._rotations = {
            event: self._rotation_vector(event, len(snapshot.payload))
            for event in self._EVENTS
            if event != "reset"
        }

    def perturb(self, index: int = 0, amount: int = 1) -> None:
        self._latent = self._latent.with_perturbation(index=index, amount=amount)

    def probe(self, decoder: ProbeDecoder) -> ProbeResult:
        return decoder.decode(self._latent)

    def _rotation_vector(self, event: str, width: int) -> Tuple[int, ...]:
        rng = random.Random(f"{self.seed}:{event}:{width}")
        return tuple(rng.randrange(1, 256) for _ in range(width))


class ResilienceTester:
    """Measures decoder sensitivity to byte-level latent perturbations."""

    def __init__(self, decoders: Sequence[ProbeDecoder], seed: int = 0) -> None:
        if not decoders:
            raise ValueError("resilience tester requires at least one decoder")
        self.decoders = tuple(decoders)
        self.seed = seed

    def run(
        self,
        runtime: LatentRuntime,
        events: Sequence[str],
        amounts: Sequence[int],
    ) -> List[PerturbationReport]:
        for event in events:
            runtime.apply(event)
        baseline = OpaqueLatentState.from_bytes(runtime.snapshot().payload)
        expected_value = self._expected_value(events)

        reports: List[PerturbationReport] = []
        for amount in amounts:
            for case in self._perturbations(baseline, amount):
                decoder_reports = [
                    self._decoder_report(decoder, baseline, case.latent, expected_value)
                    for decoder in self.decoders
                ]
                confidence_decay = sum(
                    report.confidence_decay for report in decoder_reports
                ) / len(decoder_reports)
                reports.append(
                    PerturbationReport(
                        kind=case.kind,
                        amount=case.amount,
                        decoder_reports=decoder_reports,
                        confidence_decay=confidence_decay,
                    )
                )
        return reports

    def decay_curve(
        self,
        runtime: LatentRuntime,
        events: Sequence[str],
        amounts: Sequence[int],
    ) -> List[Tuple[int, float]]:
        reports = self.run(runtime, events, amounts)
        curve: List[Tuple[int, float]] = []
        for amount in amounts:
            matching = [report.confidence_decay for report in reports if report.amount == amount]
            curve.append((amount, sum(matching) / len(matching)))
        return curve

    def _perturbations(
        self, baseline: OpaqueLatentState, amount: int
    ) -> List[PerturbationCase]:
        payload = baseline.to_bytes()
        width = len(payload)
        if width == 0:
            return []
        byte_increment = baseline.with_perturbation(0, amount)
        bit_mask = (1 << (amount % 8)) & 0xFF
        bit_flipped = OpaqueLatentState.from_bytes(
            [
                (value ^ bit_mask) if index == 0 else value
                for index, value in enumerate(payload)
            ]
        )
        rng = random.Random(self.seed + amount)
        noisy = OpaqueLatentState.from_bytes(
            [
                (value + rng.randint(-amount, amount)) % 256
                for value in payload
            ]
        )
        return [
            PerturbationCase("bit_flip", amount, bit_flipped),
            PerturbationCase("byte_increment", amount, byte_increment),
            PerturbationCase("random_noise", amount, noisy),
        ]

    def _decoder_report(
        self,
        decoder: ProbeDecoder,
        baseline: OpaqueLatentState,
        perturbed: OpaqueLatentState,
        expected_value: int,
    ) -> DecoderPerturbationReport:
        before = decoder.decode(baseline)
        after = decoder.decode(perturbed)
        before_value = int(before.candidate_state.get("value", 0))
        after_value = int(after.candidate_state.get("value", 0))
        baseline_confidence = self._baseline_confidence(before_value, expected_value)
        perturbed_confidence = self._perturbed_confidence(before_value, after_value)
        return DecoderPerturbationReport(
            decoder=decoder.name,
            baseline_value=before_value,
            perturbed_value=after_value,
            delta=after_value - before_value,
            changed=before_value != after_value,
            baseline_confidence=baseline_confidence,
            perturbed_confidence=perturbed_confidence,
            confidence_decay=baseline_confidence - perturbed_confidence,
        )

    def _expected_value(self, events: Sequence[str]) -> int:
        value = 0
        for event in events:
            if event == "increment":
                value = (value + 1) % 256
            elif event == "decrement":
                value = (value - 1) % 256
            elif event == "reset":
                value = 0
        return value

    def _baseline_confidence(self, baseline_value: int, expected_value: int) -> float:
        if expected_value == 0:
            return 1.0 if baseline_value == 0 else 0.0
        relative_error = abs(baseline_value - expected_value) / abs(expected_value)
        return max(0.0, min(1.0, 1.0 - relative_error))

    def _perturbed_confidence(self, baseline_value: int, perturbed_value: int) -> float:
        if baseline_value != 0:
            relative_shift = abs(perturbed_value - baseline_value) / abs(baseline_value)
            return max(0.0, min(1.0, 1.0 - relative_shift))
        return max(0.0, min(1.0, abs(perturbed_value) / 256.0))


class CrossDecoderAnalyzer:
    """Analyzes decoder agreement and sensitivity across perturbations."""

    def analyze(self, reports: Sequence[PerturbationReport]) -> CrossDecoderReport:
        by_decoder = self._values_by_decoder(reports)
        amounts = [report.amount for report in reports]
        pairwise = self._pairwise_correlations(by_decoder)
        sensitivities = self._sensitivities(by_decoder)
        agreements = self._agreements(reports)
        amount_correlations = {
            decoder: self._correlation(amounts, values)
            for decoder, values in by_decoder.items()
        }
        return CrossDecoderReport(
            pairwise_correlations=pairwise,
            sensitivities=sensitivities,
            agreements=agreements,
            amount_correlations=amount_correlations,
        )

    def _values_by_decoder(
        self, reports: Sequence[PerturbationReport]
    ) -> Dict[str, List[int]]:
        values: Dict[str, List[int]] = {}
        for report in reports:
            for decoder_report in report.decoder_reports:
                values.setdefault(decoder_report.decoder, []).append(
                    decoder_report.perturbed_value
                )
        return values

    def _pairwise_correlations(
        self, by_decoder: Dict[str, List[int]]
    ) -> List[PairwiseCorrelation]:
        names = sorted(by_decoder)
        correlations: List[PairwiseCorrelation] = []
        for left_index, left in enumerate(names):
            for right in names[left_index + 1 :]:
                correlations.append(
                    PairwiseCorrelation(
                        left=left,
                        right=right,
                        correlation=self._correlation(by_decoder[left], by_decoder[right]),
                    )
                )
        return correlations

    def _sensitivities(self, by_decoder: Dict[str, List[int]]) -> List[DecoderSensitivity]:
        variances = {
            decoder: self._variance(values) for decoder, values in by_decoder.items()
        }
        mean_variance = (
            sum(variances.values()) / len(variances)
            if variances
            else 0.0
        )
        return [
            DecoderSensitivity(
                decoder=decoder,
                variance=variance,
                classification="sensitive" if variance > mean_variance else "stable",
            )
            for decoder, variance in sorted(variances.items())
        ]

    def _agreements(self, reports: Sequence[PerturbationReport]) -> List[PerturbationAgreement]:
        by_amount: Dict[int, List[DecoderPerturbationReport]] = {}
        for report in reports:
            by_amount.setdefault(report.amount, []).extend(report.decoder_reports)

        agreements: List[PerturbationAgreement] = []
        for amount, decoder_reports in sorted(by_amount.items()):
            if not decoder_reports:
                continue
            values = [report.perturbed_value for report in decoder_reports]
            majority_value = max(set(values), key=values.count)
            agreed = [
                report.decoder
                for report in decoder_reports
                if report.perturbed_value == majority_value
            ]
            disagreed = [
                report.decoder
                for report in decoder_reports
                if report.perturbed_value != majority_value
            ]
            agreements.append(
                PerturbationAgreement(
                    amount=amount,
                    agreed_decoders=sorted(set(agreed)),
                    disagreed_decoders=sorted(set(disagreed)),
                    agreement_ratio=len(agreed) / len(decoder_reports),
                )
            )
        return agreements

    def _variance(self, values: Sequence[int]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((value - mean) ** 2 for value in values) / len(values)

    def _correlation(self, left: Sequence[int], right: Sequence[int]) -> float:
        if len(left) != len(right) or len(left) < 2:
            return 0.0
        left_mean = sum(left) / len(left)
        right_mean = sum(right) / len(right)
        numerator = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left, right)
        )
        left_denominator = math.sqrt(
            sum((left_value - left_mean) ** 2 for left_value in left)
        )
        right_denominator = math.sqrt(
            sum((right_value - right_mean) ** 2 for right_value in right)
        )
        denominator = left_denominator * right_denominator
        if denominator == 0:
            return 0.0
        return numerator / denominator


class LatentEventTracker:
    """Tracks event effects across a decoder suite."""

    def __init__(self, runtime: LatentRuntime, decoders: Sequence[ProbeDecoder]) -> None:
        if not decoders:
            raise ValueError("event tracker requires at least one decoder")
        self.runtime = runtime
        self.decoders = tuple(decoders)
        self.transitions: List[EventTransition] = []

    def apply(self, event: str) -> EventTransition:
        before_results = self._decoded_results()
        before = self._decoded_values(before_results)
        self.runtime.apply(event)
        after_results = self._decoded_results()
        after = self._decoded_values(after_results)
        inferred_events = {
            decoder.name: self._infer_decoder_event(before[decoder.name], after[decoder.name])
            for decoder in self.decoders
        }
        consensus = len(set(inferred_events.values())) == 1
        inferred_event_type = self._infer_event_type(
            inferred_events,
            before_results,
            after_results,
        )
        transition = EventTransition(
            event=event,
            decoded_before=before,
            decoded_after=after,
            inferred_events=inferred_events,
            inferred_event_type=inferred_event_type,
            consensus=consensus,
        )
        self.transitions.append(transition)
        return transition

    def report(self) -> Dict[str, Any]:
        return {
            "total_events": len(self.transitions),
            "consensus_events": sum(1 for transition in self.transitions if transition.consensus),
            "divergent_events": [
                transition.event for transition in self.transitions if not transition.consensus
            ],
            "transitions": [
                {
                    "event": transition.event,
                    "decoded_before": transition.decoded_before,
                    "decoded_after": transition.decoded_after,
                    "inferred_events": transition.inferred_events,
                    "inferred_event_type": transition.inferred_event_type,
                    "consensus": transition.consensus,
                }
                for transition in self.transitions
            ],
        }

    def _decoded_results(self) -> Dict[str, ProbeResult]:
        return {
            decoder.name: self.runtime.probe(decoder)
            for decoder in self.decoders
        }

    def _decoded_values(self, results: Dict[str, ProbeResult]) -> Dict[str, int]:
        return {
            name: int(result.candidate_state.get("value", 0))
            for name, result in results.items()
        }

    def _infer_decoder_event(self, before: int, after: int) -> str:
        if after > before:
            return "increment-like"
        if after < before:
            return "decrement-like"
        return "reset-or-stable"

    def _infer_event_type(
        self,
        inferred_events: Dict[str, str],
        before_results: Dict[str, ProbeResult],
        after_results: Dict[str, ProbeResult],
    ) -> str:
        event_types = set(inferred_events.values())
        if len(event_types) != 1:
            return "ambiguous"

        only_event = next(iter(event_types))
        if self._candidate_state_changed_significantly(before_results, after_results):
            return "uncertain"
        if only_event == "increment-like":
            return "confirmed_increment"
        if only_event == "decrement-like":
            return "confirmed_decrement"
        return "ambiguous"

    def _candidate_state_changed_significantly(
        self,
        before_results: Dict[str, ProbeResult],
        after_results: Dict[str, ProbeResult],
    ) -> bool:
        for name, before in before_results.items():
            after = after_results[name]
            before_state = dict(before.candidate_state)
            after_state = dict(after.candidate_state)
            before_value = int(before_state.pop("value", 0))
            after_value = int(after_state.pop("value", 0))
            if before_state != after_state:
                return True
            if abs(after_value - before_value) > 128:
                return True
        return False


class SlopObserver:
    """Build a SLOP-like observer tree from diagnostic probe results."""

    def __init__(self, decoder: ProbeDecoder) -> None:
        self.decoder = decoder

    def project(self, runtime: LatentRuntime) -> Dict[str, Any]:
        decoded = runtime.probe(self.decoder)
        candidate = dict(decoded.candidate_state)
        return {
            "id": "latent-observer",
            "type": "root",
            "properties": {
                "label": "Track C latent-state observer",
                "authority": "diagnostic_projection",
                "strong_projection_evidence": False,
            },
            "children": [
                {
                    "id": "probe-result",
                    "type": "diagnostic",
                    "properties": {
                        "label": "Diagnostic probe result",
                        "decoded_state": candidate,
                        "confidence": decoded.confidence,
                        "authoritative": False,
                        "probed": True,
                    },
                    "children": [],
                    "affordances": [],
                    "meta": {
                        "salience": 0.95,
                        "diagnostic": True,
                        "confidence": decoded.confidence,
                        "authority": "diagnostic_projection",
                        "source": "probe decoder over opaque mock latent",
                    },
                }
            ],
            "affordances": [
                {"action": "snapshot", "idempotent": True},
                {"action": "restore"},
                {
                    "action": "perturb",
                    "params": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "amount": {"type": "integer"},
                        },
                    },
                },
                {
                    "action": "apply",
                    "params": {
                        "type": "object",
                        "properties": {
                            "event": {
                                "type": "string",
                                "enum": ["increment", "decrement", "reset"],
                            }
                        },
                        "required": ["event"],
                    },
                },
            ],
            "meta": {
                "decoder": self.decoder.name,
                "diagnostic": True,
                "salience": 0.9,
                "confidence": decoded.confidence,
                "authority": "diagnostic_projection",
                "caveat": (
                    "Mock latent only; replace OpaqueLatentState with actual "
                    "open-model KV/activation state before making strong claims."
                ),
            },
        }

    def render_text(self, node: Dict[str, Any] | None = None, indent: int = 0) -> str:
        if node is None:
            raise ValueError("render_text requires an observer tree node")

        prefix = "  " * indent
        props = node.get("properties", {})
        label = props.get("label") or node.get("id")
        extra_props = {
            key: value
            for key, value in props.items()
            if key not in {"label", "title"}
        }
        extra_text = ""
        if extra_props:
            extra_text = " (" + ", ".join(
                f"{key}={json.dumps(value, sort_keys=True)}"
                for key, value in extra_props.items()
            ) + ")"
        actions = node.get("affordances", [])
        action_text = ""
        if actions:
            action_text = "  actions: {" + ", ".join(
                self._format_action(action) for action in actions
            ) + "}"

        diagnostic_flag = ""
        if node.get("meta", {}).get("diagnostic") or props.get("probed"):
            diagnostic_flag = " diagnostic=true"

        salience_text = ""
        if "salience" in node.get("meta", {}):
            salience_text = f"  salience={node['meta']['salience']:.2f}"

        line = (
            f"{prefix}[{node['type']}] {node['id']}: {label}"
            f"{extra_text}{diagnostic_flag}{salience_text}{action_text}"
        )
        child_lines = [self.render_text(child, indent + 1) for child in node.get("children", [])]
        return "\n".join([line] + child_lines)

    def _format_action(self, action: Dict[str, Any]) -> str:
        params = action.get("params", {}).get("properties", {})
        if not params:
            return action["action"]
        param_text = ", ".join(
            f"{name}: {schema.get('type', 'any')}" for name, schema in params.items()
        )
        return f"{action['action']}({param_text})"


def run_demo() -> None:
    runtime = LatentCounterRuntime()
    decoders = default_probe_suite()
    ensemble = EnsembleProbeDecoder(decoders)
    observer = SlopObserver(ensemble)
    tester = ResilienceTester(decoders)
    tracker = LatentEventTracker(runtime, decoders)

    print("Track C latent-state observer experiment suite")
    print("This is a mock harness, not proof of actual LLM KV-cache/activation persistence.")
    print()

    print("Initial ensemble observer tree:")
    print(observer.render_text(observer.project(runtime)))
    print()

    print("Multi-event tracking:")
    for event in ("increment", "increment", "decrement", "reset"):
        transition = tracker.apply(event)
        print(
            f"  event={event} consensus={transition.consensus} "
            f"type={transition.inferred_event_type} inferred={transition.inferred_events}"
        )
        print(observer.render_text(observer.project(runtime)))
    print()

    snapshot = runtime.snapshot()
    print("Ensemble comparison across 4 individual probes:")
    print(json.dumps(runtime.probe(ensemble).diagnostics, indent=2, sort_keys=True))
    print()

    print("Perturbation resilience decay curve:")
    counter_reports = tester.run(
        LatentCounterRuntime(OpaqueLatentState.from_bytes(snapshot.payload)),
        events=("increment",),
        amounts=(1, 4, 8, 16),
    )
    decay_curve = []
    for amount in (1, 4, 8, 16):
        matching = [
            report.confidence_decay
            for report in counter_reports
            if report.amount == amount
        ]
        decay_curve.append((amount, sum(matching) / len(matching)))
    for amount, decay in decay_curve:
        print(f"  amount={amount:>2} mean_confidence_decay={decay:.3f}")
    print()

    print("Cross-decoder sensitivity on counter model:")
    counter_analysis = CrossDecoderAnalyzer().analyze(counter_reports)
    for sensitivity in counter_analysis.sensitivities:
        print(
            f"  {sensitivity.decoder}: {sensitivity.classification} "
            f"variance={sensitivity.variance:.2f}"
        )
    print()

    print("Counter vs vector latent model probe comparison:")
    vector_reports = tester.run(
        LatentVectorRuntime(),
        events=("increment",),
        amounts=(1, 4, 8, 16),
    )
    vector_analysis = CrossDecoderAnalyzer().analyze(vector_reports)
    for sensitivity in vector_analysis.sensitivities:
        print(
            f"  vector {sensitivity.decoder}: {sensitivity.classification} "
            f"variance={sensitivity.variance:.2f}"
        )
    print()

    print("Observer tree after perturbation:")
    runtime.perturb(index=0, amount=9)
    print(observer.render_text(observer.project(runtime)))
    print()

    runtime.restore(snapshot)
    print("Restored observer tree JSON:")
    print(json.dumps(observer.project(runtime), indent=2, sort_keys=True))


if __name__ == "__main__":
    run_demo()
