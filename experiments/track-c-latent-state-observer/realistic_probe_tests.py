"""Realistic stress tests for Track C probe decoders.

These tests encode a tiny structured record list into opaque bytes, then probe
it back out without adding symbolic state to the runtime. The custom decoder is
still deterministic and mock-level, but it exercises richer behavior than the
counter probes: schema validation, checksums, field-level mutation, and partial
corruption after byte perturbations.
"""

from __future__ import annotations

import os
import random
import sys
import unittest
from typing import Any, Dict, Iterable, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from experiment_harness import run_full_experiment  # noqa: E402
from prototype import (  # noqa: E402
    EnsembleProbeDecoder,
    OpaqueLatentState,
    ProbeResult,
)


MAGIC = b"LSO1"


class CustomStructureProbeDecoder:
    """Decode a tiny checksummed record list from opaque latent bytes."""

    name = "custom-structure-probe"

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        payload = latent.to_bytes()
        errors: List[str] = []
        records: List[Dict[str, Any]] = []
        expected_length = 0
        valid_checksum = False

        if len(payload) < len(MAGIC) + 2:
            errors.append("truncated_header")
        elif not payload.startswith(MAGIC):
            errors.append("bad_magic")
        else:
            count = payload[len(MAGIC)]
            expected_length = len(MAGIC) + 1 + (count * 2) + 1
            if len(payload) < expected_length:
                errors.append("truncated_records")
            elif len(payload) > expected_length:
                errors.append("trailing_bytes")
            else:
                offset = len(MAGIC) + 1
                for _ in range(count):
                    record_id = chr(payload[offset])
                    records.append({"id": record_id, "v": payload[offset + 1]})
                    offset += 2
                valid_checksum = (sum(payload[:-1]) % 256) == payload[-1]
                if not valid_checksum:
                    errors.append("checksum_mismatch")

        structurally_valid = not errors or errors == ["checksum_mismatch"]
        confidence = 0.91 if not errors else 0.42 if structurally_valid else 0.05
        return ProbeResult(
            candidate_state={
                "kind": "record-list",
                "records": records,
                "value": sum(int(record["v"]) for record in records),
                "valid": not errors,
            },
            confidence=confidence,
            diagnostics={
                "decoder": self.name,
                "valid_checksum": valid_checksum,
                "errors": errors,
                "record_count": len(records),
                "expected_length": expected_length,
                "authority": "diagnostic_probe_only",
            },
        )


class FixedValueProbeDecoder:
    """Probe used to force a known ensemble agreement pattern."""

    def __init__(self, name: str, value: int, confidence: float = 0.8) -> None:
        self.name = name
        self.value = value
        self.confidence = confidence

    def decode(self, latent: OpaqueLatentState) -> ProbeResult:
        return ProbeResult(
            candidate_state={"kind": "fixed", "value": self.value},
            confidence=self.confidence,
            diagnostics={"decoder": self.name, "latent_width": len(latent.to_bytes())},
        )


def encode_records(records: Iterable[Dict[str, Any]]) -> bytes:
    """Encode one-character IDs and byte values into a checksummed payload."""

    normalized = list(records)
    if len(normalized) > 255:
        raise ValueError("record count must fit in one byte")

    payload = bytearray(MAGIC)
    payload.append(len(normalized))
    for record in normalized:
        record_id = str(record["id"])
        value = int(record["v"])
        if len(record_id) != 1 or ord(record_id) > 127:
            raise ValueError("record id must be one ASCII character")
        if value < 0 or value > 255:
            raise ValueError("record value must fit in one byte")
        payload.append(ord(record_id))
        payload.append(value)

    payload.append(sum(payload) % 256)
    return bytes(payload)


def mutate_record_value(
    latent: OpaqueLatentState,
    record_id: str,
    value: int,
) -> OpaqueLatentState:
    """Return a new latent with one record value changed and checksum updated."""

    payload = bytearray(latent.to_bytes())
    count = payload[len(MAGIC)]
    for index in range(count):
        offset = len(MAGIC) + 1 + (index * 2)
        if chr(payload[offset]) == record_id:
            payload[offset + 1] = value
            payload[-1] = sum(payload[:-1]) % 256
            return OpaqueLatentState.from_bytes(payload)
    raise KeyError(record_id)


def perturb_random_record_byte(
    latent: OpaqueLatentState,
    *,
    seed: int,
    amount: int,
) -> Tuple[int, OpaqueLatentState]:
    """Perturb a deterministic random record byte without fixing the checksum."""

    payload = bytearray(latent.to_bytes())
    mutable_indices = list(range(len(MAGIC) + 1, len(payload) - 1))
    index = random.Random(seed).choice(mutable_indices)
    payload[index] = (payload[index] + amount) % 256
    return index, OpaqueLatentState.from_bytes(payload)


class RealisticProbeTests(unittest.TestCase):
    """Exercises structured decoding and disagreement behavior."""

    def setUp(self) -> None:
        self.decoder = CustomStructureProbeDecoder()
        self.latent = OpaqueLatentState.from_bytes(
            encode_records([{"id": "a", "v": 1}, {"id": "b", "v": 2}])
        )

    def decode(self, latent: OpaqueLatentState | None = None) -> ProbeResult:
        return self.decoder.decode(latent or self.latent)

    def test_structure_probe_decodes_valid_payload(self) -> None:
        result = self.decode()

        self.assertEqual(
            [{"id": "a", "v": 1}, {"id": "b", "v": 2}],
            result.candidate_state["records"],
        )
        self.assertEqual(3, result.candidate_state["value"])
        self.assertTrue(result.candidate_state["valid"])
        self.assertEqual([], result.diagnostics["errors"])
        self.assertGreater(result.confidence, 0.9)

    def test_encode_mutate_decode_verifies_changed_fields(self) -> None:
        mutated = mutate_record_value(self.latent, "a", 9)
        result = self.decode(mutated)

        self.assertEqual(
            [{"id": "a", "v": 9}, {"id": "b", "v": 2}],
            result.candidate_state["records"],
        )
        self.assertEqual(11, result.candidate_state["value"])
        self.assertTrue(result.diagnostics["valid_checksum"])

    def test_perturb_random_value_byte_reports_expected_corruption(self) -> None:
        index, perturbed = perturb_random_record_byte(self.latent, seed=1, amount=9)
        result = self.decode(perturbed)

        self.assertEqual(6, index)
        self.assertEqual(
            [{"id": "a", "v": 10}, {"id": "b", "v": 2}],
            result.candidate_state["records"],
        )
        self.assertFalse(result.candidate_state["valid"])
        self.assertEqual(["checksum_mismatch"], result.diagnostics["errors"])
        self.assertLess(result.confidence, self.decode().confidence)

    def test_truncated_payload_reports_low_confidence(self) -> None:
        truncated = OpaqueLatentState.from_bytes(self.latent.to_bytes()[:-2])
        result = self.decode(truncated)

        self.assertEqual([], result.candidate_state["records"])
        self.assertIn("truncated_records", result.diagnostics["errors"])
        self.assertEqual(0.05, result.confidence)

    def test_bad_magic_reports_corruption(self) -> None:
        payload = bytearray(self.latent.to_bytes())
        payload[0] = ord("X")
        result = self.decode(OpaqueLatentState.from_bytes(payload))

        self.assertEqual([], result.candidate_state["records"])
        self.assertIn("bad_magic", result.diagnostics["errors"])
        self.assertFalse(result.candidate_state["valid"])

    def test_ensemble_of_four_decoders_with_one_disagreement(self) -> None:
        decoders = [
            FixedValueProbeDecoder("agree-a", 42, confidence=0.8),
            FixedValueProbeDecoder("agree-b", 42, confidence=0.75),
            FixedValueProbeDecoder("agree-c", 42, confidence=0.7),
            FixedValueProbeDecoder("disagree", 99, confidence=0.65),
        ]
        result = EnsembleProbeDecoder(decoders).decode(self.latent)
        member_values = [
            member["candidate_state"]["value"]
            for member in result.diagnostics["members"]
        ]

        self.assertEqual(3, member_values.count(42))
        self.assertEqual(1, member_values.count(99))
        self.assertFalse(result.candidate_state["ensemble_agreement"])
        self.assertEqual("agree-a", result.candidate_state["selected_decoder"])
        self.assertEqual(0.4, result.confidence)

    def test_full_experiment_records_recovery_and_accuracy(self) -> None:
        result = run_full_experiment(
            ("increment", "decrement", "reset"),
            perturb_every=1,
            perturbation_amounts=(1,),
        )

        self.assertEqual(3, len(result.probe_consistency_over_time))
        self.assertEqual(3, len(result.confidence_trajectory))
        self.assertEqual(3, len(result.recovery_checks))
        self.assertEqual(1.0, result.perturbation_recovery_rate)
        self.assertEqual(1.0, result.event_inference_accuracy)


if __name__ == "__main__":
    unittest.main()
