"""
SCHELET pentru integrarea cu Tradesea -- NEFUNCTIONAL inca.

Cand primesti documentatia API de la Tradesea, trimite-mi:
  - URL-ul endpoint-ului (autentificare + plasare ordine)
  - metoda de autentificare (API key / token / user-parola)
  - formatul exact al payload-ului pentru un ordin (market, stop, limit)

...si completez metodele de mai jos ca sa aiba exact aceeasi interfata
ca broker_tradovate.py. Odata facut asta, in main.py schimbi o singura
linie (care broker se instantiaza) si tot restul botului (strategia,
gestiunea SL/TP, loop-ul) ramane neschimbat.
"""


class TradeseaBroker:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Integrarea Tradesea nu e completa inca. "
            "Trimite documentatia API primita de la suport si o implementez."
        )

    def authenticate(self):
        raise NotImplementedError

    def place_market_order(self, symbol: str, action: str, qty: int):
        raise NotImplementedError

    def place_stop_order(self, symbol: str, action: str, qty: int, stop_price: float):
        raise NotImplementedError

    def place_limit_order(self, symbol: str, action: str, qty: int, limit_price: float):
        raise NotImplementedError

    def get_recent_bars(self, symbol: str, unit_seconds: int, count: int):
        raise NotImplementedError
