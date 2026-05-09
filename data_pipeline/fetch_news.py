import yfinance as yf
import time
import random
from datetime import datetime
import json

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

        try:
            data = yf.download(symbol, period="1d", interval="1m", progress=False)

            if data is None or data.empty or len(data) < 2:
                raise Exception("Bad data")

            base_price = float(data["Close"].iloc[-1])

            change = random.uniform(-0.02, 0.02)
            latest_price = base_price * (1 + change)

        except:
            print(f"⚠️ Using fallback for {name}")
            base_price = random.uniform(100, 500)

            change = random.uniform(-0.02, 0.02)
            latest_price = base_price * (1 + change)
            change = random.uniform(-0.05, 0.05)

        rows.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "company": name,
            "price": round(latest_price, 2),
            "change": round(change, 5),
            "shift": "🚀 Positive Shift" if change > 0 else "🔻 Negative Shift"
        })

    # ✅ ALWAYS WRITE NEW JSON
    with open("frontend/public/shifts_live.json", "w") as f:
        json.dump(rows, f, indent=2)

    print("✅ JSON updated")


def run_pipeline():
    while True:
        print("\n🔄 Updating market data...\n")
        fetch_price()
        time.sleep(5)


if __name__ == "__main__":
    run_pipeline()