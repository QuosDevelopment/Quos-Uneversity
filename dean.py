"""Dean synthesis for QUOS University."""

from __future__ import annotations

from teachers import ask_gemini


def merge_answers(question: str, answers: dict[str, str]) -> str:
    """Merge teacher answers into one clear, useful, original lesson."""
    teacher_packet = "\n\n".join(
        f"--- {teacher} ---\n{answer.strip()}" for teacher, answer in answers.items()
    )
    prompt = f"""You are the Dean of QUOS University.

Question:
{question}

Four teachers answered the question:
{teacher_packet}

Create one powerful, original final answer. Synthesize the strongest insights,
resolve contradictions, and do not mention the teachers or this synthesis
process. The response should be self-contained and practical. Use this structure:

1. Core insight
2. Why it matters
3. A concrete practice for the next 24 hours
4. One reflection question

Write in clear, humane language. Avoid generic motivational clichés. Keep it
between 300 and 700 words."""
    return ask_gemini(prompt, system_instruction="You are the discerning Dean of QUOS University.")
