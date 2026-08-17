from __future__ import annotations

from teachers import ask_groq


def merge_answers(question: str, teacher_answers: dict[str, str]) -> str:
    """Use Groq as the Dean to synthesize the independent teacher perspectives."""
    perspectives = []
    for provider, answer in teacher_answers.items():
        perspectives.append(f"--- {provider} teacher ---\n{answer.strip()}")
    joined_perspectives = "\n\n".join(perspectives)
    prompt = f"""You are the Dean of QUOS University.

Question:
{question}

Three independent teachers offered these perspectives:
{joined_perspectives}

Compare the perspectives, identify agreement and disagreement, correct weak or
unsupported reasoning, and synthesize the strongest ideas into one original
answer. Do not mention the providers, teachers, or this synthesis process. The
response must be self-contained and practical. Use this structure:

1. Core insight
2. Why it matters
3. A concrete practice for the next 24 hours
4. One reflection question

Write in clear, humane language. Avoid generic motivational clichés. Keep it
between 300 and 700 words."""
    return ask_groq(prompt, system_instruction="You are the discerning Dean of QUOS University. Compare multiple expert perspectives before writing one accurate, useful lesson.")
