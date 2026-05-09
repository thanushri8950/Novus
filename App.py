import streamlit as st
import asyncio
import requests
import xml.etree.ElementTree as ET
from playwright.async_api import async_playwright
from transformers import pipeline
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. SETTINGS & MODEL ---
DB_FILE = "sentiment_history.csv"
TICKERS = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT"]

@st.cache_resource
def load_finbert():
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

finbert = load_finbert()

if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Ticker", "Sentiment"]).to_csv(DB_FILE, index=False)


#new2lines
if "chat" not in st.session_state:
    st.session_state.chat = []

# --- 2. CUSTOM STYLING (The "Gold" Look) ---
st.set_page_config(page_title="Big 5 Sentiment Shift", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .agent-card {
        background-color: #3d3d00;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #fbcf33;
        margin-bottom: 10px;
    }
    .metric-label { font-size: 1.2rem; font-weight: bold; color: #fbcf33; }
    .metric-value { font-size: 2rem; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ROBUST SCRAPING LOGIC ---
async def fetch_news_robust(ticker):
    # Attempt 1: Playwright Browser
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0")
            page = await context.new_page()
            await page.goto(f"https://www.google.com/search?q={ticker}+stock+news&tbm=nws", timeout=10000)
            headlines = await page.locator('div[role="heading"]').all_inner_texts()
            await browser.close()
            valid = [h.strip() for h in headlines if len(h) > 20]
            if valid: return valid[:5]
    except: pass

    # Attempt 2: Google News RSS Fallback
    try:
        url = f"https://news.google.com/rss/search?q={ticker}+stock+when:1d"
        res = requests.get(url, timeout=5)
        root = ET.fromstring(res.content)
        return [item.find('title').text for item in root.findall('./channel/item')[:5]]
    except: return []

def analyze_sentiment(headlines):
    if not headlines: return None
    results = finbert(headlines)
    processed = []
    for i, res in enumerate(results):
        score = res['score'] if res['label'] == 'positive' else (-res['score'] if res['label'] == 'negative' else 0)
        processed.append({"Headline": headlines[i], "Sentiment": res['label'].upper(), "Score": round(score, 4)})
    return pd.DataFrame(processed)

# --- 4. TOP SECTION: ANALYSIS ENGINE ---
st.title("🛰️ Big Five Sentiment Shift Detector")
st.caption(f"Real-time Analysis Engine | Last Update: {datetime.now().strftime('%H:%M:%S')}")

cols = st.columns(len(TICKERS))
trigger = st.button('🚀 TRIGGER REAL-TIME SCAN')

# Logic for results
analysis_results = {}

if trigger:
    new_entries = []
    for i, ticker in enumerate(TICKERS):
        with cols[i]:
            with st.spinner(f"Scanning {ticker}..."):
                news = asyncio.run(fetch_news_robust(ticker))
                if news:
                    df = analyze_sentiment(news)
                    avg_score = df["Score"].mean()
                    
                    # Status logic
                    status = "STABLE"
                    if avg_score > 0.12: status = "BULLISH SHIFT"
                    elif avg_score < -0.12: status = "BEARISH SHIFT"
                    
                    analysis_results[ticker] = {"score": avg_score, "status": status, "df": df}
                    new_entries.append({"Timestamp": datetime.now(), "Ticker": ticker, "Sentiment": avg_score})
                    
                    st.metric(label=ticker, value=f"{avg_score:.2f}", delta=status)
                    with st.expander("Scraped News Details"):
                        st.dataframe(df, hide_index=True)
                else:
                    st.error(f"Failed {ticker}")

    if new_entries:
        hist = pd.read_csv(DB_FILE)
        hist = pd.concat([hist, pd.DataFrame(new_entries)], ignore_index=True)
        hist.to_csv(DB_FILE, index=False)

# --- 5. AI AGENT ANALYSIS SECTION (Gold Cards) ---
st.divider()
st.subheader("🤖 AI Agent Analysis")

if analysis_results:
    for ticker, data in analysis_results.items():
        # Only show gold card if sentiment is "Heating Up" (Bullish or Bearish)
        if data["status"] != "STABLE":
            st.markdown(f"""
                <div class="agent-card">
                    <span style="font-weight:bold; color:#fbcf33;">{ticker}:</span> 
                    📈 Sentiment is Heating Up ({data['status']}).
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**{ticker}:** ⚖️ Sentiment is Stable.")
else:
    st.info("Trigger a scan to see Agent Analysis.")

# --- 6. TREND GRAPH (Z-Score) ---
st.divider()
st.subheader("📈 Sentiment Deviation over Time (Z-Score)")

if os.path.exists(DB_FILE):
    history_df = pd.read_csv(DB_FILE)
    if not history_df.empty:
        history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp'], format='mixed')
        
        plot_list = []
        for t in TICKERS:
            t_data = history_df[history_df['Ticker'] == t].sort_values('Timestamp')
            if len(t_data) >= 1:
                for idx in range(len(t_data)):
                    subset = t_data.iloc[:idx+1]
                    mu = subset['Sentiment'].mean()
                    std = subset['Sentiment'].std()
                    z = (subset['Sentiment'].iloc[-1] - mu) / std if (std and std > 0.0001) else 0
                    plot_list.append({"Time": t_data['Timestamp'].iloc[idx], "Ticker": t, "Z-Score": z})
        
        if plot_list:
            fig = px.line(pd.DataFrame(plot_list), x='Time', y='Z-Score', color='Ticker', 
                          markers=True, template="plotly_dark")
            fig.add_hline(y=1.5, line_dash="dash", line_color="green", annotation_text="Hot")
            fig.add_hline(y=-1.5, line_dash="dash", line_color="red", annotation_text="Cold")
            st.plotly_chart(fig, use_container_width=True)

with st.expander("Show History Log"):
    st.dataframe(history_df.sort_values("Timestamp", ascending=False), use_container_width=True)

st.info("💡 **Note:** If scores are 0.00, the news found was interpreted as 'Neutral'.")

#new
st.divider()
st.subheader("💬 Market Assistant")

user_input = st.text_input("Ask about stocks (e.g., 'What about TSLA?')")

if user_input:
    st.session_state.chat.append(("user", user_input))

def generate_reply(query):
    query = query.lower()

    for ticker in TICKERS:
        if ticker.lower() in query:
            if ticker in analysis_results:
                data = analysis_results[ticker]
                return f"{ticker} is {data['status']} (score {data['score']:.2f}). This indicates potential momentum in the market."
            else:
                return f"No recent data for {ticker}. Try running a scan."

    if "top" in query:
        if analysis_results:
            top = max(analysis_results.items(), key=lambda x: abs(x[1]['score']))
            return f"{top[0]} is showing the strongest movement ({top[1]['status']})"

    return "Ask me about a stock like TSLA, AAPL, etc."

st.caption("💡 Try: 'TSLA', 'top stock', 'market trend'")

if user_input:
    with st.spinner("Thinking..."):
        reply = generate_reply(user_input)
    st.session_state.chat.append(("bot", reply))

for sender, msg in st.session_state.chat:
    if sender == "user":
        st.markdown(f"**🧑 You:** {msg}")
    else:
        st.markdown(f"**🤖 Bot:** {msg}")