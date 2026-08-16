from teachers import ask_gemini

def dean_merge(answers):
    prompt = f"""
You are the Dean of QUOS University.
You received 4 answers from your professors.

Answer 1: {answers[0]}
Answer 2: {answers[1]}
Answer 3: {answers[2]}
Answer 4: {answers[3]}

Merge them into ONE clear, powerful, original answer.
Do not copy them verbatim. Write in your own words.
"""
    return ask_gemini(prompt)