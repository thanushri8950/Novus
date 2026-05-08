"""
sentiment_engine.py
────────────────────────────────────────────────────────────────────────────────
Sentiment Shift Detection – Scoring Module
Loads ProsusAI/finbert, scores financial headlines, maintains a rolling
30-minute average, persists results to sentiment_live.csv, and exposes
get_latest_sentiment(ticker) for downstream teammates.

Reads live headlines from teammate's news.csv:
  Expected columns: date, company, ticker, headline, url
────────────────────────────────────────────────────────────────────────────────
"""

import csv
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

# ── Third-party ────────────────────────────────────────────────────────────────
try:
    import pandas as pd
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
except ImportError as e:
    raise ImportError(
        "[ERROR] Missing dependencies. Run:\n"
        "  pip install transformers torch pandas\n"
        f"Original error: {e}"
    ) from e

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
MODEL_NAME       = "ProsusAI/finbert"
NEWS_CSV_PATH    = "news.csv"          # teammate's input file
CSV_PATH         = "sentiment_live.csv"
ROLLING_WINDOW   = timedelta(minutes=30)
REFRESH_INTERVAL = 30 * 60            # seconds – how often the background loop runs
CSV_COLUMNS      = ["timestamp", "ticker", "headline", "label", "score", "avg_score"]

# ── Teammate's news.csv schema (LOCKED ✅ confirmed 2025-05-08) ───────────────
# Full schema: date, company, ticker, headline, url, source
# DO NOT CHANGE — any rename will break sentiment scoring
NEWS_COL_TICKER   = "ticker"
NEWS_COL_HEADLINE = "headline"

LABEL_TO_SCORE   = {"positive": 1, "neutral": 0, "negative": -1}
SCORE_TO_LABEL   = {1: "POSITIVE", 0: "NEUTRAL", -1: "NEGATIVE"}

# ──────────────────────────────────────────────────────────────────────────────
# Logging helper
# ──────────────────────────────────────────────────────────────────────────────
def _log(message: str) -> None:
    """Print a timestamped log line."""
    ts = datetime.now().strftime("%I:%M %p")
    print(f"[{ts}] {message}")


# ──────────────────────────────────────────────────────────────────────────────
# SentimentEngine
# ──────────────────────────────────────────────────────────────────────────────
class SentimentEngine:
    """
    Loads FinBERT once, scores headlines on demand, keeps an in-memory
    rolling window, persists to CSV, and exposes get_latest_sentiment().
    """

    def __init__(self) -> None:
        self._pipe        = None          # HuggingFace pipeline (lazy-loaded)
        self._model_ready = threading.Event()
        self._lock        = threading.Lock()

        # Rolling window: ticker → deque of (datetime, numeric_score)
        self._window: dict[str, deque] = defaultdict(deque)

        # Latest computed avg per ticker
        self._latest: dict[str, dict]  = {}

        self._ensure_csv()
        self._load_model_async()

    # ── Model loading ──────────────────────────────────────────────────────────

    def _load_model_async(self) -> None:
        """Load FinBERT in a background thread so startup is non-blocking."""
        thread = threading.Thread(target=self._load_model, daemon=True, name="finbert-loader")
        thread.start()

    def _load_model(self) -> None:
        _log(f"Loading {MODEL_NAME} … (this may take a moment)")
        try:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model     = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            device    = 0 if torch.cuda.is_available() else -1  # GPU if available
            self._pipe = pipeline(
                task="text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device,
                top_k=None,           # return all three label scores
            )
            self._model_ready.set()
            _log(f"FinBERT loaded successfully (device={'GPU' if device == 0 else 'CPU'})")
        except Exception as exc:
            _log(
                f"[ERROR] Failed to load {MODEL_NAME}.\n"
                f"  Reason : {exc}\n"
                f"  Fix    : Check your internet connection and that "
                f"'transformers' + 'torch' are installed."
            )
            # Leave _model_ready un-set → callers will treat as neutral

    def _wait_for_model(self, timeout: float = 120) -> bool:
        """Block until model is ready; return False if it never loads."""
        return self._model_ready.wait(timeout=timeout)

    # ── CSV ───────────────────────────────────────────────────────────────────

    def _ensure_csv(self) -> None:
        """Create CSV with header row if it doesn't already exist."""
        if not os.path.exists(CSV_PATH):
            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()

    def _append_rows(self, rows: list[dict]) -> None:
        """Thread-safe CSV append."""
        with self._lock:
            with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writerows(rows)

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_headline(self, headline: str) -> tuple[str, float, int]:
        """
        Returns (label_str, confidence, numeric_score).
        Falls back to NEUTRAL if model isn't ready.
        """
        if not self._model_ready.is_set():
            return "NEUTRAL", 0.0, 0

        raw = self._pipe(headline, truncation=True, max_length=512)
        # raw is a list of lists: [[{"label": "positive", "score": 0.97}, ...]]
        # Flatten if nested
        preds = raw[0] if isinstance(raw[0], list) else raw

        best = max(preds, key=lambda x: x["score"])
        label_key  = best["label"].lower()          # "positive" / "negative" / "neutral"
        confidence = round(best["score"], 4)
        numeric    = LABEL_TO_SCORE.get(label_key, 0)
        label_str  = label_key.upper()
        return label_str, confidence, numeric

    # ── Rolling average ───────────────────────────────────────────────────────

    def _update_window(self, ticker: str, ts: datetime, numeric: float) -> float:
        """Push new score, evict entries older than 30 min, return current avg."""
        dq    = self._window[ticker]
        cutoff = ts - ROLLING_WINDOW
        dq.append((ts, numeric))
        while dq and dq[0][0] < cutoff:
            dq.popleft()
        avg = sum(v for _, v in dq) / len(dq) if dq else 0.0
        return round(avg, 4)

    # ── Public: process a batch of headlines ─────────────────────────────────

    def process_headlines(self, ticker: str, headlines: list[str]) -> dict:
        """
        Score every headline for *ticker*.
        Returns {"avg_score": float, "label": str}.

        Designed to be called from your teammate's pipeline or the
        background refresh loop.
        """
        ticker = ticker.upper()

        # Edge case: empty list
        if not headlines:
            _log(f"No headlines for {ticker} → returning neutral score 0")
            self._latest[ticker] = {"avg_score": 0.0, "label": "NEUTRAL"}
            return self._latest[ticker]

        # Wait up to 2 min for model on first use
        if not self._wait_for_model(timeout=120):
            _log(f"[WARN] Model not ready for {ticker} → returning neutral score 0")
            self._latest[ticker] = {"avg_score": 0.0, "label": "NEUTRAL"}
            return self._latest[ticker]

        ts   = datetime.now()
        rows = []

        for headline in headlines:
            label_str, confidence, numeric = self._score_headline(headline)
            avg = self._update_window(ticker, ts, numeric)
            rows.append({
                "timestamp": ts.isoformat(timespec="seconds"),
                "ticker"   : ticker,
                "headline" : headline,
                "label"    : label_str,
                "score"    : confidence,
                "avg_score": avg,
            })

        # Save to CSV (avg_score in each row reflects the running avg at that moment)
        self._append_rows(rows)

        # Compute final avg for the whole batch
        final_avg = rows[-1]["avg_score"]
        label_out = self._avg_to_label(final_avg)
        self._latest[ticker] = {"avg_score": final_avg, "label": label_out}

        _log(
            f"Scored {len(headlines)} {ticker} headlines "
            f"→ avg: {final_avg:+.2f} {label_out}"
        )
        return self._latest[ticker]

    # ── Public: teammate API ──────────────────────────────────────────────────

    def get_latest_sentiment(self, ticker: str) -> dict:
        """
        Teammate-facing function.
        Returns {"avg_score": float, "label": str}.

        avg_score : rolling 30-min average mapped to [-1, 1]
        label     : "POSITIVE" | "NEUTRAL" | "NEGATIVE"

        Returns neutral 0 if no data has been processed yet for *ticker*.
        """
        ticker = ticker.upper()
        breakpoint()
        result = self._latest.get(ticker, {"avg_score": 0.0, "label": "NEUTRAL"})
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _avg_to_label(avg: float) -> str:
        """Convert a continuous avg score to a human-readable label."""
        if avg > 0.15:
            return "POSITIVE"
        if avg < -0.15:
            return "NEGATIVE"
        return "NEUTRAL"


# ──────────────────────────────────────────────────────────────────────────────
# Background refresh loop
# ──────────────────────────────────────────────────────────────────────────────

def start_live_scoring(
    engine: SentimentEngine,
    fetch_live_news,           # callable: ticker -> list[str]
    tickers: list[str],
) -> threading.Thread:
    """
    Spawn a daemon thread that calls fetch_live_news() every 30 minutes
    and feeds new headlines into *engine* for each ticker.

    Usage:
        from sentiment_engine import SentimentEngine, start_live_scoring
        from my_teammate_module import fetch_live_news

        engine = SentimentEngine()
        thread = start_live_scoring(engine, fetch_live_news, ["AAPL", "MSFT", "TSLA"])
        # thread runs in the background; your main code continues
    """
    def _loop():
        _log(f"Live scoring started for: {', '.join(tickers)}")
        while True:
            for ticker in tickers:
                try:
                    headlines = fetch_live_news(ticker)
                    engine.process_headlines(ticker, headlines)
                except Exception as exc:
                    _log(f"[ERROR] Failed to fetch/score {ticker}: {exc}")
            _log(f"Next refresh in {REFRESH_INTERVAL // 60} minutes …")
            time.sleep(REFRESH_INTERVAL)

    thread = threading.Thread(target=_loop, daemon=True, name="live-scoring-loop")
    thread.start()
    return thread


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton + convenience wrapper (drop-in for teammates)
# ──────────────────────────────────────────────────────────────────────────────

_engine = SentimentEngine()


def get_latest_sentiment(ticker: str) -> dict:
    """
    Public API for teammates.

    Example
    -------
    >>> from sentiment_engine import get_latest_sentiment
    >>> result = get_latest_sentiment("AAPL")
    >>> print(result)
    {"avg_score": 0.72, "label": "POSITIVE"}
    """
    return _engine.get_latest_sentiment(ticker)


def process_headlines(ticker: str, headlines: list[str]) -> dict:
    """
    Convenience wrapper – score a batch of headlines through the shared engine.

    Example
    -------
    >>> from sentiment_engine import process_headlines
    >>> result = process_headlines("MSFT", fetch_live_news("MSFT"))
    """
    return _engine.process_headlines(ticker, headlines)


# ──────────────────────────────────────────────────────────────────────────────
# news.csv reader  (reads from teammate's file)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_live_news(ticker: str) -> list[str]:
    """
    Reads headlines for *ticker* from the teammate's news.csv.

    Expected columns (confirm with team):
        date, company, ticker, headline, url

    Returns a list of headline strings, or [] on any error.
    """
    try:
        df = pd.read_csv(NEWS_CSV_PATH)
        df.columns = df.columns.str.strip()   # handle accidental spaces after commas

        # Validate required columns exist
        for col in (NEWS_COL_TICKER, NEWS_COL_HEADLINE):
            if col not in df.columns:
                _log(
                    f"[ERROR] '{col}' column missing in {NEWS_CSV_PATH}. "
                    f"Found columns: {list(df.columns)} — confirm schema with teammate."
                )
                return []

        mask      = df[NEWS_COL_TICKER].astype(str).str.upper() == ticker.upper()
        headlines = df.loc[mask, NEWS_COL_HEADLINE].dropna().tolist()

        if not headlines:
            _log(f"[WARN] No headlines found for {ticker} in {NEWS_CSV_PATH}")

        return headlines

    except FileNotFoundError:
        _log(
            f"[ERROR] {NEWS_CSV_PATH} not found. "
            f"Is your teammate's data script running? "
            f"Expected path: {os.path.abspath(NEWS_CSV_PATH)}"
        )
        return []
    except Exception as exc:
        _log(f"[ERROR] Failed to read {NEWS_CSV_PATH}: {exc}")
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Quick smoke-test  (python sentiment_engine.py)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # ── If news.csv exists, use it. Otherwise fall back to fake data. ──────────
    if os.path.exists(NEWS_CSV_PATH):
        _log(f"Found {NEWS_CSV_PATH} — reading real headlines from teammate's file")

        # Auto-detect tickers present in the file
        df_check = pd.read_csv(NEWS_CSV_PATH)
        df_check.columns = df_check.columns.str.strip()
        tickers = df_check["ticker"].dropna().str.upper().unique().tolist()
        _log(f"Tickers detected in {NEWS_CSV_PATH}: {tickers}")

    else:
        _log(f"{NEWS_CSV_PATH} not found — running with fake data for testing")

        # Create a temporary fake news.csv so fetch_live_news() works
        fake_rows = [
            {"date": "2025-05-08", "company": "Apple",     "ticker": "AAPL", "headline": "Apple beats Q3 earnings expectations with record iPhone sales",  "url": ""},
            {"date": "2025-05-08", "company": "Apple",     "ticker": "AAPL", "headline": "Apple faces EU antitrust fine over App Store policies",          "url": ""},
            {"date": "2025-05-08", "company": "Apple",     "ticker": "AAPL", "headline": "Apple stock rises after analyst upgrades to Buy",                 "url": ""},
            {"date": "2025-05-08", "company": "Apple",     "ticker": "AAPL", "headline": "Supply chain concerns weigh on Apple's outlook",                  "url": ""},
            {"date": "2025-05-08", "company": "Apple",     "ticker": "AAPL", "headline": "Apple announces record $90B buyback program",                     "url": ""},
            {"date": "2025-05-08", "company": "Microsoft", "ticker": "MSFT", "headline": "Microsoft Azure revenue surges 29% year-over-year",               "url": ""},
            {"date": "2025-05-08", "company": "Microsoft", "ticker": "MSFT", "headline": "Microsoft faces regulatory scrutiny over Activision deal",         "url": ""},
            {"date": "2025-05-08", "company": "Microsoft", "ticker": "MSFT", "headline": "Microsoft raises dividend for the 20th consecutive year",          "url": ""},
        ]
        pd.DataFrame(fake_rows).to_csv(NEWS_CSV_PATH, index=False)
        _log(f"Created temporary {NEWS_CSV_PATH} with fake headlines for testing")
        tickers = ["AAPL", "MSFT"]

    # Start background loop (fires immediately, then every 30 min)
    start_live_scoring(_engine, fetch_live_news, tickers)

    # Let the background thread do one scoring pass
    time.sleep(5)

    # Query teammate API
    for t in tickers:
        result = get_latest_sentiment(t)
        print(f"\n  get_latest_sentiment('{t}') → {result}")

    print(f"\n  Sentiment results saved to: {os.path.abspath(CSV_PATH)}")