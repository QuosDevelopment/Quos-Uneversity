"""Small QUOS-branded read-only preview server.

This is optional and intended for local inspection or a separate web service.
"""

from __future__ import annotations

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
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "unknown", "message": "Status file is temporarily unavailable."}


def _recent_records(limit: int = 5) -> list[dict]:
    if not DATA_PATH.exists():
        return []
    records: list[dict] = []
    for line in DATA_PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


@app.get("/health")
def health() -> Response:
    return jsonify({"ok": True, "service": "quos-university-preview", "worker": _read_status().get("state")})


@app.get("/api/status")
def api_status() -> Response:
    return jsonify(_read_status())


@app.get("/")
def index() -> str:
    status = _read_status()
    records = _recent_records()
    last_answer = status.get("last_answer", "No lesson has been completed yet.")
    escaped = (
        last_answer.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    cards = "".join(
        f"<article><h3>Lesson {len(records) - i}</h3><p><strong>Question:</strong> {item.get('input', '')}</p><p>{item.get('output', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')[:900]}</p></article>"
        for i, item in enumerate(reversed(records))
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QUOS University</title><style>
:root {{ color-scheme: dark; --ink:#f5f2e9; --muted:#a6b0bb; --gold:#d4a84f; --bg:#10161d; --card:#18222c; }}
* {{ box-sizing:border-box }} body {{ margin:0; font-family:Inter,system-ui,sans-serif; background:radial-gradient(circle at top right,#253847 0,#10161d 48%); color:var(--ink); }}
main {{ width:min(980px,92vw); margin:0 auto; padding:64px 0 72px }} .eyebrow {{ color:var(--gold); letter-spacing:.18em; text-transform:uppercase; font-size:.78rem; font-weight:700 }}
h1 {{ font-family:Georgia,serif; font-weight:500; font-size:clamp(3rem,8vw,6rem); line-height:.95; margin:14px 0 22px }} .lede {{ color:var(--muted); font-size:1.1rem; max-width:650px; line-height:1.6 }}
.status {{ margin:36px 0; padding:24px; border:1px solid #31414e; background:#13202a; border-radius:18px; display:grid; gap:8px }} .status b {{ color:var(--gold) }}
.lesson, article {{ padding:28px; border-radius:18px; background:rgba(24,34,44,.88); border:1px solid #2b3a47; margin-top:18px; line-height:1.7 }} .lesson h2, article h3 {{ font-family:Georgia,serif; font-weight:500; color:var(--gold); margin-top:0 }} article p {{ color:#dbe3e9 }}
footer {{ color:var(--muted); margin-top:46px; font-size:.9rem }}
</style></head><body><main><div class="eyebrow">QUOS University · Self-Learning AI</div><h1>Think deeper.<br>Live wiser.</h1><p class="lede">Groq explores one deep question every 2 minutes. A Dean AI sharpens the response into a clear lesson across science, technology, arts, culture, health, and human understanding.</p>
<div class="status"><div>Worker state: <b>{status.get('state','unknown')}</b></div><div>Last update: {status.get('updated_at','—')}</div><div>Completed lessons: {len(records)}</div></div>
<section class="lesson"><h2>Latest Dean’s Lesson</h2><div>{escaped}</div></section><section><h2 style="font-family:Georgia,serif;font-weight:500;margin-top:48px">Recent curriculum</h2>{cards or '<p class="lede">The first lesson is being prepared.</p>'}</section><footer>QUOS University is an experimental self-learning system. Keep API credentials server-side and review generated content before using it in formal training.</footer></main></body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
