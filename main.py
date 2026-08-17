"""QUOS University self-learning worker.

Run once with ``python main.py --once`` for a smoke test, or without arguments
for the recurring 30-second background loop.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dean import merge_answers
from saver import ensure_data_file, save_training_example
from teachers import ask_gemini


INTERVAL_SECONDS = int(os.getenv("LOOP_INTERVAL_SECONDS", "30"))
RESPONSE_DELAY_SECONDS = float(os.getenv("RESPONSE_DELAY_SECONDS", "3"))
STATUS_PATH = Path(os.getenv("STATUS_PATH", "status.json"))

QUESTIONS = [
    "What hidden reward keeps a person repeating a habit they say they want to change, and how can they redesign that reward without relying on willpower?",
    "How can someone tell whether a money decision is an expression of their values or a short-term attempt to regulate an uncomfortable emotion?",
    "Why do intelligent people often protect an outdated self-image, and what small experiment could help them become more psychologically flexible?",
    "What is the difference between genuine ambition and borrowed ambition, and how could a person discover which goals are truly theirs?",
    "How does a person’s relationship with uncertainty shape their earning, spending, and learning behavior?",
    "When does self-discipline become self-punishment, and what would a sustainable form of discipline look like in daily life?",
    "Why can visible progress sometimes sabotage long-term growth, and how should someone measure progress when the most important change is internal?",
    "How can a person interrupt a scarcity mindset without pretending that real financial constraints do not exist?",
    "What makes a personal rule trustworthy enough to guide behavior when motivation, mood, and social pressure all change?",
    "How should someone respond when their current habits are rational adaptations to an old environment that no longer exists?",
]

_stop_event = threading.Event()
_question_index = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(**updates: Any) -> None:
    """Write a small status document for logs, health checks, and the preview."""
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {}
    if STATUS_PATH.exists():
        try:
            status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = {}
    status.update(updates)
    status["updated_at"] = _utc_now()
    temporary = STATUS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2), encoding="utf-8")
    temporary.replace(STATUS_PATH)


def generate_question() -> str:
    global _question_index
    question = QUESTIONS[_question_index % len(QUESTIONS)]
    _question_index += 1
    return question


def _pause_after_response(label: str) -> None:
    """Pace provider calls to reduce burst pressure and rate-limit risk."""
    if RESPONSE_DELAY_SECONDS > 0:
        logging.info("Waiting %.1fs after %s response", RESPONSE_DELAY_SECONDS, label)
        _stop_event.wait(RESPONSE_DELAY_SECONDS)


def ask_gemini_teacher(question: str) -> str:
    """Ask Gemini for the one teacher perspective used by this cycle."""
    return ask_gemini(
        question,
        system_instruction=(
            "You are the sole teacher at QUOS University. Explore habits, money "
            "psychology, and personal growth with rigorous, humane, original insight. "
            "Prefer practical reasoning over generic motivation."
        ),
    )


def run_once() -> str:
    question = generate_question()
    logging.info("New QUOS question: %s", question)
    write_status(state="asking_gemini", question=question, teachers_completed=[])

    gemini_answer = ask_gemini_teacher(question)
    _pause_after_response("Gemini teacher")
    write_status(state="dean_synthesis", question=question, teachers_completed=["Gemini"])
    final_answer = merge_answers(question, gemini_answer)
    _pause_after_response("Gemini Dean")
    save_training_example(question, final_answer)
    write_status(
        state="idle",
        question=question,
        last_answer=final_answer,
        last_completed_at=_utc_now(),
        teachers_completed=["Gemini"],
    )
    return final_answer


def _handle_signal(signum: int, _frame: Any) -> None:
    logging.info("Received signal %s; stopping after the current operation.", signum)
    _stop_event.set()


def run_forever() -> None:
    ensure_data_file()
    write_status(
        state="starting",
        interval_seconds=INTERVAL_SECONDS,
        response_delay_seconds=RESPONSE_DELAY_SECONDS,
    )
    logging.info("QUOS University Gemini-only worker started; interval=%ss", INTERVAL_SECONDS)
    while not _stop_event.is_set():
        cycle_started = time.monotonic()
        try:
            final_answer = run_once()
            print("\n" + "=" * 80 + "\nQUOS UNIVERSITY — DEAN'S LESSON\n" + "=" * 80)
            print(final_answer)
            print("=" * 80 + "\n", flush=True)
        except Exception as exc:  # noqa: BLE001 - worker should remain alive for transient failures
            logging.exception("Cycle failed; no training example was written: %s", exc)
            write_status(state="error", error=str(exc), last_failed_at=_utc_now())

        elapsed = time.monotonic() - cycle_started
        wait_seconds = max(0, INTERVAL_SECONDS - int(elapsed))
        if wait_seconds:
            logging.info("Next cycle in %ss", wait_seconds)
            _stop_event.wait(wait_seconds)

    write_status(state="stopped")
    logging.info("QUOS University worker stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QUOS University self-learning worker.")
    parser.add_argument("--once", action="store_true", help="Run exactly one cycle and exit.")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    args = parse_args()
    if args.once:
        ensure_data_file()
        try:
            print(run_once())
        except Exception as exc:  # noqa: BLE001
            logging.exception("Single cycle failed: %s", exc)
            raise SystemExit(1) from exc
    else:
        run_forever()
