"""QUOS University live preview and lesson-history dashboard."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

from flask import Flask, Response, jsonify


app = Flask(__name__)
STATUS_PATH = Path(os.getenv("STATUS_PATH", "status.json"))
DATA_PATH = Path(os.getenv("TRAINING_DATA_PATH", "training_data.jsonl"))


def _read_status() -> dict:
    if not STATUS_PATH.exists():
        return {"state": "starting", "message": "Worker has not written a status checkpoint yet."}
    try:
        value = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"state": "unknown", "message": "Status is not an object."}
    except (OSError, ValueError):
        return {"state": "unknown", "message": "Status file is temporarily unavailable."}


def _read_records() -> list[dict]:
    """Read every valid JSONL lesson in chronological order."""
    if not DATA_PATH.exists():
        return []
    records: list[dict] = []
    try:
        lines = DATA_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _safe(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _lesson_card(number: int, item: dict, *, open_card: bool = False) -> str:
    question = _safe(item.get("input", "Untitled question"))
    answer = _safe(item.get("output", "No answer recorded."))
    opened = " open" if open_card else ""
    return (
        f'<details class="lesson"{opened}>'
        f'<summary><span class="lesson-number">Lesson {number}</span>'
        f'<span class="question-preview">{question}</span></summary>'
        f'<div class="lesson-body"><div class="label">Question</div><p class="question">{question}</p>'
        f'<div class="label">Answer</div><div class="answer">{answer}</div></div></details>'
    )


@app.get("/health")
def health() -> Response:
    return jsonify({"ok": True, "service": "quos-university-preview", "worker": _read_status().get("state")})


@app.get("/api/status")
def api_status() -> Response:
    status = _read_status()
    status["completed_lessons"] = len(_read_records())
    return jsonify(status)


@app.get("/api/history")
def api_history() -> Response:
    records = _read_records()
    return jsonify({"count": len(records), "records": records})


@app.get("/")
def index() -> str:
    status = _read_status()
    records = _read_records()
    latest_answer = status.get("last_answer", "No lesson has been completed yet.")
    latest_question = status.get("question", "Waiting for the first question.")
    teachers = ", ".join(status.get("teachers_completed", [])) or "—"
    errors = status.get("provider_errors", {})
    error_note = ""
    if errors:
        error_note = (
            '<div class="notice"><strong>Provider notes:</strong> '
            f'{_safe("; ".join(f"{name}: {message}" for name, message in errors.items()))}</div>'
        )

    history_cards = "".join(
        _lesson_card(len(records) - index, item, open_card=index == 0)
        for index, item in enumerate(reversed(records))
    )
    if not history_cards:
        history_cards = '<p class="muted">No saved lessons yet. The worker is preparing the first cycle.</p>'

    latest_html = (
        f'<div class="label">Question</div><p class="question">{_safe(latest_question)}</p>'
        f'<div class="label">Dean answer</div><div class="answer">{_safe(latest_answer)}</div>'
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QUOS University · Lesson History</title><style>
:root {{ color-scheme: dark; --ink:#f5f2e9; --muted:#a6b0bb; --gold:#d4a84f; --bg:#10161d; --card:#18222c; --line:#2b3a47; --accent:#9ed4c8; }}
* {{ box-sizing:border-box }} body {{ margin:0; font-family:Inter,system-ui,sans-serif; background:radial-gradient(circle at top right,#253847 0,#10161d 52%); color:var(--ink); }}
main {{ width:min(1080px,92vw); margin:0 auto; padding:56px 0 72px }} .eyebrow {{ color:var(--gold); letter-spacing:.18em; text-transform:uppercase; font-size:.78rem; font-weight:700 }}
h1 {{ font-family:Georgia,serif; font-weight:500; font-size:clamp(3rem,8vw,6rem); line-height:.95; margin:14px 0 22px }} .lede {{ color:var(--muted); font-size:1.1rem; max-width:760px; line-height:1.6 }}
.status-grid {{ margin:36px 0 22px; display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px }}
.stat {{ padding:20px; border:1px solid var(--line); background:#13202a; border-radius:16px }} .stat .value {{ display:block; color:var(--gold); font-family:Georgia,serif; font-size:1.55rem; margin-top:7px; overflow-wrap:anywhere }}
.label {{ color:var(--gold); font-size:.74rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin-top:8px }}
.panel {{ padding:28px; border-radius:18px; background:rgba(24,34,44,.9); border:1px solid var(--line); margin-top:18px; line-height:1.7 }} .panel h2 {{ font-family:Georgia,serif; font-weight:500; color:var(--gold); margin-top:0 }}
.question {{ color:var(--accent); font-size:1.08rem; line-height:1.65 }} .answer {{ color:#dbe3e9; white-space:pre-wrap; line-height:1.75; }}
.notice {{ margin-top:18px; padding:14px 16px; border-left:3px solid var(--gold); background:#241f16; color:#dfd3b6; overflow-wrap:anywhere }}
.history {{ margin-top:46px }} .history h2 {{ font-family:Georgia,serif; font-weight:500; color:var(--gold) }}
.lesson {{ margin-top:12px; border:1px solid var(--line); background:rgba(24,34,44,.84); border-radius:14px; overflow:hidden }}
.lesson summary {{ cursor:pointer; list-style:none; display:flex; gap:16px; align-items:baseline; padding:18px 20px; }} .lesson summary::-webkit-details-marker {{ display:none }}
.lesson summary::before {{ content:'＋'; color:var(--gold); font-size:1.1rem }} .lesson[open] summary::before {{ content:'−' }}
.lesson-number {{ color:var(--gold); font-weight:700; white-space:nowrap }} .question-preview {{ color:#dbe3e9; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }}
.lesson-body {{ padding:0 24px 26px 58px; border-top:1px solid var(--line); }} .lesson-body .label:first-child {{ margin-top:22px }}
.muted, footer {{ color:var(--muted) }} footer {{ margin-top:46px; font-size:.9rem; line-height:1.6 }} a {{ color:var(--accent) }}
@media (max-width:600px) {{ main {{ padding-top:36px }} .lesson summary {{ align-items:flex-start }} .question-preview {{ white-space:normal }} .lesson-body {{ padding-left:24px }} }}
</style></head><body><main>
<div class="eyebrow">QUOS University · Self-Learning AI</div>
<h1>Think deeper.<br>Keep the lessons.</h1>
<p class="lede">DeepSeek and Groq explore questions across computer science, mathematics, physics, history, arts, culture, health, finance, and human understanding. Available teacher perspectives are synthesized into lessons and preserved here as a growing training archive.</p>
<div class="status-grid"><div class="stat">Saved lessons<span class="value">{len(records)}</span></div><div class="stat">Worker state<span class="value">{_safe(status.get('state', 'unknown'))}</span></div><div class="stat">Teachers completed<span class="value">{_safe(teachers)}</span></div><div class="stat">Loop interval<span class="value">{_safe(status.get('interval_seconds', 120))} seconds</span></div></div>
{error_note}
<section class="panel"><h2>Latest Dean's Lesson</h2>{latest_html}</section>
<section class="history"><h2>Complete lesson history <span class="muted">({len(records)} total)</span></h2>{history_cards}</section>
<footer>QUOS University is an experimental self-learning system. <a href="/api/history">Download the full history as JSON</a> · <a href="/api/status">View live status</a>. Review generated content before using it in formal training.</footer>
</main></body></html>'''


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
