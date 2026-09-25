"""
Punct de intrare pentru gazduire (Railway, Render etc.).
Porneste bucla de trading intr-un thread de fundal, si serverul web
(dashboard-ul) in thread-ul principal.
"""

import os
import threading

from main import run_trading_loop
from dashboard import app

if __name__ == "__main__":
    trading_thread = threading.Thread(target=run_trading_loop, daemon=True)
    trading_thread.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
