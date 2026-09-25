"""
Starea botului, impartita intre broker_manager (conexiunea la
Tradovate) si dashboard.py (webhook + pagina web).
"""

import threading
from datetime import datetime, timezone


class BotState:
    def __init__(self):
        self._lock = threading.Lock()
        self.connected = False
        self.account_name = None
        self.last_update = None
        self.last_webhook_at = None
        self.trade_log = []  # listă de dict-uri, cele mai recente primele
        self.last_error = None

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.last_update = datetime.now(timezone.utc)

    def add_trade(self, entry):
        with self._lock:
            self.trade_log.insert(0, entry)
            self.trade_log = self.trade_log[:50]  # ține doar ultimele 50

    def snapshot(self):
        with self._lock:
            return {
                "connected": self.connected,
                "account_name": self.account_name,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "last_webhook_at": self.last_webhook_at.isoformat() if self.last_webhook_at else None,
                "trade_log": self.trade_log,
                "last_error": self.last_error,
            }


bot_state = BotState()
