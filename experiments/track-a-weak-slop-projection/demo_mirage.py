"""Scripted Mirage-style demo for the weak SLOP projection loop."""

from __future__ import annotations

import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from interactive_loop import WeakProjectionLoop
from model_adapter import DeterministicAdapter


CANNED_COMMANDS = (
    "create Draft Track A README",
    "create Define drift detector",
    "complete current todo",
    "create Measure prompt tail growth",
    "complete current todo",
    "create Add scripted Mirage demo",
    "create Document weak projection loop",
    "complete current todo",
    "create Run evaluation summary",
    "complete current todo",
)


def run_demo() -> WeakProjectionLoop:
    """Run ten deterministic turns and print prompt-growth/drift metrics."""
    loop = WeakProjectionLoop(
        adapter=DeterministicAdapter(),
        adapter_name="deterministic",
    )
    print("Mirage weak-projection scripted demo")
    print(f"adapter={loop.adapter_name}")
    print("--- turns ---")
    for result in loop.run_scripted(CANNED_COMMANDS):
        print(
            f"{result.turn_index:02d}. {result.user_text!r} -> "
            f"{result.invocation.action} {result.invocation.params} | "
            f"tail_chars={result.tail_size} | "
            f"drift={result.drift_report.drift_count}"
        )

    first_tail = loop.metrics.prompt_tail_sizes[0] if loop.metrics.prompt_tail_sizes else 0
    last_tail = loop.metrics.prompt_tail_sizes[-1] if loop.metrics.prompt_tail_sizes else 0
    print("--- summary ---")
    print(f"turns={loop.metrics.total_turns}")
    print(f"accumulated_prompt_chars={loop.metrics.accumulated_prompt_size}")
    print(f"tail_chars_first={first_tail}")
    print(f"tail_chars_last={last_tail}")
    print(f"tail_growth_chars={loop.metrics.prompt_tail_growth}")
    print(f"state_changes={loop.metrics.total_state_changes}")
    print(f"drift_events={loop.metrics.drift_events}")
    print(f"drift_percentage={loop.metrics.drift_percentage:.1f}%")
    print("final_state=")
    for item in loop.app.snapshot():
        print(f"  {item['id']}: {item['title']} completed={item['completed']}")
    return loop


if __name__ == "__main__":
    run_demo()
