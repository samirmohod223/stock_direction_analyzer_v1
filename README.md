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
Only after validating usefulness, consider an official broker feed such as Zerodha Kite Connect for supported live market dataI:%M:%S %p IST")
except Exception:
    age_minutes = None
    stamp_text = str(d.index[-1])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest candle close", format_price(float(last["Close"])))
m2.metric("Technical bias", label, f"Score {score:+d} / 4")
m3.metric("RSI (14)", f"{last['RSI']:.1f}" if pd.notna(last["RSI"]) else "—")
m4.metric("ATR (14)", format_price(atr))

st.caption(f"Symbol: `{symbol}` · Timeframe: {timeframe} · Latest candle timestamp: {stamp_text}")
if timeframe != "Daily":
    st.warning("Intraday data from this free source is not guaranteed real-time. Check the candle timestamp before acting.")
elif age_minutes is not None and age_minutes > 60 * 24 * 3:
    st.warning("Latest daily candle looks older than expected. The data may be stale or the market may be closed.")

# Chart
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
    name="Candles"
))
fig.add_trace(go.Scatter(x=d.index, y=d["SMA20"], name="SMA 20", line=dict(width=1.4)))
fig.add_trace(go.Scatter(x=d.index, y=d["SMA50"], name="SMA 50", line=dict(width=1.4)))
fig.update_layout(
    height=570, xaxis_rangeslider_visible=False, template="plotly_dark",
    margin=dict(l=10, r=10, t=35, b=10), legend=dict(orientation="h", y=1.02)
)
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns([1, 1])
with left:
    st.subheader("Evidence behind the bias")
    for item in evidence:
        st.write("• " + item)
    if risks:
        st.subheader("Risks / missing confirmation")
        for item in risks:
            st.write("⚠️ " + item)
    st.caption("The score is a simple rules-based summary, not a calibrated probability of price direction.")

with right:
    st.subheader("Candlestick patterns in latest candle")
    if patterns:
        for name, direction, note in patterns:
            st.write(f"**{name}** — {direction}")
            st.caption(note)
    else:
        st.write("No listed pattern detected in the latest candle.")
    st.caption("Patterns are approximate rule-based detections and should be confirmed by context and subsequent candles.")

st.subheader("Possible price range scenarios")
st.caption("ATR-based volatility bands, not a directional prediction or price target. Actual prices can move outside these ranges.")
view = scenarios.copy()
for c in ["Lower scenario", "Reference price", "Upper scenario"]:
    view[c] = view[c].map(format_price)
view["Range width (%)"] = view["Range width (%)"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
st.dataframe(view, use_container_width=True, hide_index=True)

with st.expander("Download data / inspect recent candles"):
    export = d.reset_index()
    st.download_button(
        "Download analysed candles as CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name=f"{symbol.replace('.', '_')}_{INTERVAL_MAP[timeframe]}_analysis.csv",
        mime="text/csv"
    )
    st.dataframe(d.tail(15).sort_index(ascending=False), use_container_width=True)

st.info(
    "Important limitations: this prototype does not guarantee real-time data, does not use a trained forecasting model, "
    "does not know future news, and does not place orders. Forecast ranges use recent volatility only. "
    "Test on paper first and never treat a technical bias as a buy/sell instruction."
)
