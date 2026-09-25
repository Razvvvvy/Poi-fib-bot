"""
Integrare cu Tradovate (broker cu API public documentat).

IMPORTANT:
- Testeaza intai pe mediul DEMO (demo.tradovateapi.com), NU pe live,
  pana esti sigur ca botul se comporta exact cum trebuie.
- Ai nevoie de un cont Tradovate + API key (cid/sec), generate din
  contul tau Tradovate (Settings -> API Access).
- Acest fisier e izolat de restul botului: cand primesti documentatia
  Tradesea, faci un fisier broker_tradesea.py cu aceeasi interfata
  (authenticate / place_market_order / place_stop / place_limit) si
  il folosesti in loc de asta in main.py, fara sa modifici strategia.
"""

import os
import time
import requests
from dataclasses import dataclass


@dataclass
class TradovateCredentials:
    username: str
    password: str
    app_id: str
    app_version: str
    cid: str
    sec: str
    demo: bool = True


class TradovateBroker:
    def __init__(self, creds: TradovateCredentials):
        self.creds = creds
        self.base_url = (
            "https://demo.tradovateapi.com/v1" if creds.demo else "https://live.tradovateapi.com/v1"
        )
        self.access_token = None
        self.account_id = None
        self.account_spec = None

    # ---------------------------------------------------------------
    def authenticate(self):
        url = f"{self.base_url}/auth/accesstokenrequest"
        payload = {
            "name": self.creds.username,
            "password": self.creds.password,
            "appId": self.creds.app_id,
            "appVersion": self.creds.app_version,
            "cid": self.creds.cid,
            "sec": self.creds.sec,
        }
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "accessToken" not in data:
            raise RuntimeError(f"Autentificare esuata la Tradovate: {data}")
        self.access_token = data["accessToken"]
        return data

    def _headers(self):
        if not self.access_token:
            raise RuntimeError("Nu esti autentificat. Cheama authenticate() intai.")
        return {"Authorization": f"Bearer {self.access_token}"}

    # ---------------------------------------------------------------
    def load_account(self):
        """Ia primul cont disponibil pe user-ul autentificat.
        Daca ai mai multe conturi (evaluare + finantat etc.), ajusteaza
        aici sa selectezi contul corect dupa nume."""
        url = f"{self.base_url}/account/list"
        resp = requests.get(url, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        accounts = resp.json()
        if not accounts:
            raise RuntimeError("Niciun cont Tradovate gasit pe acest user.")
        self.account_id = accounts[0]["id"]
        self.account_spec = accounts[0]["name"]
        return accounts[0]

    # ---------------------------------------------------------------
    def place_market_order(self, symbol: str, action: str, qty: int):
        """action: 'Buy' sau 'Sell'"""
        url = f"{self.base_url}/order/placeorder"
        payload = {
            "accountSpec": self.account_spec,
            "accountId": self.account_id,
            "action": action,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": "Market",
            "isAutomated": True,
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def place_stop_order(self, symbol: str, action: str, qty: int, stop_price: float):
        url = f"{self.base_url}/order/placeorder"
        payload = {
            "accountSpec": self.account_spec,
            "accountId": self.account_id,
            "action": action,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": "Stop",
            "stopPrice": stop_price,
            "isAutomated": True,
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def place_limit_order(self, symbol: str, action: str, qty: int, limit_price: float):
        url = f"{self.base_url}/order/placeorder"
        payload = {
            "accountSpec": self.account_spec,
            "accountId": self.account_id,
            "action": action,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": "Limit",
            "price": limit_price,
            "isAutomated": True,
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ---------------------------------------------------------------
    def get_recent_bars(self, symbol: str, unit_seconds: int, count: int):
        """Foloseste endpoint-ul de chart al Tradovate pentru bare istorice.
        Verifica in documentatia curenta Tradovate numele exact al
        endpoint-ului de market data pentru contul tau (poate necesita
        Data Subscription activa)."""
        url = f"{self.base_url}/md/getchart"
        payload = {
            "symbol": symbol,
            "chartDescription": {
                "underlyingType": "Tick" if unit_seconds < 60 else "MinuteBar",
                "elementSize": unit_seconds if unit_seconds < 60 else unit_seconds // 60,
                "elementSizeUnit": "Second" if unit_seconds < 60 else "Minute",
                "withHistogram": False,
            },
            "timeRange": {"asMuchAsElements": count},
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()


def credentials_from_env() -> TradovateCredentials:
    return TradovateCredentials(
        username=os.environ["TRADOVATE_USERNAME"],
        password=os.environ["TRADOVATE_PASSWORD"],
        app_id=os.environ.get("TRADOVATE_APP_ID", "MyTradingBot"),
        app_version=os.environ.get("TRADOVATE_APP_VERSION", "1.0"),
        cid=os.environ["TRADOVATE_CID"],
        sec=os.environ["TRADOVATE_SEC"],
        demo=os.environ.get("TRADOVATE_DEMO", "true").lower() == "true",
    )
