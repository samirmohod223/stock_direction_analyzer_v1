import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date

st.set_page_config(page_title="Stock Direction Analyzer", page_icon="📈", layout="wide")

st.title("📈 Indian Stock Direction Analyzer")
st.caption("Prototype v1 • Technical evidence, not a guaranteed prediction or investment advice")

with st.sidebar:
    st.header("Analysis settings")
    symbol_input = st.text_input("NSE symbol", value="RELIANCE", help="Enter a symbol without .NS, e.g. TCS, INFY, SBIN, RELIANCE")
    period = st.selectbox("History to analyse", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("Chart timeframe", ["1d", "1wk"], index=0, format_func=lambda x: {"1d":"Daily candles","1wk":"Weekly candles"}[x])
    st.caption("Yahoo Finance symbols for NSE usually use the .NS suffix. BSE symbols and some tickers may need separate handling.")
    run = st.button("Analyse stock", type="primary", use_container_width=True)

def fetch_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = symbol.strip().upper()
    if not ticker:
        raise ValueError("Enter a stock symbol.")
    yf_symbol = ticker if "." in ticker else f"{ticker}.NS"
    data = yf.download(
        yf_symbol, period=period, interval=interval,
        auto_adjust=True, progress=False, threads=False
    )
    if data is None or data.empty:
        raise ValueError(f"No data returned for {yf_symbol}. Check the symbol or try another NSE symbol.")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(set(data.columns)):
        raise ValueError(f"Market data is missing required fields. Returned columns: {list(data.columns)}")
    data = data.loc[:, ["Open", "High", "Low", "Close", "Volume"]].copy()
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    data = data[~data.index.duplicated(keep="last")].sort_index()
    if len(data) < 60:
        raise ValueError("Not enough history to calculate the indicators reliably.")
    return data

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    c, h, l, o, v = x["Close"], x["High"], x["Low"], x["Open"], x["Volume"]
    x["SMA20"] = c.rolling(20).mean()
    x["SMA50"] = c.rolling(50).mean()
    x["EMA12"] = c.ewm(span=12, adjust=False).mean()
    x["EMA26"] = c.ewm(span=26, adjust=False).mean()
    x["MACD"] = x["EMA12"] - x["EMA26"]
    x["MACD_signal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    x["RSI"] = 100 - (100 / (1 + rs))
    x["RSI"] = x["RSI"].fillna(100).where(loss.eq(0), x["RSI"])
    x["ATR"] = pd.concat([
        h-l, (h-c.shift()).abs(), (l-c.shift()).abs()
    ], axis=1).max(axis=1).rolling(14).mean()
    x["Volume20"] = v.rolling(20).mean()
    x["VolRatio"] = v / x["Volume20"].replace(0, np.nan)

    prev_o, prev_c = o.shift(1), c.shift(1)
    body = (c-o).abs()
    prev_body = (prev_c-prev_o).abs()
    candle_range = (h-l).replace(0, np.nan)
    lower_shadow = pd.concat([o, c], axis=1).min(axis=1)-l
    upper_shadow = h-pd.concat([o, c], axis=1).max(axis=1)
    x["Pattern"] = ""
    bullish_engulf = (prev_c < prev_o) & (c > o) & (o <= prev_c) & (c >= prev_o)
    bearish_engulf = (prev_c > prev_o) & (c < o) & (o >= prev_c) & (c <= prev_o)
    hammer = (lower_shadow >= 2*body) & (upper_shadow <= body*0.6) & (body/candle_range <= 0.4)
    shooting_star = (upper_shadow >= 2*body) & (lower_shadow <= body*0.6) & (body/candle_range <= 0.4)
    doji = body/candle_range <= 0.1
    x.loc[bullish_engulf, "Pattern"] = "Bullish engulfing"
    x.loc[bearish_engulf, "Pattern"] = "Bearish engulfing"
    x.loc[hammer, "Pattern"] = "Hammer"
    x.loc[shooting_star, "Pattern"] = "Shooting star"
    x.loc[doji, "Pattern"] = "Doji"
    return x

def score_latest(x: pd.DataFrame):
    row = x.iloc[-1]
    score = 0
    evidence = []
    risks = []
    # Trend
    if pd.notna(row["SMA20"]) and pd.notna(row["SMA50"]):
        if row["Close"] > row["SMA20"] > row["SMA50"]:
            score += 2; evidence.append("Price is above the 20-day average, which is above the 50-day average.")
        elif row["Close"] < row["SMA20"] < row["SMA50"]:
            score -= 2; evidence.append("Price is below the 20-day average, which is below the 50-day average.")
        elif row["Close"] > row["SMA20"]:
            score += 1; evidence.append("Price is above its 20-period average.")
        elif row["Close"] < row["SMA20"]:
            score -= 1; evidence.append("Price is below its 20-period average.")
    # MACD
    if pd.notna(row["MACD"]) and pd.notna(row["MACD_signal"]):
        if row["MACD"] > row["MACD_signal"]:
            score += 1; evidence.append("MACD is above its signal line (positive momentum evidence).")
        else:
            score -= 1; evidence.append("MACD is below its signal line (negative momentum evidence).")
    # RSI
    if pd.notna(row["RSI"]):
        if 50 <= row["RSI"] <= 68:
            score += 1; evidence.append(f"RSI is {row['RSI']:.1f}, consistent with positive but not extreme momentum.")
        elif row["RSI"] < 40:
            score -= 1; evidence.append(f"RSI is {row['RSI']:.1f}, indicating weak momentum; oversold conditions can still fall further.")
        elif row["RSI"] > 75:
            risks.append(f"RSI is {row['RSI']:.1f}; the stock may be stretched and vulnerable to a pullback.")
    # Volume
    if pd.notna(row["VolRatio"]):
        if row["VolRatio"] >= 1.5 and row["Close"] > row["Open"]:
            score += 1; evidence.append(f"Latest candle rose on {row['VolRatio']:.1f}× its 20-period average volume.")
        elif row["VolRatio"] >= 1.5 and row["Close"] < row["Open"]:
            score -= 1; evidence.append(f"Latest candle fell on {row['VolRatio']:.1f}× its 20-period average volume.")
    # Latest candle pattern is weak evidence only
    pattern = row["Pattern"] if isinstance(row["Pattern"], str) else ""
    if pattern == "Bullish engulfing":
        score += 1; evidence.append("Latest candle meets a bullish-engulfing rule; confirmation is still needed.")
    elif pattern == "Bearish engulfing":
        score -= 1; evidence.append("Latest candle meets a bearish-engulfing rule; confirmation is still needed.")
    elif pattern in ("Hammer", "Shooting star", "Doji"):
        risks.append(f"Latest candle was classified as {pattern}; context and following candles matter.")
    if pd.notna(row["ATR"]) and row["Close"] > 0:
        atr_pct = row["ATR"] / row["Close"] * 100
        if atr_pct >= 4:
            risks.append(f"ATR is {atr_pct:.1f}% of price, suggesting elevated recent volatility.")
    else:
        atr_pct = np.nan

    label = "Bullish" if score >= 2 else ("Bearish" if score <= -2 else "Neutral / mixed")
    return score, label, evidence, risks, atr_pct

if "analysis_df" not in st.session_state:
    st.session_state.analysis_df = None
    st.session_state.analysis_symbol = None

if run:
    try:
        with st.spinner("Fetching market data and calculating indicators..."):
            raw = fetch_data(symbol_input, period, interval)
            analysed = add_indicators(raw)
            st.session_state.analysis_df = analysed
            st.session_state.analysis_symbol = symbol_input.strip().upper()
    except Exception as e:
        st.error(str(e))

df = st.session_state.analysis_df
symbol = st.session_state.analysis_symbol

if df is None:
    st.info("Enter an NSE symbol in the sidebar and select **Analyse stock** to begin.")
    st.markdown("**Try:** RELIANCE, TCS, INFY, SBIN, ITC, LT, HDFCBANK")
    st.stop()

score, label, evidence, risks, atr_pct = score_latest(df)
latest = df.iloc[-1]
prev_close = df["Close"].iloc[-2]
change = (latest["Close"] / prev_close - 1) * 100
horizon_name = "daily" if interval == "1d" else "weekly"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest adjusted close", f"₹{latest['Close']:,.2f}", f"{change:+.2f}% vs previous {horizon_name} close")
c2.metric("Directional bias", label, f"Rule score: {score:+d}")
c3.metric("RSI (14)", f"{latest['RSI']:.1f}" if pd.notna(latest["RSI"]) else "—")
c4.metric("ATR (14)", f"₹{latest['ATR']:.2f}" if pd.notna(latest["ATR"]) else "—",
          f"{atr_pct:.2f}% of price" if pd.notna(atr_pct) else None)

st.caption(f"Symbol: {symbol if '.' in symbol else symbol + '.NS'} • Last data candle: {df.index[-1].strftime('%Y-%m-%d')} • Data source: Yahoo Finance via yfinance. Data may be delayed, incomplete, or unavailable.")

tab1, tab2, tab3 = st.tabs(["Chart & signals", "Evidence & risks", "Recent data"])
with tab1:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Candles"))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line=dict(width=1.4)))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(width=1.4)))
    fig.update_layout(height=620, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=20,b=10), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI 14"))
    fig2.add_hline(y=70, line_dash="dash")
    fig2.add_hline(y=30, line_dash="dash")
    fig2.update_layout(height=230, yaxis_range=[0,100], margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig2, use_container_width=True)
    if latest["Pattern"]:
        st.write(f"**Latest candle pattern detected:** {latest['Pattern']}")
    else:
        st.write("**Latest candle pattern detected:** No supported named pattern matched the current rules.")
with tab2:
    st.subheader(f"Current technical bias: {label}")
    st.write("This is a transparent rule-based score, not a trained forecasting model. It does not estimate a validated probability of future returns.")
    st.markdown("**Evidence**")
    if evidence:
        for item in evidence: st.write(f"- {item}")
    else:
        st.write("- Not enough indicator evidence to form a directional view.")
    st.markdown("**Risks / caveats**")
    if risks:
        for item in risks: st.warning(item)
    else:
        st.write("- No special risk flag triggered by the simple rules; this does not mean risk is low.")
    st.write("- The signal can reverse quickly and does not include live news, company fundamentals, broad-market context, brokerage, taxes or slippage.")
    st.write("- Candlestick patterns are descriptive, not inherently predictive. Confirm with price context and test the rules before using real money.")
with tab3:
    show_cols = ["Open","High","Low","Close","Volume","SMA20","SMA50","RSI","MACD","MACD_signal","ATR","VolRatio","Pattern"]
    st.dataframe(df[show_cols].tail(40).sort_index(ascending=False), use_container_width=True)
    csv = df.to_csv().encode("utf-8")
    st.download_button("Download analysed data as CSV", data=csv, file_name=f"{symbol.replace('.','_')}_analysis.csv", mime="text/csv")

st.divider()
st.caption("Prototype limitations: Yahoo Finance is a convenient research source, not a guaranteed real-time or official NSE feed. Validate data quality, licensing, and symbol mappings before relying on it. Do not trade solely on this signal.")
