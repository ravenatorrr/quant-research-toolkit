"""
build_dataset.py -- pull a market dataset and save it to data/.

Edit the CONFIG block, then run from the repo root:
    python build_dataset.py

To also pull macro data, set a FRED key in your shell first (keeps it out of the code):
    export FRED_API_KEY="your_key_here"
"""

import os
import quantkit as qk

# ----- CONFIG -----
TICKERS = ["BHP.AX", "RIO.AX", "FMG.AX", "CBA.AX", "WBC.AX",
           "NAB.AX", "MQG.AX", "CSL.AX", "WES.AX", "TLS.AX"]
START = "2015-01-01"
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")   # read from environment, never hard-code
FRED_SERIES = {
    "US10Y": "DGS10", "US2Y": "DGS2", "VIX": "VIXCLS",
    "AUDUSD": "DEXUSAL", "USCPI": "CPIAUCSL",
}


def main():
    prices = qk.fetch_prices(TICKERS, START)
    qk.save(prices, "prices")
    qk.save(qk.log_returns(prices), "returns")

    macro = qk.fetch_macro(FRED_SERIES, FRED_API_KEY, START)
    if macro is not None:
        qk.save(qk.align_macro(macro, prices.index), "macro")
        print(f"Saved prices, returns, macro -> {len(prices)} rows, {prices.shape[1]} tickers.")
    else:
        print(f"Saved prices, returns -> {len(prices)} rows, {prices.shape[1]} tickers. "
              "(No FRED key set; macro skipped.)")


if __name__ == "__main__":
    main()
