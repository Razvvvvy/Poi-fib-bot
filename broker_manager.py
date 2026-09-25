"""
Gestioneaza conexiunea la broker (Tradovate). Se autentifica la
pornire si tine un singur obiect broker, folosit de webhook-ul din
dashboard.py cand vine un semnal de la TradingView.

Tradovate cere reautentificare periodica (token-ul expira) -- de-aia
avem o bucla de fundal care reface autentificarea la interval regulat,
ca botul sa fie mereu gata sa primeasca un webhook.
"""

import threading
import time as time_module

from broker_tradovate import TradovateBroker, credentials_from_env
from state import bot_state

REAUTH_SECONDS = 60 * 60  # reautentificare orara (tokenul Tradovate expira la ~80 min)

_broker_lock = threading.Lock()
_broker = None


def get_broker():
    with _broker_lock:
        return _broker


def _connect():
    global _broker
    try:
        creds = credentials_from_env()
        broker = TradovateBroker(creds)
        broker.authenticate()
        broker.load_account()
        with _broker_lock:
            _broker = broker
        bot_state.update(connected=True, account_name=broker.account_spec, last_error=None)
        print(f"Conectat la Tradovate, cont: {broker.account_spec}")
    except Exception as e:
        bot_state.update(connected=False, last_error=str(e))
        print(f"Nu m-am putut conecta la Tradovate: {e}")


def run_connection_loop():
    """Ruleaza intr-un thread de fundal: conecteaza la pornire, apoi
    reautentifica periodic."""
    _connect()
    while True:
        time_module.sleep(REAUTH_SECONDS)
        _connect()
