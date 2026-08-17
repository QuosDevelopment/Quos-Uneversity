# QUOS University

**QUOS University** is a universal self-learning AI worker. Every 120 seconds it selects a question from a broad curriculum spanning computer science, mathematics, physics, history, geography, art, design, music, dance, food, nutrition, philosophy, ethics, biology, medicine, literature, language, sports, fitness, economics, finance, habits, money psychology, and personal growth. It asks **Groq** for a rigorous teacher perspective, gives that perspective to a Groq-powered **Dean**, saves the Dean’s original lesson to `training_data.jsonl`, and prints the result to the console.

> **QUOS principle:** One deep question. One Groq perspective. One lesson worth keeping.

## Architecture

| Component | Responsibility |
| --- | --- |
| `main.py` | Generates the question, asks Groq, runs the 120-second loop, writes status, saves lessons, and prints results. |
| `teachers.py` | Calls Groq through its OpenAI-compatible chat-completions API. |
| `dean.py` | Sends the question and Groq’s initial perspective back to Groq for final synthesis. |
| `saver.py` | Appends the required `{"input": "question", "output": "final_answer"}` JSON object to `training_data.jsonl`. |
| `preview.py` | Serves a read-only QUOS-branded status page and health endpoint. |
| `service.py` | Runs the worker in a background thread while exposing the preview page, making a public web URL possible on Render. |

A cycle is written only after both Groq calls and the Dean synthesis succeed. The worker waits three seconds after each Groq response to reduce burst pressure and rate-limit risk. Failed cycles remain visible in status and logs and do not create partial training examples.

## Curriculum

The question selector samples from twelve knowledge domains: **Computer Science & Programming; Mathematics; Physics; History & Geography; Art & Design; Music & Dance; Food & Nutrition; Philosophy & Ethics; Biology & Medicine; Literature & Language; Sports & Fitness; and Economics & Finance**. The original habits, money psychology, and personal growth questions remain in the bank so QUOS can connect technical, scientific, creative, cultural, health, and personal-development ideas in one training dataset.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
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
| `GROQ_API_KEY` | Groq API key used by the teacher and Dean. |
| `GROQ_MODEL` | Optional Groq model override; defaults to `openai/gpt-oss-120b`. |
| `LOOP_INTERVAL_SECONDS` | Loop interval; defaults to `120` seconds. |
| `RESPONSE_DELAY_SECONDS` | Delay after each Groq teacher and Dean response; defaults to `3` seconds. |
| `HTTP_TIMEOUT_SECONDS` | HTTP timeout for Groq requests. |
| `HTTP_MAX_RETRIES` | Number of retries after transient request failures. |
| `TRAINING_DATA_PATH` | JSONL output path. |
| `STATUS_PATH` | Worker status path. |
| `LOG_LEVEL` | Python logging level. |

Never commit a real `.env` file or API key.

## Data format

Each completed lesson is appended as one line to `training_data.jsonl`:

```json
{"input":"How should a Python programmer choose between a list, tuple, set, and dictionary when designing a data pipeline, and what trade-offs matter most?","output":"1. Core insight..."}
```

The file is JSONL rather than one large JSON array so new examples can be appended safely and consumed incrementally by later training or evaluation pipelines.

## Deploy on Render

The included `render.yaml` defines a Python web service that launches `service.py`. That process runs the QUOS Groq worker continuously and exposes the branded preview at the service URL. This combined mode provides both the 120-second worker and the requested live preview.

1. Put this folder in a Git repository and push it to GitHub or GitLab.
2. In Render, create a new Blueprint and select the repository.
3. Render detects `render.yaml` and creates the `quos-university` service.
4. Add `GROQ_API_KEY` when Render requests the unsynced secret.
5. Deploy and open the generated service URL. `/health` returns a machine-readable health response and `/api/status` returns the latest worker checkpoint.

The deployed QUOS preview is available at <https://quos-university.onrender.com>.

## Replit alternative

Create a Python Repl, upload the project files, add `GROQ_API_KEY` through Replit Secrets, and run `python service.py`. Replit’s public web preview will show the QUOS status page. For continuous execution, use an always-on deployment option rather than a session that stops when the workspace is inactive.

## Safety and quality notes

The system produces educational content, not financial, medical, or legal advice. Review generated lessons before publishing them as formal curriculum. Keep the Groq API key in server-side secret storage. Groq model names are environment-configurable because provider availability can change over time.

## References

[1]: https://console.groq.com/docs/openai "Groq OpenAI compatibility documentation"
[2]: https://console.groq.com/docs/models "Groq model documentation"
[3]: https://render.com/docs/blueprint-spec "Render Blueprint YAML Reference"
[4]: https://render.com/docs/free "Render Deploy for Free"
