from tools.yfinance_tools import get_stock_info
from agents.team1.price_filter import run_price_filter
import logging
from utils.gates import check_gate
from strategies.strategy_manager import get_strategy
# This line makes logging messages actually show up in your terminal
logging.basicConfig(level=logging.WARNING)

strategy = get_strategy("Small Cap Momentum")
criteria = strategy["criteria"]

tickers = ["AAPL", "HOOD"]


for ticker in tickers:
    print(f"\n--- Processing {ticker} ---")

    stock_data = get_stock_info(ticker)
    if not stock_data:
        print(f"Failed to fetch data for {ticker}, skipping.")
        continue
    result = run_price_filter(stock_data, criteria)
    print(f"Agent result: {result}")

    if check_gate(result):
        print(f"{ticker} PASSED the price filter, moving to next step.")
    else:
        print(f"{ticker} FAILED the price filter, stopping processing for this ticker.")