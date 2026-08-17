# QUOS University

**QUOS University** is a self-learning AI worker for deep reflection on habits, money psychology, and personal growth. Every five minutes it selects a question, asks **Gemini** for a rigorous teacher perspective, gives that perspective to a Gemini-powered **Dean**, saves the Dean’s original lesson to `training_data.jsonl`, and prints the result to the console.

> **QUOS principle:** One deep question. One Gemini perspective. One lesson worth keeping.

## Architecture

| Component | Responsibility |
| --- | --- |
| `main.py` | Generates the question, asks Gemini, runs the five-minute loop, writes status, saves lessons, and prints results. |
| `teachers.py` | Calls Gemini through the Gemini `generateContent` HTTP API. |
| `dean.py` | Sends the question and Gemini’s initial perspective back to Gemini for final synthesis. |
| `saver.py` | Appends the required `{"input": "question", "output": "final_answer"}` JSON object to `training_data.jsonl`. |
| `preview.py` | Serves a read-only QUOS-branded status page and health endpoint. |
| `service.py` | Runs the worker in a background thread while exposing the preview page, making a public web URL possible on Render. |

A cycle is written only after both Gemini calls and the Dean synthesis succeed. Failed cycles remain visible in status and logs and do not create partial training examples.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GEMINI_KEY to .env
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

| Variable | Purpose |
| --- | --- |
| `GEMINI_KEY` | Gemini API key used by the teacher and Dean. |
| `GEMINI_MODEL` | Optional Gemini model override; defaults to `gemini-3.7-flash`. |
| `LOOP_INTERVAL_SECONDS` | Loop interval; defaults to `300` seconds. |
| `HTTP_TIMEOUT_SECONDS` | HTTP timeout for Gemini requests. |
| `HTTP_MAX_RETRIES` | Number of retries after transient request failures. |
| `TRAINING_DATA_PATH` | JSONL output path. |
| `STATUS_PATH` | Worker status path. |
| `LOG_LEVEL` | Python logging level. |

Never commit a real `.env` file or API key.

## Data format

Each completed lesson is appended as one line to `training_data.jsonl`:

```json
{"input":"What hidden reward keeps a person repeating a habit they say they want to change, and how can they redesign that reward without relying on willpower?","output":"1. Core insight..."}
```

The file is JSONL rather than one large JSON array so new examples can be appended safely and consumed incrementally by later training or evaluation pipelines.

## Deploy on Render

The included `render.yaml` defines a Python web service that launches `service.py`. That process runs the QUOS Gemini-only worker continuously and exposes the branded preview at the service URL. This combined mode provides both the five-minute worker and the requested live preview.

1. Put this folder in a Git repository and push it to GitHub or GitLab.
2. In Render, create a new Blueprint and select the repository.
3. Render detects `render.yaml` and creates the `quos-university` service.
4. Add `GEMINI_KEY` when Render requests the unsynced secret.
5. Deploy and open the generated service URL. `/health` returns a machine-readable health response and `/api/status` returns the latest worker checkpoint.

The deployed QUOS preview is available at <https://quos-university.onrender.com>.

## Replit alternative

Create a Python Repl, upload the project files, add `GEMINI_KEY` through Replit Secrets, and run `python service.py`. Replit’s public web preview will show the QUOS status page. For continuous execution, use an always-on deployment option rather than a session that stops when the workspace is inactive.

## Safety and quality notes

The system produces educational content, not financial, medical, or legal advice. Review generated lessons before publishing them as formal curriculum. Keep the Gemini API key in server-side secret storage. Gemini model names are environment-configurable because provider availability can change over time.

## References

[1]: https://ai.google.dev/api/generate-content "Google Gemini API: Generate Content"
[2]: https://render.com/docs/blueprint-spec "Render Blueprint YAML Reference"
[3]: https://render.com/docs/free "Render Deploy for Free"
