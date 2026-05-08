import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from collections import deque
import os

# ── Storage ──────────────────────────────────────────────────────────────────
# Rolling 7-day sentiment window per ticker (max 7 scores)
sentiment_windows: dict[str, deque] = {}

# Shift events log per ticker
shift_log: dict[str, list] = {}

# Correlation data per ticker
# Stores list of (z_score, price_1hr_chg, price_1day_chg, price_3day_chg)
correlation_data: dict[str, list] = {}

# CSV paths
SHIFTS_CSV = "shifts_live.csv"
CORR_CSV = "correlation_live.csv"

# ── Init CSVs ─────────────────────────────────────────────────────────────────
def _init_csvs():
    if not os.path.exists(SHIFTS_CSV):
        pd.DataFrame(columns=[
            "timestamp", "ticker", "z_score", "direction", "price_at_shift"
        ]).to_csv(SHIFTS_CSV, index=False)

    if not os.path.exists(CORR_CSV):
        pd.DataFrame(columns=[
            "ticker", "1hr_corr", "1day_corr", "3day_corr"
        ]).to_csv(CORR_CSV, index=False)

_init_csvs()

# ── Logging ───────────────────────────────────────────────────────────────────
def _log(msg: str):
    now = datetime.now().strftime("%I:%M %p")
    print(f"[{now}] {msg}")

# ── Core: Ingest new sentiment score ─────────────────────────────────────────
def ingest_sentiment(ticker: str, avg_score: float, price_at_shift: float):
    """
    Call this every time get_latest_sentiment() returns a new score.
    Maintains rolling 7-day window, computes z-score, flags shifts.
    """
    ticker = ticker.upper()

    # Init window if first time seeing this ticker
    if ticker not in sentiment_windows:
        sentiment_windows[ticker] = deque(maxlen=7)
        shift_log[ticker] = []
        correlation_data[ticker] = []

    window = sentiment_windows[ticker]
    window.append(avg_score)

    # Need at least 3 data points for meaningful z-score
    if len(window) < 3:
        _log(f"{ticker} — collecting data ({len(window)}/3 minimum)...")
        return None

    scores = np.array(window)
    mean = np.mean(scores)
    std = np.std(scores)

    if std == 0:
        return None  # No variance, skip

    z_score = (avg_score - mean) / std

    if abs(z_score) > 1.5:
        direction = "BULLISH" if z_score > 0 else "BEARISH"
        timestamp = datetime.now()

        _log(f"⚠️  {ticker} Shift Detected! z={z_score:.1f} {direction}")

        # Save shift event
        event = {
            "timestamp": timestamp,
            "ticker": ticker,
            "z_score": round(z_score, 4),
            "direction": direction,
            "price_at_shift": price_at_shift
        }
        shift_log[ticker].append(event)

        # Append to CSV
        pd.DataFrame([event]).to_csv(SHIFTS_CSV, mode="a", header=False, index=False)

        return event

    return None

# ── Core: Record price follow-through after a shift ──────────────────────────
def record_price_followthrough(
    ticker: str,
    z_score: float,
    price_1hr_pct: float,
    price_1day_pct: float,
    price_3day_pct: float
):
    """
    Call this after 1hr, 1day, 3day has passed since a shift was detected.
    Stores the follow-through data and recomputes running correlation.
    """
    ticker = ticker.upper()

    if ticker not in correlation_data:
        correlation_data[ticker] = []

    correlation_data[ticker].append((z_score, price_1hr_pct, price_1day_pct, price_3day_pct))

    _update_correlation(ticker)

# ── Internal: Recompute and save correlation ──────────────────────────────────
def _update_correlation(ticker: str):
    data = correlation_data.get(ticker, [])

    if len(data) < 2:
        return  # Need at least 2 points

    arr = np.array(data)
    z_scores   = arr[:, 0]
    pct_1hr    = arr[:, 1]
    pct_1day   = arr[:, 2]
    pct_3day   = arr[:, 3]

    def safe_corr(a, b):
        if np.std(a) == 0 or np.std(b) == 0:
            return 0.0
        return round(float(np.corrcoef(a, b)[0, 1]), 4)

    corr_1hr  = safe_corr(z_scores, pct_1hr)
    corr_1day = safe_corr(z_scores, pct_1day)
    corr_3day = safe_corr(z_scores, pct_3day)

    _log(f"{ticker} 1-day correlation updated: {corr_1day}")

    row = {
        "ticker": ticker,
        "1hr_corr": corr_1hr,
        "1day_corr": corr_1day,
        "3day_corr": corr_3day
    }

    # Update correlation CSV (replace row for this ticker)
    if os.path.exists(CORR_CSV):
        df = pd.read_csv(CORR_CSV)
        df = df[df["ticker"] != ticker]  # Remove old row
    else:
        df = pd.DataFrame(columns=["ticker", "1hr_corr", "1day_corr", "3day_corr"])

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CORR_CSV, index=False)

# ── Public API for frontend team ──────────────────────────────────────────────
def get_shift_events(ticker: str) -> list:
    """
    Returns list of recent shift events for a ticker.
    Each event: {timestamp, ticker, z_score, direction, price_at_shift}
    """
    return shift_log.get(ticker.upper(), [])

def get_correlation(ticker: str) -> dict:
    """
    Returns correlation values for a ticker.
    Returns: {ticker, 1hr_corr, 1day_corr, 3day_corr}
    """
    ticker = ticker.upper()

    if os.path.exists(CORR_CSV):
        df = pd.read_csv(CORR_CSV)
        row = df[df["ticker"] == ticker]
        if not row.empty:
            return row.iloc[0].to_dict()

    return {"ticker": ticker, "1hr_corr": None, "1day_corr": None, "3day_corr": None}

# ── Main loop (called by your teammate's pipeline) ────────────────────────────
def run_detection_cycle(ticker: str, get_latest_sentiment, fetch_live_price, fetch_intraday):
    """
    Your teammates call this every cycle with their data-fetch functions.
    
    Example usage:
        from shift_detector import run_detection_cycle
        run_detection_cycle("TSLA", get_latest_sentiment, fetch_live_price, fetch_intraday)
    """
    sentiment = get_latest_sentiment(ticker)
    price_data = fetch_live_price(ticker)

    avg_score = sentiment["avg_score"]
    price     = price_data["price"]

    event = ingest_sentiment(ticker, avg_score, price)
    return event


df = pd.read_csv("data/price_live.csv")

def detect_shift(row):
    if row["change"] > 0.001:
        return "🚀 Positive Shift"
    elif row["change"] < -0.001:
        return "⚠️ Negative Shift"
    else:
        return "➖ Stable"

df["shift"] = df.apply(detect_shift, axis=1)

df.to_csv("data/shifts_live.csv", index=False)
print("✅ shifts_live.csv updated")
