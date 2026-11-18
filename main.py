"""Defensive long-only trend strategy for agent-fun/bars-replay/v1."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars


FAST_SPAN = 5
MID_SPAN = 15
SLOW_SPAN = 40
SLOPE_LAG = 10
MOMENTUM_LAG = 12
POSITION_BPS = 8_000
MAX_IMPACT_BPS = 15
MAX_SLIPPAGE_BPS = 250
HARD_STOP_BPS = 85
TRAIL_STOP_BPS = 95
TAKE_PROFIT_BPS = 140
COOLDOWN_BARS = 180


def ema_step(previous, price, span):
    if previous is None:
        return float(price)
    return previous + (2.0 / (span + 1)) * (price - previous)


class TrendBot:
    def __init__(self):
        self.fast = None
        self.mid = None
        self.slow = None
        self.previous_fast = None
        self.previous_close = None
        self.history = []
        self.regime_bars = 0
        self.peak = None
        self.was_holding = False
        self.cooldown_until = -1
        self.halted = False
        self.peak_equity = None

    def on_batch(self, state, batch):
        bar = next((b for b in batch["bars"] if b["symbol"] == "CBBTC"), None)
        if bar is None:
            return []

        close = int(bar["c"])
        self.fast = ema_step(self.fast, close, FAST_SPAN)
        self.mid = ema_step(self.mid, close, MID_SPAN)
        self.slow = ema_step(self.slow, close, SLOW_SPAN)
        self.history.append(close)
        if len(self.history) > max(SLOPE_LAG + 1, MOMENTUM_LAG + 1):
            self.history.pop(0)

        if self.peak_equity is None or state.equity > self.peak_equity:
            self.peak_equity = state.equity
        if state.equity * 10_000 <= self.peak_equity * 9_800:
            self.halted = True

        holding = state.positions.get("CBBTC")
        if holding is None:
            if self.was_holding:
                self.cooldown_until = state.seq + COOLDOWN_BARS
            self.was_holding = False
            self.peak = None
        else:
            self.was_holding = True
            self.peak = close if self.peak is None else max(self.peak, close)

        ready = len(self.history) > max(SLOPE_LAG, MOMENTUM_LAG)
        regime = (
            ready
            and self.fast is not None
            and self.mid is not None
            and self.slow is not None
            and self.fast > self.mid
            and self.mid > self.slow
            and self.slow > self.history[-1 - SLOPE_LAG]
            and close * 10_000 > self.history[-1 - MOMENTUM_LAG] * 10_010
        )
        self.regime_bars = self.regime_bars + 1 if regime else 0

        if state.warming_up or self.halted:
            self.previous_fast = self.fast
            self.previous_close = close
            return []

        if holding is not None:
            marked_value = state.value("CBBTC", holding.qty)
            hard_stop = marked_value * 10_000 <= holding.cost * (10_000 - HARD_STOP_BPS)
            trail_stop = self.peak is not None and close * 10_000 <= self.peak * (10_000 - TRAIL_STOP_BPS)
            take_profit = marked_value * 10_000 >= holding.cost * (10_000 + TAKE_PROFIT_BPS)
            bearish = self.fast < self.mid and close < self.mid
            if hard_stop or trail_stop or take_profit or bearish:
                self.previous_fast = self.fast
                self.previous_close = close
                return [{
                    "side": "sell",
                    "symbol": "CBBTC",
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            self.previous_fast = self.fast
            self.previous_close = close
            return []

        rising_reclaim = (
            self.previous_close is not None
            and self.previous_fast is not None
            and close > self.previous_close
            and close >= self.fast
            and self.previous_close <= self.previous_fast
        )
        if (
            self.regime_bars >= 6
            and rising_reclaim
            and state.seq >= self.cooldown_until
            and state.cash >= 1_000_000
        ):
            notional = min(state.cash, state.equity * POSITION_BPS // 10_000)
            impact = state.impact_bps("CBBTC", notional)
            if notional >= 1_000_000 and impact is not None and impact <= MAX_IMPACT_BPS:
                self.peak = close
                self.was_holding = True
                self.previous_fast = self.fast
                self.previous_close = close
                return [{
                    "side": "buy",
                    "symbol": "CBBTC",
                    "notional_quote_units": notional,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]

        self.previous_fast = self.fast
        self.previous_close = close
        return []


bot = TrendBot()
if __name__ == "__main__":
    makefun_bars.run(bot.on_batch)
