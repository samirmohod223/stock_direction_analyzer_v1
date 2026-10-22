# Indian Stock Direction Analyzer — Prototype v1

A simple Streamlit dashboard that accepts an NSE ticker and displays candles, SMA20/SMA50, RSI, MACD, ATR, volume context, a few candle-pattern rules, and a transparent bullish/bearish/neutral rule score.

## Requirements
- Python 3.10 or newer
- Internet connection for Yahoo Finance data

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Then open the local URL printed by Streamlit.

## Use
- Enter a common NSE symbol such as `RELIANCE`, `TCS`, `INFY`, `SBIN`, `ITC`, `LT`, or `HDFCBANK`.
- Click **Analyse stock**.
- Choose daily or weekly candles and a history window.
- Review the chart, evidence, risks, and downloadable CSV.

## Important limitations
- Data is obtained from Yahoo Finance through `yfinance`, not a guaranteed real-time official NSE feed. Availability and delay can vary.
- This is a basic, transparent rule-based indicator, not a trained prediction model and not a probability forecast.
- Pattern rules are deliberately simple; a detected shape is not proof of future direction.
- No live news, fundamentals, Nifty/sector context, brokerage, taxes, slippage, or validated backtest is included.
- Do not use this alone to make trades. Validate data quality and backtest out-of-sample before relying on signals.

## Recommended next upgrades
1. Add symbol search and data-quality checks.
2. Add Nifty/sector relative strength and market-regime filters.
3. Add backtesting with walk-forward validation and realistic transaction costs.
4. Measure signal calibration and net returns before introducing machine learning.
5. Move to a licensed market-data provider if real-time or production use is required.
