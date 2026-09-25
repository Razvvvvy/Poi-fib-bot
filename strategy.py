"""
Logica strategiei (indiferent de broker):
- calculeaza range-ul (highest high / lowest low) din fereastra 06:00-09:00
- calculeaza zonele Fibonacci orizontale (0, 0.5, 1)
- calculeaza banda "gri" a cercului Fibonacci (0.5R - 1.0R de la ancora)
- decide daca un bar (OHLC) declanseaza o intrare, in functie de directia
  aleasa manual (SHORT / LONG)

Nu stie nimic despre broker sau despre cum ajung datele -- primeste bare
OHLC cu timestamp si returneaza semnale. Asta il face usor de testat
(backtest) si usor de conectat la orice sursa de date / broker.
"""

from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from typing import Optional, Literal


@dataclass
class Bar:
    ts: datetime  # timezone-aware, in fusul orar al sesiunii
    open: float
    high: float
    low: float
    close: float


@dataclass
class StrategyConfig:
    tz_name: str = "America/New_York"
    range_start: dtime = dtime(9, 0)
    range_end: dtime = dtime(12, 0)
    trade_start: dtime = dtime(13, 30)
    trade_end: dtime = dtime(16, 45)
    direction: Literal["SHORT", "LONG"] = "SHORT"
    stop_loss_points: float = 300.0
    take_profit_mult: float = 5.0
    use_circle_filter: bool = True


@dataclass
class Signal:
    ts: datetime
    direction: Literal["SHORT", "LONG"]
    entry_price: float
    stop_loss: float
    take_profit: float
    range_high: float
    range_low: float


class RangeFibStrategy:
    def __init__(self, config: StrategyConfig):
        self.cfg = config
        self.tz = ZoneInfo(config.tz_name)

        self._current_day: Optional[datetime.date] = None
        self.range_high: Optional[float] = None
        self.range_low: Optional[float] = None
        self.range_high_ts: Optional[datetime] = None
        self.range_low_ts: Optional[datetime] = None
        self.range_ready: bool = False
        self.traded_today: bool = False

    # ---------------------------------------------------------------
    def _local(self, bar: Bar) -> datetime:
        return bar.ts.astimezone(self.tz)

    def _in_window(self, t: dtime, start: dtime, end: dtime) -> bool:
        return start <= t <= end

    def _reset_for_new_day(self, day):
        self._current_day = day
        self.range_high = None
        self.range_low = None
        self.range_high_ts = None
        self.range_low_ts = None
        self.range_ready = False
        self.traded_today = False

    # ---------------------------------------------------------------
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """Proceseaza un bar nou. Returneaza un Signal daca s-a declansat
        o intrare pe bar-ul asta, altfel None. Se poate apela cu bare de
        orice timeframe (recomandat: acelasi timeframe pe care vrei
        executia, ex. 15s), pentru ca range-ul e calculat din wick-uri
        (high/low) care sunt aceleasi indiferent de rezolutia datelor."""

        local_ts = self._local(bar)
        day = local_ts.date()
        t = local_ts.time()

        if day != self._current_day:
            self._reset_for_new_day(day)

        in_range_window = self._in_window(t, self.cfg.range_start, self.cfg.range_end)
        in_trade_window = self._in_window(t, self.cfg.trade_start, self.cfg.trade_end)

        # 1) actualizeaza range-ul cat timp suntem in fereastra 6:00-9:00
        if in_range_window:
            if self.range_high is None or bar.high > self.range_high:
                self.range_high = bar.high
                self.range_high_ts = local_ts
            if self.range_low is None or bar.low < self.range_low:
                self.range_low = bar.low
                self.range_low_ts = local_ts

        # 2) blocheaza range-ul prima data cand iesim din fereastra
        if not in_range_window and self.range_high is not None and not self.range_ready:
            self.range_ready = True

        if not self.range_ready or self.traded_today or not in_trade_window:
            return None

        # 3) niveluri fibonacci orizontale
        level0 = self.range_low
        level1 = self.range_high
        level05 = (level0 + level1) / 2
        rng = level1 - level0
        if rng <= 0:
            return None

        # 4) ancora cercului = punctul format primul cronologic
        anchor_is_high = self.range_high_ts < self.range_low_ts
        anchor_price = self.range_high if anchor_is_high else self.range_low

        gray_upper = (anchor_price + 0.5 * rng, anchor_price + 1.0 * rng)
        gray_lower = (anchor_price - 1.0 * rng, anchor_price - 0.5 * rng)

        # 5) verifica atingerea zonei, in functie de directia configurata
        signal_dir = self.cfg.direction

        if signal_dir == "SHORT":
            zone_touch = bar.high >= level05 and bar.low <= level1
            circle_touch = (not self.cfg.use_circle_filter) or (
                bar.high >= gray_upper[0] and bar.low <= gray_upper[1]
            )
            if zone_touch and circle_touch:
                entry = bar.close
                sl = entry + self.cfg.stop_loss_points
                tp = entry - self.cfg.stop_loss_points * self.cfg.take_profit_mult
                self.traded_today = True
                return Signal(local_ts, "SHORT", entry, sl, tp, self.range_high, self.range_low)

        elif signal_dir == "LONG":
            zone_touch = bar.low <= level05 and bar.high >= level0
            circle_touch = (not self.cfg.use_circle_filter) or (
                bar.low <= gray_lower[1] and bar.high >= gray_lower[0]
            )
            if zone_touch and circle_touch:
                entry = bar.close
                sl = entry - self.cfg.stop_loss_points
                tp = entry + self.cfg.stop_loss_points * self.cfg.take_profit_mult
                self.traded_today = True
                return Signal(local_ts, "LONG", entry, sl, tp, self.range_high, self.range_low)

        return None
