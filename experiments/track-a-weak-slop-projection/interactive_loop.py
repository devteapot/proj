"""Reusable interactive weak-projection loop for the todo SLOP MVP."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from action_router import ActionInvocation, ActionRouter
from drift_detector import DriftReport, detect_drift
from model_adapter import DeterministicAdapter, ModelAdapter, OpenAIAdapter
from prompt_builder import EphemeralTailPromptBuilder
from slop_assembler import SlopAssembler
from state_tree import TodoApp, to_slop_tree


@dataclass(frozen=True)
class TurnResult:
    """Result and measurements for one weak-projection turn."""

    turn_index: int
    user_text: str
    invocation: ActionInvocation
    prompt_size: int
    tail_size: int
    tail: str
    drift_report: DriftReport
    snapshot: tuple[dict[str, Any], ...]


@dataclass
class LoopMetrics:
    """Accumulated prompt and drift metrics for a loop session."""

    total_turns: int = 0
    accumulated_prompt_size: int = 0
    total_state_changes: int = 0
    drift_events: int = 0
    prompt_tail_sizes: list[int] = field(default_factory=list)
    turn_reports: list[DriftReport] = field(default_factory=list)

    @property
    def drift_percentage(self) -> float:
        """Return aggregate drift as a percentage of all observed changes."""
        if self.total_state_changes == 0:
            return 0.0
        return self.drift_events / self.total_state_changes * 100.0

    @property
    def prompt_tail_growth(self) -> int:
        """Return tail-size delta from the first measured turn to the last."""
        if len(self.prompt_tail_sizes) < 2:
            return 0
        return self.prompt_tail_sizes[-1] - self.prompt_tail_sizes[0]


class WeakProjectionLoop:
    """Own a fresh todo app and run model-selected affordance turns."""

    def __init__(
        self,
        adapter: ModelAdapter | None = None,
        adapter_name: str | None = None,
        app: TodoApp | None = None,
        assembler: SlopAssembler | None = None,
        builder: EphemeralTailPromptBuilder | None = None,
    ) -> None:
        self.app = app or TodoApp()
        self.assembler = assembler or SlopAssembler()
        self.builder = builder or EphemeralTailPromptBuilder(renderer=self.assembler)
        if adapter is None:
            adapter, adapter_name = choose_default_adapter()
        self.adapter = adapter
        self.adapter_name = adapter_name or adapter.__class__.__name__
        self.router = ActionRouter(self.app)
        self.metrics = LoopMetrics()

    def render_current_tail(self) -> str:
        """Render the current explicit app state as a fresh SLOP tail."""
        tree = self.assembler.assemble(self.app, to_slop_tree)
        return self.assembler.render_tail(tree)

    def process_turn(self, user_text: str) -> TurnResult:
        """Apply one free-form user command through the projected SLOP state."""
        normalized = user_text.strip()
        if not normalized:
            raise ValueError("user command cannot be empty")

        previous_snapshot = self.app.snapshot()
        tree = self.assembler.assemble(self.app, to_slop_tree)
        prompt_messages = list(self.builder.stable_messages) + [
            {"role": "user", "content": normalized}
        ]
        prompt = self.builder.build_request(prompt_messages, tree)
        tail = extract_tail(prompt)

        invocation = self.adapter.choose_action(normalized, tree)
        self.router.apply(invocation)
        current_snapshot = self.app.snapshot()

        drift_report = detect_drift(
            previous_snapshot,
            current_snapshot,
            normalized,
            invocation,
        )
        self.builder.add_message("user", normalized)
        self.builder.add_message(
            "assistant",
            f"invoked {invocation.action} with {invocation.params}",
        )
        self._record_metrics(len(prompt), len(tail), drift_report)

        return TurnResult(
            turn_index=self.metrics.total_turns,
            user_text=normalized,
            invocation=invocation,
            prompt_size=len(prompt),
            tail_size=len(tail),
            tail=tail,
            drift_report=drift_report,
            snapshot=tuple(dict(item) for item in current_snapshot),
        )

    def run_scripted(self, commands: Iterable[str]) -> list[TurnResult]:
        """Run canned commands through the same path as the CLI loop."""
        return [self.process_turn(command) for command in commands]

    def _record_metrics(
        self,
        prompt_size: int,
        tail_size: int,
        drift_report: DriftReport,
    ) -> None:
        self.metrics.total_turns += 1
        self.metrics.accumulated_prompt_size += prompt_size
        self.metrics.prompt_tail_sizes.append(tail_size)
        self.metrics.total_state_changes += drift_report.total_changes
        self.metrics.drift_events += drift_report.drift_count
        self.metrics.turn_reports.append(drift_report)


def choose_default_adapter() -> tuple[ModelAdapter, str]:
    """Try OpenAI first and fall back to deterministic mode without an API key."""
    try:
        return OpenAIAdapter(), "openai"
    except ValueError as exc:
        if "OPENAI_API_KEY" not in str(exc):
            raise
        return DeterministicAdapter(), "deterministic"


def extract_tail(prompt: str) -> str:
    """Return the ephemeral SLOP tail from a rendered request prompt."""
    start = prompt.index("<slop-state")
    return prompt[start:]


def run_cli() -> LoopMetrics:
    """Run the minimal terminal loop and return final session metrics."""
    loop = WeakProjectionLoop()
    print(f"adapter: {loop.adapter_name}")
    print("commands: create <title>, complete current todo, quit")

    while True:
        print("--- current <slop-state> tail ---")
        print(loop.render_current_tail())
        try:
            user_text = input("weak-slop> ")
        except EOFError:
            print()
            break
        if user_text.strip().lower() in {"q", "quit", "exit"}:
            break
        if not user_text.strip():
            continue
        try:
            result = loop.process_turn(user_text)
        except Exception as exc:
            print(f"error: {exc}")
            continue
        print(
            f"invoked {result.invocation.action} {result.invocation.params} | "
            f"turn drift={result.drift_report.drift_count} | "
            f"tail_chars={result.tail_size}"
        )

    print("--- session summary ---")
    print(f"turns={loop.metrics.total_turns}")
    print(f"accumulated_prompt_chars={loop.metrics.accumulated_prompt_size}")
    print(f"drift_events={loop.metrics.drift_events}")
    print(f"drift_percentage={loop.metrics.drift_percentage:.1f}%")
    return loop.metrics


if __name__ == "__main__":
    run_cli()
