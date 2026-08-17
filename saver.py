"""Training-data persistence for QUOS University."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


DATA_PATH = Path(os.getenv("TRAINING_DATA_PATH", "training_data.jsonl"))


def save_training_example(question: str, final_answer: str, path: Path | None = None) -> None:
    """Append one JSONL record, creating parent directories when necessary."""
    target = path or DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"input": question, "output": final_answer}
    line = json.dumps(record, ensure_ascii=False) + "\n"

    # Append is sufficient for a single worker. The lock file makes accidental
    # concurrent writers safer on platforms that support advisory locking.
    with target.open("a", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass


def ensure_data_file(path: Path | None = None) -> Path:
    """Create an empty training file if none exists and return its path."""
    target = path or DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch(exist_ok=True)
    return target
