"""
Starea botului, impartita intre bucla de trading (thread de fundal) si
dashboard-ul web (care doar citeste starea ca sa o afiseze).
"""

import threading
from datetime import datetime, timezone


class BotState:
    def __init__(self):
        self._lock = threading.Lock()
        self.connected = False
        self.account_name = None
        self.last_update = None
        self.range_high = None
        self.range_low = None
        self.range_ready = False
        self.traded_today = False
        self.direction = None
        self.last_price = None
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
                "range_high": self.range_high,
                "range_low": self.range_low,
                "range_ready": self.range_ready,
                "traded_today": self.traded_today,
                "direction": self.direction,
                "last_price": self.last_price,
                "trade_log": self.trade_log,
                "last_error": self.last_error,
            }


bot_state = BotState()
