"""
Dashboard web, optimizat pentru telefon. Ruleaza in acelasi proces cu
botul (vezi app.py) si doar citeste din state.bot_state.
"""

from flask import Flask, jsonify, render_template_string
from state import bot_state

app = Flask(__name__)

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
    <div class="row"><span class="label">Status conexiune</span>
      <span class="value" id="connStatus">-</span></div>
    <div class="row"><span class="label">Cont</span><span class="value" id="account">-</span></div>
    <div class="row"><span class="label">Direcție configurată</span><span class="value" id="direction">-</span></div>
    <div class="row"><span class="label">Ultimul preț</span><span class="value" id="lastPrice">-</span></div>
  </div>

  <div class="card">
    <div class="row"><span class="label">Range High</span><span class="value" id="rangeHigh">-</span></div>
    <div class="row"><span class="label">Range Low</span><span class="value" id="rangeLow">-</span></div>
    <div class="row"><span class="label">Range gata</span><span class="value" id="rangeReady">-</span></div>
    <div class="row"><span class="label">Tranzacționat azi</span><span class="value" id="tradedToday">-</span></div>
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
    document.getElementById('direction').textContent = d.direction || '-';
    document.getElementById('lastPrice').textContent = d.last_price ?? '-';
    document.getElementById('rangeHigh').textContent = d.range_high ?? '-';
    document.getElementById('rangeLow').textContent = d.range_low ?? '-';
    document.getElementById('rangeReady').textContent = d.range_ready ? 'Da' : 'Nu';
    document.getElementById('tradedToday').textContent = d.traded_today ? 'Da' : 'Nu';

    const log = document.getElementById('tradeLog');
    if (d.trade_log && d.trade_log.length) {
      log.innerHTML = d.trade_log.map(t => `
        <div class="trade ${t.direction === 'SHORT' ? 'short' : 'long'}">
          <b>${t.direction}</b> @ ${t.entry_price} &middot; SL ${t.stop_loss} / TP ${t.take_profit}
          <div style="color:#999; font-size:0.8rem;">${new Date(t.ts).toLocaleString('ro-RO')}</div>
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
