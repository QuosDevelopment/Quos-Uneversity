"""Combined Render entrypoint: QUOS worker in a background thread plus preview HTTP server."""

from __future__ import annotations

import logging
import threading

from main import run_forever
from preview import app


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    worker = threading.Thread(target=run_forever, name="quos-worker", daemon=True)
    worker.start()
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
