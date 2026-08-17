from __future__ import annotations

import logging
import os
import time

from teachers import ask_deepseek, ask_groq


def merge_answers(question: str, teacher_answers: dict[str, str]) -> str:
    """Use Groq as the Dean to synthesize the independent teacher perspectives."""
    perspectives = []
    for provider, answer in teacher_answers.items():
        perspectives.append(f"--- {provider} teacher ---\n{answer.strip()}")
    joined_perspectives = "\n\n".join(perspectives)
    perspective_count = len(teacher_answers)
    perspective_label = "perspective" if perspective_count == 1 else "perspectives"
    prompt = f"""You are the Dean of QUOS University.

Question:
{question}

{perspective_count} independent teacher {perspective_label} offered the following:
{joined_perspectives}

Compare the available perspective(s), identify agreement and disagreement when
possible, correct weak or unsupported reasoning, and synthesize the strongest ideas into one original
answer. Do not mention the providers, teachers, or this synthesis process. The
response must be self-contained and practical. Use this structure:

1. Core insight
2. Why it matters
3. A concrete practice for the next 24 hours
4. One reflection question

Write in clear, humane language. Avoid generic motivational clichés. Keep it
between 300 and 700 words."""
    system_instruction = "You are the discerning Dean of QUOS University. Compare the available expert perspective(s) before writing one accurate, useful lesson."
    delay = float(os.getenv("RESPONSE_DELAY_SECONDS", "3"))
    try:
        return ask_groq(prompt, system_instruction=system_instruction)
    except Exception as groq_error:  # noqa: BLE001 - use DeepSeek when Groq is unavailable
        logging.warning("Groq Dean unavailable; falling back to DeepSeek Dean", exc_info=True)
        if delay > 0:
            time.sleep(delay)
        try:
            return ask_deepseek(prompt, system_instruction=system_instruction)
        except Exception as deepseek_error:  # noqa: BLE001 - surface both failures to the worker
            if delay > 0:
                time.sleep(delay)
            raise RuntimeError(
                f"Both Dean providers failed: Groq: {groq_error}; DeepSeek: {deepseek_error}"
            ) from deepseek_error
