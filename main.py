"""QUOS University self-learning worker.

Run once with ``python main.py --once`` for a smoke test, or without arguments
for the recurring 120-second background loop using Gemini, DeepSeek, Groq, and a Groq Dean.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dean import merge_answers
from saver import ensure_data_file, save_training_example
from teachers import ask_deepseek, ask_gemini, ask_groq


INTERVAL_SECONDS = int(os.getenv("LOOP_INTERVAL_SECONDS", "120"))
RESPONSE_DELAY_SECONDS = float(os.getenv("RESPONSE_DELAY_SECONDS", "3"))
STATUS_PATH = Path(os.getenv("STATUS_PATH", "status.json"))

CURRICULUM = {
    "Computer Science & Programming": [
        "How should a Python programmer choose between a list, tuple, set, and dictionary when designing a data pipeline, and what trade-offs matter most?",
        "What makes a React component maintainable as an application grows, and how should state, effects, and data fetching be separated?",
        "How can an algorithm designer recognize when a problem needs dynamic programming rather than greedy selection, and what evidence supports the choice?",
        "What principles make a distributed system resilient when latency, partial failure, and changing scale are unavoidable?",
    ],
    "Mathematics": [
        "What does a derivative reveal about a changing system beyond its formal calculation, and how can that idea guide a real optimization problem?",
        "Why are eigenvectors and eigenvalues useful for understanding transformations, and where do they appear in applied linear algebra?",
        "How should probability be used to update beliefs when evidence is incomplete, noisy, or potentially biased?",
        "How can mathematical modeling turn a messy real-world question into assumptions, variables, equations, and testable predictions?",
    ],
    "Physics": [
        "How do conservation laws simplify a mechanics problem, and when is choosing the right conserved quantity more useful than solving force equations directly?",
        "Why does thermodynamic irreversibility emerge even when microscopic physical laws are often reversible?",
        "What does quantum superposition mean operationally, and how should it be explained without treating it as ordinary uncertainty?",
        "How do observations across the electromagnetic spectrum help astronomers infer the structure and history of the universe?",
    ],
    "History & Geography": [
        "How do geography, resources, and institutions interact to shape the rise and decline of civilizations?",
        "What distinguishes a historical cause from a background condition, and how can a historian avoid reducing complex events to one explanation?",
        "How have trade routes, migration, and urbanization changed the distribution of power across regions?",
        "How should geopolitical events be analyzed when local actors, global incentives, and historical memory point in different directions?",
    ],
    "Art & Design": [
        "How can color theory guide hierarchy and emotion in a visual composition without turning design into a formula?",
        "What makes typography readable, expressive, and appropriate for a specific audience and medium?",
        "How should a UI/UX designer balance user needs, accessibility, visual clarity, and business constraints?",
        "What can painting and sculpture teach about material, gesture, proportion, and the relationship between intention and interpretation?",
    ],
    "Music & Dance": [
        "How do rhythm, meter, and syncopation shape a listener’s expectation and physical response?",
        "What is the practical difference between harmony and melody, and how can a composer use their tension and resolution?",
        "How do classical dance forms encode balance, timing, posture, and cultural meaning through movement?",
        "What production decisions most strongly change the emotional character of a recording before any new notes are added?",
    ],
    "Food & Nutrition": [
        "How do heat, time, moisture, and surface area interact during cooking, and how can understanding them improve technique?",
        "What makes a dietary claim scientifically credible, and how should someone distinguish mechanism, correlation, and clinical evidence?",
        "How can global cuisines be studied through ingredients, preservation methods, climate, trade, and cultural practice?",
        "How should a person build a nourishing eating pattern that accounts for energy needs, preference, budget, culture, and sustainability?",
    ],
    "Philosophy & Ethics": [
        "How can formal logic expose a hidden assumption in an argument without deciding the moral or practical question by itself?",
        "When should consequences, duties, virtues, or care relationships carry the most weight in an ethical decision?",
        "What does existential responsibility mean when a person cannot control their circumstances but must still choose how to respond?",
        "How can philosophical disagreement become a method for clarifying values rather than a contest to defeat an opponent?",
    ],
    "Biology & Medicine": [
        "How do genes, environment, development, and behavior interact to produce variation in a biological trait?",
        "What is the relationship between anatomy and function, and how does that relationship guide medical reasoning?",
        "How should health evidence be interpreted when a study is statistically significant but its effect is small or uncertain?",
        "Why do infectious diseases spread differently across populations, and which interventions address transmission versus severity?",
    ],
    "Literature & Language": [
        "How do grammar and word choice shape what a speaker can emphasize, imply, or leave ambiguous?",
        "What makes a story’s point of view trustworthy, limited, or deliberately misleading?",
        "How can poetry create meaning through sound, image, rhythm, and omission as well as literal statement?",
        "What can linguistics reveal about how language changes across communities, generations, and social contexts?",
    ],
    "Sports & Fitness": [
        "How should training load, recovery, technique, and adaptation be balanced when building long-term physical performance?",
        "What makes calisthenics progression safe and effective when strength must be developed through leverage and control?",
        "How do attention, confidence, pressure, and routine influence performance in competitive sport?",
        "How can exercise science inform a practical fitness plan without confusing population averages with an individual prescription?",
    ],
    "Economics & Finance": [
        "How do incentives, opportunity cost, and marginal analysis help explain a microeconomic decision?",
        "What should a learner track when comparing inflation, unemployment, growth, and monetary policy in a macroeconomic cycle?",
        "How do diversification, time horizon, risk tolerance, and fees interact in a long-term investment decision?",
        "How can personal finance systems turn irregular income, competing goals, and uncertainty into a workable plan?",
    ],
}

QUESTIONS = [question for questions in CURRICULUM.values() for question in questions]

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
    question = random.choice(QUESTIONS)
    _question_index += 1
    return question


def _pause_after_response(label: str) -> None:
    """Pace provider calls to reduce burst pressure and rate-limit risk."""
    if RESPONSE_DELAY_SECONDS > 0:
        logging.info("Waiting %.1fs after %s response", RESPONSE_DELAY_SECONDS, label)
        _stop_event.wait(RESPONSE_DELAY_SECONDS)


TEACHER_SYSTEM = (
    "You are an independent teacher at QUOS University. Explore the full curriculum "
    "across computer science, mathematics, physics, history, geography, art, design, "
    "music, dance, food, nutrition, philosophy, ethics, biology, medicine, literature, "
    "language, sports, fitness, economics, finance, habits, money psychology, and "
    "personal growth. Use rigorous, humane, original insight and prefer practical "
    "reasoning over generic summaries or motivation."
)

TEACHER_SPECS = (
    ("Gemini", ask_gemini),
    ("DeepSeek", ask_deepseek),
    ("Groq", ask_groq),
)


def run_once() -> str:
    question = generate_question()
    logging.info("New QUOS question for Gemini, DeepSeek, and Groq: %s", question)
    write_status(state="asking_teachers", question=question, teachers_completed=[])

    teacher_answers: dict[str, str] = {}
    for provider, ask_teacher in TEACHER_SPECS:
        logging.info("Asking %s teacher", provider)
        teacher_answers[provider] = ask_teacher(question, system_instruction=TEACHER_SYSTEM)
        _pause_after_response(f"{provider} teacher")
        write_status(
            state="asking_teachers",
            question=question,
            teachers_completed=list(teacher_answers),
        )

    write_status(
        state="dean_synthesis",
        question=question,
        teachers_completed=list(teacher_answers),
    )
    final_answer = merge_answers(question, teacher_answers)
    _pause_after_response("Groq Dean")
    save_training_example(question, final_answer)
    write_status(
        state="idle",
        question=question,
        last_answer=final_answer,
        last_completed_at=_utc_now(),
        teachers_completed=list(teacher_answers),
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
    logging.info("QUOS University multi-teacher worker started; interval=%ss", INTERVAL_SECONDS)
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
