"""
Punct de intrare pentru gazduire (Railway).
Porneste conexiunea la broker intr-un thread de fundal, si serverul
web (webhook + dashboard) in thread-ul principal.
"""

import os
import threading

from broker_manager import run_connection_loop
from dashboard import app

if __name__ == "__main__":
    conn_thread = threading.Thread(target=run_connection_loop, daemon=True)
    conn_thread.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
