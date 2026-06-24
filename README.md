# quant — a personal quantitative research toolkit

A small, reusable toolkit for pulling market data and stress-testing trading
ideas **honestly**. Point it at any tickers, ask a question, get an answer you
can actually trust — because the tools bake in the checks that stop you fooling
yourself.

> Educational project. Nothing here is financial advice.

---

## What this is

Markets are full of patterns; most of them are noise that looks like signal. The
job of quantitative research isn't finding patterns — it's figuring out which
ones are real and which are you fooling yourself. This toolkit is built around
that one idea. Every tool in it exists to run the research loop:

> **hypothesis → data → test → (usually) reject → repeat**

The tools are generic. They don't know or care which market you point them at —
swap the tickers in `build_dataset.py` and everything downstream just works on
the new data.

---

## Repo structure

```
quant/
├── quantkit.py        # the toolkit: data, metrics, backtests, validation
├── build_dataset.py   # pull a dataset (edit the config) and save it to data/
├── notebooks/         # research notebooks that use quantkit
├── data/              # generated CSVs (git-ignored — regenerate any time)
└── README.md
```

---

## Setup

Requires a Python environment with `pandas`, `numpy`, `matplotlib`,
`yfinance`, and `fredapi` (a conda env named `quant` is assumed).

```bash
conda activate quant
```

Optional — to pull macro data from FRED, set your free API key in the shell so it
never ends up in the code:

```bash
export FRED_API_KEY="your_key_here"
```

---

## Quickstart

```bash
# 1. pull the data (edit the ticker list in build_dataset.py first if you like)
python build_dataset.py

# 2. open the example notebook and run it
#    notebooks/example_research.ipynb
```

That's the whole loop: `build_dataset.py` fetches and cleans, the notebooks
consume the clean CSVs.

---

## The toolkit (`quantkit.py`)

**Data**
- `fetch_prices(tickers, start, end=None)` — adjusted daily closes, one column per ticker.
- `fetch_macro(series_map, api_key, start)` — FRED series (returns `None` without a key).
- `align_macro(macro, index)` — reindex macro onto trading days, forward-filled.
- `save(df, name)` / `load(name)` — read/write `data/<name>.csv`.

**Returns**
- `simple_returns(prices)`, `log_returns(prices)`.

**Metrics** (`periods=252` daily, `12` monthly)
- `annualized_return(prices)` — CAGR.
- `annualized_vol(returns)`, `sharpe(returns)`, `max_drawdown(prices)`.
- `summarize(prices)` — one table of all four, per column.

**Strategies**
- `equal_weight(prices)` — equal-weight benchmark return series.
- `ma_crossover(price, short, long, cost)` — moving-average crossover backtest.
- `momentum_portfolio(prices, lookback, top_k, which)` — cross-sectional momentum.

**Validation**
- `train_test_split(df, split_date)` — split history into train / test.
- `rank_momentum_params(prices, lookbacks, top_ks)` — grid-search by Sharpe (train only).

---

## The research workflow (why the tools are built this way)

Three ideas are wired into the tools because they're what separate a backtest you
can trust from one that lies to you:

1. **Work in returns, not prices.** A $3 stock and a $300 stock aren't comparable
   in dollars; a +2% day is comparable for both.
2. **No look-ahead.** Every backtest acts on a signal the period *after* it's
   computed (`.shift(1)` in `ma_crossover` and `momentum_portfolio`). You can't
   trade on a close you haven't seen yet. Forgetting this is the #1 way people
   produce a fake brilliant strategy.
3. **Costs and out-of-sample.** Trades cost money (`cost` per trade), and any edge
   must survive on data it was never fitted to (`train_test_split`).

**Judge strategies on two gaps:**
- *train Sharpe vs test Sharpe* — the **overfitting gap**. Want it **small**
  (the strategy is robust).
- *strategy vs benchmark, on the test set* — want the **strategy ahead** (it's
  actually worth something).
A strategy must pass **both** to be taken seriously.

---

## What I learned building this

Findings from running these tools on 10 ASX large-caps (2015–2026):

- **Return without risk context is meaningless.** Ranking by raw return and by
  Sharpe give different winners — the biggest grower is rarely the best
  risk-adjusted bet. Max drawdown is the human side of risk: the number that
  decides whether you could actually *hold* something.
- **A moving-average crossover lost to buy-and-hold** after costs, across every
  stock and setting tried. Being "clever" mostly bought lower drawdown, not
  higher return.
- **Momentum looked great in-sample, then collapsed out-of-sample.** Train Sharpe
  ~1.5–1.8 fell to ~0.4–0.7 on unseen data, and the verdict flipped between
  "wins" and "loses" depending purely on where the train/test split was drawn.
  That instability is the signature of a fragile, overfit result — not an edge.
- **Conclusion:** on this small universe, simple strategies don't beat
  buy-and-hold, and the ones that look like they do are usually fooling you.
  Beating the market is genuinely hard. The value of the work is the *discipline*
  of telling real from fake — not a winning strategy.
- **Open caveat:** "momentum fails" and "momentum fails *on 10 stocks*" are
  different claims. Momentum is well documented across hundreds of stocks; 10 is
  far too few for it to show up over single-name noise. Settling that needs
  breadth (see next steps).

---

## The anti-overfitting checklist

Before believing any result:

- [ ] Hypothesis (and what would disprove it) written down *first*?
- [ ] Data point-in-time, no look-ahead?
- [ ] Working in returns, not raw prices?
- [ ] Split by date, with a real out-of-sample test set held back?
- [ ] Realistic costs subtracted?
- [ ] How many things did I try before this "worked"? (multiple testing)
- [ ] Does it survive different split dates / small parameter changes?
- [ ] Judged on risk-adjusted metrics, not just total return?

If you can't tick them all, you have a hypothesis — not an edge.

---

## Next steps

- **More breadth** — pull 50–100+ tickers so a single rocket can't carry a
  basket, and re-run the momentum study.
- **Walk-forward testing** — re-fit periodically while rolling through time.
- **Monte Carlo** — bootstrap returns to see the *distribution* of outcomes, not
  just the one history that happened.
