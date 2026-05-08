import requests
import pandas as pd
import time
import os
from datetime import datetime, timezone
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

def fetch_news():
    all_articles = []
    seen_headlines = set()

    for company, ticker in COMPANIES.items():
        print(f"📡 Fetching news for {company}...")

        url = f"https://newsapi.org/v2/everything?q={company}&apiKey={API_KEY}&pageSize=10"

        data = None

        # Retry logic
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                break
            except Exception:
                print(f"⚠️ Retry {attempt+1} for {company}")
                time.sleep(2)

        # Skip if API failed
        if data is None:
            print(f"❌ Skipping {company} (API failed)")
            continue

        articles = data.get("articles", [])

        for article in articles[:10]:
            title = article.get("title")   # ✅ FIXED

            if not title:
                continue

            title = title.strip()

            # Remove duplicates
            if title in seen_headlines:
                continue

            seen_headlines.add(title)

            all_articles.append({
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "company": company,
                "ticker": ticker,
                "headline": title,
                "url": article.get("url"),
                "source": article.get("source", {}).get("name")
            })

    # Ensure output folder exists
    os.makedirs("output", exist_ok=True)

    # Save CSV
    df = pd.DataFrame(all_articles)
    df.to_csv("output/news.csv", index=False)

    print(f"✅ news.csv saved ({len(df)} rows)")


def run_pipeline():
    while True:
        print("\n🔄 Updating data...")
        fetch_news()
        print("⏳ Sleeping for 30 minutes...\n")
        time.sleep(1800)  # 30 min


if __name__ == "__main__":
    run_pipeline()