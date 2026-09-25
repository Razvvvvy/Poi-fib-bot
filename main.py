"""
Bucla de trading. Ruleaza intr-un thread de fundal, separat de
serverul web (dashboard.py), si actualizeaza state.bot_state dupa
fiecare verificare, ca dashboard-ul sa aiba mereu date proaspete.
"""

import time as time_module
from datetime import datetime, timezone

from strategy import RangeFibStrategy, StrategyConfig, Bar
from broker_tradovate import TradovateBroker, credentials_from_env
from state import bot_state

# =====================================================================
# CONFIGURARE -- ajusteaza aici
# =====================================================================
SYMBOL = "MESZ6"          # simbolul exact la Tradovate, verifica-l in platforma
QTY = 1
POLL_SECONDS = 15         # cat de des verificam bare noi (timeframe-ul de executie)
BAR_SIZE_SECONDS = 15     # dimensiunea barei folosite pentru semnal

strategy_config = StrategyConfig(
    direction="SHORT",           # SHORT sau LONG -- schimbi manual pana clarificam regula automata
    stop_loss_points=300.0,
    take_profit_mult=5.0,
    use_circle_filter=True,
)


def run_trading_loop():
    bot_state.update(direction=strategy_config.direction)

    try:
        creds = credentials_from_env()
        broker = TradovateBroker(creds)
        broker.authenticate()
        broker.load_account()
        bot_state.update(connected=True, account_name=broker.account_spec, last_error=None)
        print(f"Conectat la Tradovate, cont: {broker.account_spec}")
    except Exception as e:
        bot_state.update(connected=False, last_error=str(e))
        print(f"Nu m-am putut conecta la Tradovate: {e}")
        return

    strat = RangeFibStrategy(strategy_config)
    last_bar_ts = None

    while True:
        try:
            chart_data = broker.get_recent_bars(SYMBOL, BAR_SIZE_SECONDS, 1)
            bars = chart_data.get("bars", [])

            if bars:
                latest = bars[-1]
                bar_ts = datetime.fromisoformat(latest["timestamp"]).astimezone(timezone.utc)

                bot_state.update(
                    connected=True,
                    last_price=latest["close"],
                    range_high=strat.range_high,
                    range_low=strat.range_low,
                    range_ready=strat.range_ready,
                    traded_today=strat.traded_today,
                    last_error=None,
                )

                if bar_ts != last_bar_ts:
                    last_bar_ts = bar_ts
                    bar = Bar(
                        ts=bar_ts,
                        open=latest["open"],
                        high=latest["high"],
                        low=latest["low"],
                        close=latest["close"],
                    )
                    signal = strat.on_bar(bar)

                    if signal:
                        print(f"[{signal.ts}] SEMNAL {signal.direction} @ {signal.entry_price} "
                              f"SL={signal.stop_loss} TP={signal.take_profit}")

                        action = "Sell" if signal.direction == "SHORT" else "Buy"
                        opposite = "Buy" if signal.direction == "SHORT" else "Sell"

                        broker.place_market_order(SYMBOL, action, QTY)
                        broker.place_stop_order(SYMBOL, opposite, QTY, signal.stop_loss)
                        broker.place_limit_order(SYMBOL, opposite, QTY, signal.take_profit)

                        bot_state.add_trade({
                            "ts": signal.ts.isoformat(),
                            "direction": signal.direction,
                            "entry_price": signal.entry_price,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                        })
                        bot_state.update(traded_today=True)

        except Exception as e:
            bot_state.update(connected=False, last_error=str(e))
            print(f"Eroare in bucla principala: {e}")

        time_module.sleep(POLL_SECONDS)
