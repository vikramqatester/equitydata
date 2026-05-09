from datetime import date, timedelta
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import streamlit as st
import yfinance as yf


INTERVAL_OPTIONS = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
}


def clean_symbols(symbols: pd.Series) -> list[str]:
    """Return non-empty unique symbols while keeping the user's CSV order."""
    cleaned_symbols = []
    seen_symbols = set()

    for symbol in symbols.dropna():
        cleaned_symbol = str(symbol).strip().upper()
        if cleaned_symbol and cleaned_symbol not in seen_symbols:
            cleaned_symbols.append(cleaned_symbol)
            seen_symbols.add(cleaned_symbol)

    return cleaned_symbols


def flatten_yfinance_columns(data: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            "_".join(str(part) for part in column if part)
            for column in data.columns.to_flat_index()
        ]
    return data


def download_symbol_data(
    symbol: str,
    start_date: date,
    end_date: date,
    interval: str,
) -> tuple[pd.DataFrame | None, str | None]:
    try:
        data = yf.download(
            symbol,
            start=start_date,
            end=end_date + timedelta(days=1),
            interval=interval,
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        return None, str(exc)

    if data.empty:
        return None, "No data returned"

    data = flatten_yfinance_columns(data.reset_index())
    return data, None


def build_zip_file(downloaded_data: dict[str, pd.DataFrame]) -> BytesIO:
    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_file:
        for symbol, data in downloaded_data.items():
            safe_symbol = symbol.replace("/", "-").replace("\\", "-")
            zip_file.writestr(f"{safe_symbol}.csv", data.to_csv(index=False))

    zip_buffer.seek(0)
    return zip_buffer


def main() -> None:
    st.set_page_config(page_title="Equity Data Downloader", layout="wide")

    st.title("Equity Data Downloader")
    st.caption("Upload a CSV with a Symbol column and download one CSV per symbol.")

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    left_column, right_column = st.columns(2)
    with left_column:
        default_start = date.today() - timedelta(days=365)
        start_date = st.date_input("Start date", value=default_start)
    with right_column:
        end_date = st.date_input("End date", value=date.today())

    timeframe = st.selectbox("Time frame", list(INTERVAL_OPTIONS.keys()))

    if uploaded_file is None:
        st.info('Please upload a CSV file containing a column named "Symbol".')
        return

    try:
        input_data = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the uploaded CSV file: {exc}")
        return

    if "Symbol" not in input_data.columns:
        st.error('The uploaded CSV must contain a column named "Symbol".')
        return

    symbols = clean_symbols(input_data["Symbol"])
    if not symbols:
        st.error('The "Symbol" column does not contain any valid symbols.')
        return

    if start_date > end_date:
        st.error("Start date must be earlier than or equal to end date.")
        return

    st.write(f"Found {len(symbols)} symbol(s): {', '.join(symbols)}")

    if not st.button("Fetch data", type="primary"):
        return

    downloaded_data = {}
    failed_downloads = {}
    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, symbol in enumerate(symbols, start=1):
        status_text.write(f"Fetching {symbol}...")
        data, error = download_symbol_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=INTERVAL_OPTIONS[timeframe],
        )

        if error:
            failed_downloads[symbol] = error
        else:
            downloaded_data[symbol] = data

        progress_bar.progress(index / len(symbols))

    status_text.empty()

    if downloaded_data:
        st.success(f"Downloaded data for {len(downloaded_data)} symbol(s).")
        zip_buffer = build_zip_file(downloaded_data)
        st.download_button(
            label="Download CSV files",
            data=zip_buffer,
            file_name="equity_data.zip",
            mime="application/zip",
        )

        with st.expander("Preview downloaded data"):
            selected_symbol = st.selectbox(
                "Symbol preview",
                list(downloaded_data.keys()),
            )
            st.dataframe(downloaded_data[selected_symbol], use_container_width=True)

    if failed_downloads:
        st.warning("Some symbols could not be downloaded.")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Symbol": symbol, "Reason": reason}
                    for symbol, reason in failed_downloads.items()
                ]
            ),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
