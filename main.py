import time
from teachers import ask_gemini, ask_claude, ask_deepseek, ask_chatgpt
from dean import dean_merge

# This runs forever
while True:
    question = "What is the best way to build a daily habit?"
    
    answers = [
        ask_gemini(question),
        ask_claude(question),
        ask_deepseek(question),
        ask_chatgpt(question)
    ]
    
    final_answer = dean_merge(answers)
    
    print(f"✅ Saved: {final_answer[:50]}...")
    
    time.sleep(300)  # 5 minutes