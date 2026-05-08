import time
from fetch_news import fetch_news

def run():
    while True:
        print("🔄 Updating data...")
        fetch_news()
        print("⏳ Sleeping 30 min...\n")
        time.sleep(1800)

if __name__ == "__main__":
    run()