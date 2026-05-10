import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Nifty SmallCap 250", layout="wide")

st.title("📂 Nifty SmallCap 250 Companies Data")
st.markdown("Upload a CSV to filter by industry and fetch live financial metrics.")

# --- Helper Function to Fetch and Process Data ---
@st.cache_data(ttl=3600)  # Caches data for 1 hour
def get_stock_metrics(symbols):
    data_list = []
    
    for sym in symbols:
        try:
            # Handle NSE symbols automatically
            ticker_sym = f"{sym}.NS" if not str(sym).endswith(('.NS', '.BO')) else sym
            ticker = yf.Ticker(ticker_sym)
            info = ticker.info
            
            # Market Cap conversion to Crores
            raw_market_cap = info.get("marketCap")
            market_cap_cr = raw_market_cap / 10_000_000 if raw_market_cap else None
            
            data_list.append({
                "Symbol": sym,
                "Stock Price": info.get("currentPrice"),
                "PE Ratio": info.get("trailingPE"),
                "EPS": info.get("trailingEps"),
                "Market Cap (Cr)": market_cap_cr
            })
        except Exception:
            # Handle cases where the symbol might be invalid or API fails
            data_list.append({
                "Symbol": sym, 
                "Stock Price": None, 
                "PE Ratio": None, 
                "EPS": None, 
                "Market Cap (Cr)": None
            })
            
    return pd.DataFrame(data_list)

# --- File Upload Section ---
uploaded_file = st.file_uploader("Upload CSV (Must contain 'Symbol' and 'Industry' columns)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Check if required columns exist
    if 'Symbol' in df.columns and 'Industry' in df.columns:
        industry_list = sorted(df['Industry'].dropna().unique())
        
        # 1. Dropdown with NO default selection
        selected_industry = st.selectbox(
            "Select an Industry", 
            options=industry_list,
            index=None,
            placeholder="Choose an industry to fetch data..."
        )
        
        # 2. Logic execution only AFTER industry selection
        if selected_industry:
            industry_symbols = df[df['Industry'] == selected_industry]['Symbol'].tolist()
            
            st.divider()
            st.subheader(f"📊 Financial Summary: {selected_industry}")
            
            with st.spinner(f'Retrieving live data for {len(industry_symbols)} companies...'):
                metrics_df = get_stock_metrics(industry_symbols)
            
            if not metrics_df.empty:
                # 3. Formatted Data Display
                st.dataframe(
                    metrics_df.style.format({
                        "Stock Price": "{:.2f}",
                        "PE Ratio": "{:.2f}",
                        "EPS": "{:.2f}",
                        "Market Cap (Cr)": "{:,.2f}"
                    }), 
                    use_container_width=True
                )

                # 4. Individual Industry Download Option
                csv_data = metrics_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download {selected_industry} Metrics (CSV)",
                    data=csv_data,
                    file_name=f"{selected_industry.replace(' ', '_')}_financials.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data could be retrieved for the selected industry.")
        else:
            st.info("Please select an industry from the dropdown above to view the stock metrics.")
            
    else:
        st.error("Error: The CSV must contain columns named exactly 'Symbol' and 'Industry'.")

else:
    st.info("Waiting for CSV upload. Ensure your file contains 'Symbol' and 'Industry' columns.")
