# Track C - Latent-State Observer Scaffold

This directory contains a careful mock harness for the Track C strong-projection experiment. It is intended to test the mechanics of probing, snapshotting, restoring, perturbing, and observing an opaque latent state.

It is **not** proof that an LLM KV-cache, activation stream, recurrent state, or other model-internal state can persist as an application runtime.

## What This Prototype Is

- `OpaqueLatentState` stores uninterpreted bytes.
- `LatentCounterRuntime` mutates those bytes with tiny counter-like events.
- `LatentVectorRuntime` mutates those bytes with deterministic event-specific
  vector rotations to test whether probe behavior generalizes beyond one event
  pattern.
- `ProbeDecoder` is an interface for recovering candidate app state from opaque latent bytes.
- `CounterProbeDecoder`, `ChecksumProbeDecoder`, `XORProbeDecoder`, and
  `PrefixProbeDecoder` are deterministic mock probes used only for local
  testing.
- `EnsembleProbeDecoder` compares the individual probe candidates and lowers
  confidence when they disagree.
- `ResilienceTester` runs bit-flip, byte-increment, and random-noise
  perturbations against snapshots and reports decoded deltas plus confidence
  decay computed from actual probe output stability.
- `CrossDecoderAnalyzer` reports pairwise decoder correlations, stable vs.
  sensitive decoders, and decoder agreement by perturbation amount.
- `LatentEventTracker` logs decoded before/after values for event sequences and
  reports consensus, divergence, and multi-factor inferred event type across
  probes.
- `SlopObserver` projects the probe result into a SLOP-like observer tree with properties, children, affordances, and diagnostic metadata.
- `experiment_harness.py` adds `ProbeTimeline`, perturbation recovery checks,
  and `run_full_experiment(...)` for end-to-end probe consistency, confidence,
  recovery, and event-inference metrics.
- `realistic_probe_tests.py` adds a checksummed structured-record probe that
  decodes a small encoded byte structure, validates field-level mutation,
  detects byte corruption, and exercises deliberate ensemble disagreement.
- `demo_exploration.py` runs a fixed ten-event counter sequence, prints the
  per-step probe timeline, perturbation resilience results, event-inference
  accuracy, and a summary of what must change for real model internals.

The mock latent is an engineering stand-in for an actual open-model KV/activation snapshot. The observer tree is diagnostic projection, not the authoritative state. Success here only validates harness mechanics: probe, snapshot, restore, perturb, observe.

## What This Prototype Is Not

This is not strong evidence for the full neural app runtime thesis until `OpaqueLatentState` is replaced by actual model KV-cache or activation state from an open inference runtime.

The runtime does not expose a symbolic `counter_value`, todo list, JSON app store, or other canonical application state through its API. The only runtime source of truth is the opaque byte payload. Any visible counter-like value is recovered by a probe and must be treated as diagnostic.

## Run The Demo

```bash
python3 experiments/track-c-latent-state-observer/prototype.py
python3 experiments/track-c-latent-state-observer/demo_exploration.py
```

## Run Tests

```bash
python3 -m unittest experiments/track-c-latent-state-observer/test_prototype.py
python3 -m unittest experiments/track-c-latent-state-observer/test_probe_suite.py
python3 -m unittest experiments/track-c-latent-state-observer/realistic_probe_tests.py
```

## Interpreting Results

The demo prints a SLOP-like observer tree at each stage, an ensemble comparison
for four individual probes, a perturbation confidence-decay curve, cross-decoder
sensitivity summaries for the counter and vector models, multi-event tracking
consensus, and snapshot restore output. If decoded values change, that only
shows that the mock probes are sensitive to byte-level latent changes. It does
not show that a real model stores application state internally.

The useful next step is replacing `OpaqueLatentState` with snapshots from an open inference runtime, then checking whether independent probes can recover stable app state across event updates, perturbations, and restores without falling back to a symbolic app store.
