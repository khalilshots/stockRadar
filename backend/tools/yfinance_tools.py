import yfinance as yf

def get_stock_info(ticker: str) -> dict | None:
    """Basic price/float/volume info for a ticker, or None on error."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "float_shares": info.get("floatShares"),
            "volume": info.get("regularMarketVolume"),
            "prev_close": info.get("previousClose"),
        }

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None