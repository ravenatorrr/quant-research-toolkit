"""
quantkit -- a small toolkit for quantitative market research.

Pull data, compute risk/return metrics, run backtests, and validate
strategies out-of-sample. Point it at any tickers you like.

Frequency convention: pass `periods=252` for daily data, `periods=12` for
monthly. See README.md for the workflow and the reasoning behind the design.
"""

from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

__all__ = [
    "fetch_prices", "fetch_macro", "align_macro", "save", "load",
    "simple_returns", "log_returns",
    "annualized_return", "annualized_vol", "sharpe", "max_drawdown", "summarize",
    "equal_weight", "ma_crossover", "momentum_portfolio",
    "train_test_split", "rank_momentum_params",
]


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

def fetch_prices(tickers, start, end=None):
    """Download split/dividend-adjusted daily closes. One column per ticker."""
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame()
    return close.dropna(how="all")


def fetch_macro(series_map, api_key, start):
    """Download FRED series. Returns None if no api_key. series_map: name -> code."""
    if not api_key:
        return None
    from fredapi import Fred
    fred = Fred(api_key=api_key)
    return pd.DataFrame({name: fred.get_series(code, observation_start=start)
                         for name, code in series_map.items()})


def align_macro(macro, index):
    """Reindex macro onto `index`, forward-filling last-known values."""
    return macro.reindex(index).ffill()


# repo root = the folder this file lives in
_ROOT = Path(__file__).resolve().parent


def save(df, name, data_dir=None):
    """Write df to <repo>/data/name.csv (creating the folder if needed)."""
    path = Path(data_dir) if data_dir else _ROOT / "data"
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{name}.csv"
    df.to_csv(out)
    return out


def load(name, data_dir=None):
    """Load <repo>/data/name.csv into a date-indexed DataFrame."""
    path = Path(data_dir) if data_dir else _ROOT / "data"
    return pd.read_csv(path / f"{name}.csv", index_col=0, parse_dates=True)


# --------------------------------------------------------------------------- #
# Returns
# --------------------------------------------------------------------------- #

def simple_returns(prices):
    return prices.pct_change()


def log_returns(prices):
    return np.log(prices / prices.shift(1))


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def annualized_return(prices, periods=252):
    """Compound annual growth rate (CAGR) of a price series or frame."""
    def _cagr(col):
        col = col.dropna()
        if len(col) < 2:
            return np.nan
        years = len(col) / periods
        return (col.iloc[-1] / col.iloc[0]) ** (1 / years) - 1
    return prices.apply(_cagr) if isinstance(prices, pd.DataFrame) else _cagr(prices)


def annualized_vol(returns, periods=252):
    return returns.std() * np.sqrt(periods)


def sharpe(returns, periods=252, rf=0.0):
    """Annualised Sharpe ratio (risk-free rate rf, default 0)."""
    excess = returns - rf / periods
    vol = excess.std()
    if isinstance(vol, pd.Series):
        return (excess.mean() * periods) / (vol * np.sqrt(periods))
    if vol == 0 or np.isnan(vol):
        return np.nan
    return (excess.mean() * periods) / (vol * np.sqrt(periods))


def max_drawdown(prices):
    """Worst peak-to-trough decline of a price/equity series or frame."""
    return (prices / prices.cummax() - 1).min()


def summarize(prices, periods=252):
    """Per-column table of CAGR, volatility, Sharpe and max drawdown."""
    rets = simple_returns(prices)
    return pd.DataFrame({
        "Ann. Return": annualized_return(prices, periods),
        "Ann. Volatility": annualized_vol(rets, periods),
        "Sharpe": sharpe(rets, periods),
        "Max Drawdown": max_drawdown(prices),
    })


# --------------------------------------------------------------------------- #
# Strategies
# --------------------------------------------------------------------------- #

def equal_weight(prices):
    """Per-period return of an equal-weight portfolio of all columns."""
    return simple_returns(prices).mean(axis=1)


def ma_crossover(price, short=50, long=200, cost=0.001):
    """Long/cash moving-average crossover on a single price series.

    Returns a frame with columns: ret, sma_short, sma_long, position,
    strat_ret, bh_ret. `cost` is charged per trade (position change).
    """
    df = pd.DataFrame(index=price.index)
    df["ret"] = price.pct_change()
    df["sma_short"] = price.rolling(short).mean()
    df["sma_long"] = price.rolling(long).mean()
    signal = (df["sma_short"] > df["sma_long"]).astype(int)
    df["position"] = signal.shift(1)          # act next bar: no look-ahead
    df = df.dropna()
    trade = df["position"].diff().abs().fillna(0)
    df["strat_ret"] = df["position"] * df["ret"] - trade * cost
    df["bh_ret"] = df["ret"]
    return df


def momentum_portfolio(prices, lookback=12, top_k=3, which="top"):
    """Equal-weight cross-sectional momentum portfolio, rebalanced each period.

    which="top" holds the strongest `top_k`; "bottom" holds the weakest.
    Pass prices already at the desired frequency (e.g. month-end).
    """
    rets = prices.pct_change()
    signal = prices / prices.shift(lookback) - 1
    ranks = signal.rank(axis=1, ascending=False)
    if which == "top":
        pick = ranks <= top_k
    else:
        pick = ranks >= (ranks.max(axis=1).to_numpy().reshape(-1, 1) - top_k + 1)
    held = pick.shift(1).astype(float)        # hold next period: no look-ahead
    port = (rets * held).sum(axis=1) / held.sum(axis=1)
    return port.replace([np.inf, -np.inf], np.nan).dropna()


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def train_test_split(df, split_date):
    """Split a date-indexed frame into (train, test) at split_date."""
    return df[df.index < split_date], df[df.index >= split_date]


def rank_momentum_params(prices, lookbacks, top_ks, periods=12):
    """Grid-search momentum (lookback, top_k) by Sharpe. Run on TRAIN data only."""
    rows = []
    for lb in lookbacks:
        for k in top_ks:
            rows.append({"lookback": lb, "top_k": k,
                         "sharpe": sharpe(momentum_portfolio(prices, lb, k), periods=periods)})
    return pd.DataFrame(rows).sort_values("sharpe", ascending=False).reset_index(drop=True)
