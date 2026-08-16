import requests

GEMINI_KEY = "YOUR_GEMINI_KEY"
CLAUDE_KEY = "YOUR_CLAUDE_KEY"
DEEPSEEK_KEY = "YOUR_DEEPSEEK_KEY"
CHATGPT_KEY = "YOUR_CHATGPT_KEY"

def ask_gemini(question):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    data = {"contents": [{"parts": [{"text": question}]}]}
    response = requests.post(url, json=data)
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

def ask_claude(question):
    url = "https://api.anthropic.com/v1/messages"
    headers = {"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01"}
    data = {"model": "claude-3-sonnet-20240229", "max_tokens": 1024, "messages": [{"role": "user", "content": question}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["content"][0]["text"]

def ask_deepseek(question):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": question}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def ask_chatgpt(question):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {CHATGPT_KEY}"}
    data = {"model": "gpt-4", "messages": [{"role": "user", "content": question}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]