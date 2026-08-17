"""Gemini-backed Dean synthesis for QUOS University."""

from __future__ import annotations

from teachers import ask_gemini


def merge_answers(question: str, gemini_answer: str) -> str:
    """Use Gemini as the Dean to refine one teacher response into a lesson."""
    prompt = f"""You are the Dean of QUOS University.

Question:
{question}

A Gemini teacher offered this initial perspective:
--- Gemini teacher ---
{gemini_answer.strip()}

Create one powerful, original final answer. Deepen and sharpen the strongest
ideas, correct weak reasoning, and do not mention the teacher or this synthesis
process. The response should be self-contained and practical. Use this structure:

1. Core insight
2. Why it matters
3. A concrete practice for the next 24 hours
4. One reflection question

Write in clear, humane language. Avoid generic motivational clichés. Keep it
between 300 and 700 words."""
    return ask_gemini(prompt, system_instruction="You are the discerning Dean of QUOS University.")
