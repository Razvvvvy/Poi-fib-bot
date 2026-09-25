"""
Server web cu doua roluri:
1. /webhook -- primeste alerta de la TradingView (Pine Script), verifica
   codul secret, si plaseaza ordinul la Tradovate (Market + Stop + Limit).
2. / -- dashboard mobil-friendly, ca sa vezi ce a facut botul.

Codul secret trebuie sa fie IDENTIC in doua locuri:
- in setarile strategiei din TradingView (input-ul "Cod secret webhook")
- in variabila de mediu WEBHOOK_SECRET, pe Railway
"""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string, request

from state import bot_state
from broker_manager import get_broker

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "SCHIMBA-MA")
QTY = int(os.environ.get("TRADE_QTY", "1"))


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "payload invalid sau lipsă"}), 400

    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "cod secret greșit"}), 403

    direction = data.get("direction")
    symbol = data.get("symbol")
    entry = data.get("entry")
    sl = data.get("sl")
    tp = data.get("tp")

    if direction not in ("SHORT", "LONG") or not symbol or sl is None or tp is None:
        return jsonify({"error": "câmpuri lipsă în payload"}), 400

    bot_state.update(last_webhook_at=datetime.now(timezone.utc))

    broker = get_broker()
    if broker is None:
        bot_state.add_trade({
            "ts": datetime.now(timezone.utc).isoformat(),
            "direction": direction, "entry_price": entry, "stop_loss": sl,
            "take_profit": tp, "status": "EȘUAT - bot neconectat la broker",
        })
        return jsonify({"error": "botul nu e conectat la broker în acest moment"}), 503

    action = "Sell" if direction == "SHORT" else "Buy"
    opposite = "Buy" if direction == "SHORT" else "Sell"

    try:
        broker.place_market_order(symbol, action, QTY)
        broker.place_stop_order(symbol, opposite, QTY, sl)
        broker.place_limit_order(symbol, opposite, QTY, tp)
        status = "EXECUTAT"
    except Exception as e:
        status = f"EROARE: {e}"

    bot_state.add_trade({
        "ts": datetime.now(timezone.utc).isoformat(),
        "direction": direction, "entry_price": entry, "stop_loss": sl,
        "take_profit": tp, "status": status,
    })

    return jsonify({"status": status})


PAGE = """
<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>POI Range Fib Bot</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 16px;
         background: #0f1115; color: #eaeaea; }
  h1 { font-size: 1.2rem; margin-bottom: 4px; }
  .sub { color: #999; font-size: 0.85rem; margin-bottom: 20px; }
  .card { background: #1a1d24; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
  .row { display: flex; justify-content: space-between; padding: 6px 0;
         border-bottom: 1px solid #2a2d35; font-size: 0.95rem; }
  .row:last-child { border-bottom: none; }
  .label { color: #999; }
  .value { font-weight: 600; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
  .green { background: #3ecf6d; } .red { background: #ef4444; } .gray { background: #6b7280; }
  .trade { padding: 10px; border-radius: 8px; background: #22262f; margin-bottom: 8px; font-size: 0.9rem; }
  .short { border-left: 3px solid #ef4444; } .long { border-left: 3px solid #3ecf6d; }
  .empty { color: #777; text-align: center; padding: 20px; font-size: 0.9rem; }
</style>
</head>
<body>
  <h1>POI Range Fib Bot</h1>
  <div class="sub" id="lastUpdate">se încarcă...</div>

  <div class="card">
    <div class="row"><span class="label">Status conexiune broker</span>
      <span class="value" id="connStatus">-</span></div>
    <div class="row"><span class="label">Cont</span><span class="value" id="account">-</span></div>
    <div class="row"><span class="label">Ultimul webhook primit</span><span class="value" id="lastWebhook">-</span></div>
  </div>

  <h2 style="font-size:1rem; margin-top:20px;">Istoric tranzacții</h2>
  <div id="tradeLog"><div class="empty">Niciun semnal încă</div></div>

<script>
async function refresh() {
  try {
    const res = await fetch('/api/status');
    const d = await res.json();

    document.getElementById('lastUpdate').textContent = d.last_update
      ? 'Actualizat: ' + new Date(d.last_update).toLocaleTimeString('ro-RO')
      : 'Fără date încă';

    const dot = d.connected ? '<span class="dot green"></span>Conectat'
                             : '<span class="dot red"></span>Deconectat';
    document.getElementById('connStatus').innerHTML = dot;
    document.getElementById('account').textContent = d.account_name || '-';
    document.getElementById('lastWebhook').textContent = d.last_webhook_at
      ? new Date(d.last_webhook_at).toLocaleString('ro-RO') : 'Niciunul încă';

    const log = document.getElementById('tradeLog');
    if (d.trade_log && d.trade_log.length) {
      log.innerHTML = d.trade_log.map(t => `
        <div class="trade ${t.direction === 'SHORT' ? 'short' : 'long'}">
          <b>${t.direction}</b> @ ${t.entry_price} &middot; SL ${t.stop_loss} / TP ${t.take_profit}
          <div style="color:#999; font-size:0.8rem;">${t.status || ''} &middot; ${new Date(t.ts).toLocaleString('ro-RO')}</div>
        </div>`).join('');
    } else {
      log.innerHTML = '<div class="empty">Niciun semnal încă</div>';
    }
  } catch (e) {
    document.getElementById('lastUpdate').textContent = 'Eroare la actualizare';
  }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    return render_template_string(PAGE)


@app.route("/api/status")
def api_status():
    return jsonify(bot_state.snapshot())


@app.route("/health")
def health():
    return "ok"
