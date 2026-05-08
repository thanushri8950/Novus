import yfinance as yf
import pandas as pd
from datetime import datetime

COMPANIES = {
    "Tesla": "TSLA",
    "Apple": "AAPL",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Microsoft": "MSFT"
}

def fetch_price():
    all_data = []

    for company, ticker in COMPANIES.items():
        data = yf.download(ticker, period="1d", interval="1m")

        latest_price = data["Close"].iloc[-1].item()
        prev_price = data["Close"].iloc[-2].item()

        change = (latest_price - prev_price) / prev_price

        all_data.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "company": company,
            "price": latest_price,
            "change": change
        })

    df = pd.DataFrame(all_data)

    # ✅ FIXED PATH
    df.to_csv("data/price_live.csv", index=False)

    print("✅ price_live.csv updated")

if __name__ == "__main__":
    fetch_price()


import time

if __name__ == "__main__":
    while True:
        print("🔄 Updating live data...")
        fetch_price()

        # run shift detection automatically
        import subprocess
        subprocess.run(["python3", "ml/shift_detector.py"])

        # convert to JSON
        import pandas as pd
        df = pd.read_csv("data/shifts_live.csv")
        df.to_json("frontend/public/shifts_live.json", orient="records", indent=2)

        print("✅ Updated UI data")
        time.sleep(10)  # update every 10 seconds