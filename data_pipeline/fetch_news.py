import yfinance as yf
import pandas as pd
import time
import subprocess
from datetime import datetime
import random

# 🔥 STOCK LIST
COMPANIES = {
    "Tesla": "TSLA",
    "Apple": "AAPL",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Microsoft": "MSFT"
}


def fetch_price():
    rows = []

    for name, symbol in COMPANIES.items():
        print(f"📡 Fetching {name}...")

        data = None

        # 🔁 Retry logic (important)
        for _ in range(3):
            try:
                data = yf.download(
                    symbol,
                    period="1d",
                    interval="1m",
                    progress=False
                )
                if not data.empty:
                    break
            except:
                pass
            time.sleep(1)

        # ❌ If still no data → skip
        if data is None or data.empty:
            print(f"❌ Failed to fetch {symbol}, skipping...")
            continue

        try:
            latest_price = float(data["Close"].iloc[-1])
            recent = data["Close"].tail(5)

           

            change = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]

# 🔥 amplify + tiny variation
            change = change * 5 + random.uniform(-0.002, 0.002)
            rows.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "company": name,
                "price": latest_price,
                "change": change
            })

        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")
            continue

    # ❗ If nothing fetched
    if len(rows) == 0:
        print("❌ No data fetched at all")
        return

    df = pd.DataFrame(rows)

    # ✅ Save CSV
    df.to_csv("data/price_live.csv", index=False)
    print("✅ price_live.csv updated")


def run_pipeline():
    while True:
        print("\n🔄 Updating live market data...\n")

        fetch_price()

        # 🔁 Run shift detection
        subprocess.run(["python3", "ml/shift_detector.py"])

        # 🔄 Convert to JSON for frontend
        try:
            df = pd.read_csv("data/shifts_live.csv")
            df.to_json(
                "frontend/public/shifts_live.json",
                orient="records",
                indent=2
            )
            print("✅ UI JSON updated")
        except Exception as e:
            print("⚠️ JSON update failed:", e)

        # ⏱️ Wait before next update
        time.sleep(10)


# 🚀 ENTRY POINT
if __name__ == "__main__":
    run_pipeline()