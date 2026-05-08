import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import time

# Load API key
load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")

if not API_KEY:
    print("❌ API key missing. Check .env file")
    exit()

# Companies
companies = {
    "Tesla": "TSLA",
    "Apple": "AAPL",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Microsoft": "MSFT"
}

def fetch_news():
    all_articles = []

    for company, ticker in companies.items():
        print(f"📡 Fetching news for {company}...")

        url = f"https://newsapi.org/v2/everything?q={company}&apiKey={API_KEY}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            # Check API error
            if data.get("status") != "ok":
                print(f"⚠ API error for {company}: {data}")
                continue

            articles = data.get("articles", [])

            for article in articles[:10]:
                all_articles.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "company": company,
                    "ticker": ticker,
                    "headline": article.get("title"),
                    "url": article.get("url")
                })

            time.sleep(1)  # avoid rate limit

        except Exception as e:
            print(f"❌ Error fetching {company}: {e}")

    return all_articles


def save_to_csv(data):
    df = pd.DataFrame(data)
    df.to_csv("news.csv", index=False)
    print(f"✅ news.csv saved ({len(df)} rows)")


if __name__ == "__main__":
    articles = fetch_news()
    save_to_csv(articles)


if __name__ == "__main__":
    while True:
        print("\n🔄 Updating data...")
        articles = fetch_news()
        save_to_csv(articles)
        print("⏳ Sleeping for 30 minutes...\n")
        time.sleep(10)