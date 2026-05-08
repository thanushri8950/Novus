import requests
import time

def fetch_with_retry(url, company):
    data = None

    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            break
        except Exception:
            print(f"⚠️ Retry {attempt+1} for {company}")
            time.sleep(2)

    return data