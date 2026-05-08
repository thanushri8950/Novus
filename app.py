import streamlit as st
import pandas as pd
import os

# 1. Page Setup
st.set_page_config(page_title="Novus Market Intelligence", layout="wide")
st.title("📊 Novus: Market News & Sentiment Shift")

# 2. Path Resolution (Make sure this matches your folder structure!)
file_path = "data_pipeline/data/news.csv"

# 3. Defensive Data Loading
if os.path.exists(file_path):
    # Check if the file actually contains data (greater than 0 bytes)
    if os.path.getsize(file_path) > 0:
        try:
            df = pd.read_csv(file_path)
            
            # Convert timestamp
            df['publishedAt'] = pd.to_datetime(df['publishedAt'])

            # --- DASHBOARD CONTROLS ---
            companies = df["company"].unique()
            selected_company = st.sidebar.selectbox("Select Company", companies)
            
            # Filter for the chart
            filtered = df[df['company'] == selected_company].sort_values("publishedAt")

            # --- THE TIME-SERIES CHART ---
            st.subheader(f"📈 {selected_company} Sentiment Shift Timeline")
            
            if not filtered.empty:
                # Prepare chart data (X-axis must be the index)
                chart_data = filtered.set_index("publishedAt")['sentiment']
                st.line_chart(chart_data)
                
                # --- NEWS FEED ---
                st.divider()
                st.subheader("📰 Recent Headlines")
                for _, row in filtered.iloc[::-1].head(5).iterrows():
                    color = "green" if row['sentiment'] > 0 else "red"
                    with st.expander(f"{row['title']}"):
                        st.markdown(f"**Sentiment Score:** :{color}[{row['sentiment']:.2f}]")
                        st.write(f"🔗 [Read More]({row['url']})")
            else:
                st.info(f"No news data found for {selected_company} yet.")

        except Exception as e:
            st.warning("🔄 Data is being updated by the pipeline. Refreshing shortly...")
            st.button("Manual Refresh")
    else:
        st.warning("⏳ Data pipeline has started, but `news.csv` is currently empty. Waiting for the first fetch...")
else:
    st.error(f"❌ Could not find {file_path}. Please ensure your scheduler is running.")

# Add an auto-refresh for the judges
if st.sidebar.button("🔄 Force Refresh Data"):
    st.rerun()