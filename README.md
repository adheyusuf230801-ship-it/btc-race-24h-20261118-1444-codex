# BTC trend bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/adheyusuf230801-ship-it/btc-race-24h-20261118-1444-codex/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/adheyusuf230801-ship-it/btc-race-24h-20261118-1444-codex/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)

A deterministic, long-only CBBTC strategy for make.fun's 1-minute bars replay. It uses Python 3.13 and the standard library; `vendor/makefun_bars.py` is an unchanged copy of the kit SDK. Run it with `python3 -P -s main.py` and send protocol JSON lines on stdin.

## Strategy

The bot requires the 5-bar EMA above the 15-bar EMA above the 40-bar EMA, the 40-bar EMA above the close from 10 observed bars earlier, and a positive 12-bar return exceeding 10 bps. The regime must persist for six observations. It enters after a rising close reclaims the 5-bar EMA, buying 80% of available equity, subject to cash, minimum-notional, and estimated-impact checks.

It exits the full position on a bearish fast/mid EMA regime, an 85-bps loss from fee-inclusive cost, a 95-bps decline from the highest observed close while held, or a 140-bps gain. After an exit it waits 180 batches before another entry. A 2% account drawdown from its observed equity peak halts new orders. Orders use a 250-bps maximum slippage allowance. All signals use supplied bars and account state; the bot uses no clock, network, environment data, randomness, or external runtime files.

## Frozen dev-window checks

The throwaway Python simulator replayed all 1,440 dev bars with next-open fills, 4-bps fees, 2-bps slippage, recorded pool depth and constant-product impact, and final liquidation. The six kit baseline programs were run through the same replay driver and fill model. Results are in USDC; trades count the bot's own filled orders, not final liquidation.

| Bot | Net PnL | Trades | Max drawdown | Fees |
| --- | ---: | ---: | ---: | ---: |
| This bot, offline simulator | +1.744905 | 2 | 0.4295% | 0.640827 |
| Buy-and-hold baseline | -31.633698 | 1 | 3.2485% | 0.787502 |
| Hold-cash baseline | 0.000000 | 0 | 0.0000% | 0.000000 |
| Momentum baseline | -23.865251 | 1 | 3.2416% | 0.790611 |
| EMA-cross baseline | -148.174061 | 80 | 14.9672% | 29.510086 |
| ADX-momentum baseline | -75.566624 | 30 | 7.5567% | 11.527500 |
| RSI-Bollinger baseline | -39.916751 | 19 | 4.3508% | 7.890360 |

The bot's offline replay was run twice and its order logs were byte-identical. `python3 -m py_compile main.py` and a hello/three-batch/done wire smoke test passed using the available local Python 3.12.3 interpreter. The official `grade-local` result is pending the orchestrator's run outside this sandbox; no official grade number is claimed here. The simulator and these limited local checks are not proof of out-of-sample profitability.

Licensed under MIT; see [LICENSE](LICENSE).
