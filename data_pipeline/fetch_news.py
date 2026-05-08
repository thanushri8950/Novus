import requests
import pandas as pd
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")

# Companies
COMPANIES = {
    "Tesla": "TSLA",
    "Apple": "AAPL",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Microsoft": "MSFT"
}

# Fetch news function
def fetch_news():
    all_articles = []
    seen_headlines = set()

    for company, ticker in COMPANIES.items():
        print(f"📡 Fetching news for {company}...")

        url = f"https://newsapi.org/v2/everything?q={company}&apiKey={API_KEY}&pageSize=10"

        data = None  # ✅ FIX: initialize

        # Retry logic
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()  # ✅ catches API errors
                data = response.json()
                break
            except Exception as e:
                print(f"⚠️ Retry {attempt+1} for {company}")
                time.sleep(2)

        # ✅ FIX: skip if API failed
        if data is None:
            print(f"❌ Skipping {company} (API failed)")
            continue

        articles = data.get("articles", [])

        for article in articles:
            title = article.get("title")

            # Skip invalid
            if not title:
                continue

            title = title.strip()

            # Remove duplicates
            if title in seen_headlines:
                continue

            seen_headlines.add(title)

            all_articles.append({
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "company": company,
                "ticker": ticker,
                "headline": title,
                "url": article.get("url"),
                "source": article.get("source", {}).get("name")
            })

    # Save CSV
    df = pd.DataFrame(all_articles)
    df.to_csv("news.csv", index=False)

    print(f"✅ news.csv saved ({len(df)} rows)")


# Auto-update loop
def run_pipeline():
    while True:
        print("\n🔄 Updating data...")
        fetch_news()
        print("⏳ Sleeping for 1 second...\n")
        time.sleep(1)  # 30 minutes


if __name__ == "__main__":
    run_pipeline()