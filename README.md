Stock Direction Analyzer — Free Upgrade
A Streamlit prototype for Indian NSE stocks using Yahoo Finance data. Designed to be deployable from GitHub and manageable on an Android phone.
Features
NSE symbols such as RELIANCE, TCS, INFY, SBIN (automatically adds .NS)
5-minute, 15-minute and daily chart views
Candlestick chart with SMA 20 and SMA 50
RSI, MACD, ATR and relative volume checks
Approximate candle pattern detection: bullish/bearish engulfing, hammer-like, shooting-star-like and doji
Rules-based bullish/bearish/mixed technical bias
ATR-based possible price-range scenarios (not a directional price forecast)
Optional auto-refresh while the app is open
CSV download
Important data limitations
This free version uses Yahoo Finance via yfinance. Free intraday data can be delayed, incomplete, throttled, temporarily unavailable, and has limited history. The app shows the timestamp of the latest candle. Do not rely on it for real-time trading decisions.
The displayed scenario ranges are based on recent ATR/volatility. They are not a trained prediction model, not calibrated probabilities, and not guaranteed price targets. No auto-trading is implemented.
Deploy on Streamlit Community Cloud from Android
Download and unzip the ZIP on your phone.
Open your existing GitHub repository.
Remove/replace the existing app.py and requirements.txt with the files from this folder. Keep the README if you wish.
Commit the changes.
Open your app in Streamlit Community Cloud. It should redeploy automatically. If not, open app settings and choose Reboot app.
Wait for it to finish loading, then test RELIANCE with the 5-minute timeframe. Check the candle timestamp.
Requirements
requirements.txt installs the required packages. No API key or secret is required.
Next steps after prototype
Record forecasts and compare with subsequent prices (out-of-sample evaluation)
Add a more robust backtesting module with transaction costs and slippage
Only after validating usefulness, consider an official broker feed such as Zerodha Kite Connect for supported live market data
