# QUOS University

**QUOS University** is a self-learning AI worker for deep reflection on habits, money psychology, and personal growth. Every five minutes it selects a question, asks **Gemini, Claude, DeepSeek, and ChatGPT** in parallel, gives their responses to a Gemini-powered **Dean**, saves the Dean’s original lesson to `training_data.jsonl`, and prints the result to the console.

> **QUOS principle:** Four perspectives. One question. A lesson worth keeping.

## Architecture

| Component | Responsibility |
| --- | --- |
| `main.py` | Generates the question, coordinates the four teachers, runs the recurring loop, writes status, and prints lessons. |
| `teachers.py` | Calls Gemini, Claude, DeepSeek, and ChatGPT through their current HTTP APIs. |
| `dean.py` | Sends the question and all four answers to Gemini for synthesis. |
| `saver.py` | Appends the required `{"input": "question", "output": "final_answer"}` JSON object to `training_data.jsonl`. |
| `preview.py` | Serves a read-only QUOS-branded status page and health endpoint. |
| `service.py` | Runs the worker in a background thread while exposing the preview page, which makes a public web URL possible on Render. |

The teacher calls are concurrent, so a cycle does not wait for each provider serially. A cycle is written only after all four teacher answers and the Dean synthesis succeed. Failed cycles are logged and do not create partial training examples.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add the four provider keys to .env
python main.py --once
```

To run continuously:

```bash
python main.py
```

To run the branded preview separately:

```bash
python preview.py
```

Then open `http://localhost:8000`. The worker writes `status.json` and `training_data.jsonl` in the project directory by default.

## Environment variables

The required deployment secrets are:

| Variable | Purpose |
| --- | --- |
| `GEMINI_KEY` | Gemini API key for the Gemini teacher and Dean. |
| `CLAUDE_KEY` | Anthropic API key for Claude. |
| `DEEPSEEK_KEY` | DeepSeek API key. |
| `CHATGPT_KEY` | OpenAI API key for ChatGPT. |

Model names, timeout, retry count, loop interval, and storage paths are configurable in `.env`. Never commit a real `.env` file or provider key.

## Data format

Each completed lesson is appended as one line to `training_data.jsonl`:

```json
{"input":"What hidden reward keeps a person repeating a habit they say they want to change, and how can they redesign that reward without relying on willpower?","output":"1. Core insight..."}
```

The file is intentionally JSONL rather than one large JSON array so new examples can be appended safely and consumed incrementally by later training or evaluation pipelines.

## Deploy on Render

The included `render.yaml` defines a Python web service that launches `service.py`. That process runs the QUOS worker continuously and exposes the branded preview at the service URL. This combined mode is deliberate: a Render background-worker service has no public HTTP URL, while the combined service provides both the five-minute worker and the requested live preview.

1. Put this folder in a Git repository and push it to GitHub or GitLab.
2. In Render, create a new Blueprint and select the repository.
3. Render detects `render.yaml` and creates the `quos-university` service.
4. Add values for `GEMINI_KEY`, `CLAUDE_KEY`, `DEEPSEEK_KEY`, and `CHATGPT_KEY` when Render requests the unsynced secrets.
5. Deploy and open the generated `https://<service-name>.onrender.com` URL. `/health` returns a machine-readable health response and `/api/status` returns the latest worker checkpoint.

For strict separation, deploy `python main.py` as a Render Background Worker. That is the pure worker topology, but it will not have a browser preview URL; use logs and the persisted training file instead. Render’s official worker documentation describes background workers as long-running processes for asynchronous tasks [1]. Render’s free web services can spin down after inactivity, so use a paid always-on instance for dependable five-minute production execution [2].

## Replit alternative

Create a Python Repl, upload the project files, add the same four secrets through Replit Secrets, and run `python service.py`. Replit’s public web preview will show the QUOS status page. For continuous execution, use an always-on deployment option rather than a session that stops when the workspace is inactive.

## Safety and quality notes

The system produces educational content, not financial, medical, or legal advice. Review generated lessons before publishing them as formal curriculum. Keep all API keys in server-side secret storage. Provider model names are environment-configurable because vendors change model availability over time.

## References

[1]: https://render.com/docs/background-workers "Render Background Workers"
[2]: https://render.com/docs/free "Render Deploy for Free"
[3]: https://ai.google.dev/api/generate-content "Google Gemini API: Generate Content"
[4]: https://platform.claude.com/docs/en/api/sdks/python "Anthropic Python SDK"
[5]: https://api-docs.deepseek.com/ "DeepSeek API Documentation"
[6]: https://render.com/docs/blueprint-spec "Render Blueprint YAML Reference"
