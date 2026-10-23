import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Stock Direction Analyzer", page_icon="📈", layout="wide")

st.title("📈 Indian Stock Direction Analyzer — Free Prototype")
st.caption("Yahoo Finance data • Technical scenarios, not guaranteed predictions or investment advice")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Monitor settings")
    symbol_input = st.text_input(
        "NSE stock symbol", value="RELIANCE",
        help="Examples: RELIANCE, TCS, INFY, SBIN. NSE suffix .NS is added automatically."
    )
    timeframe = st.selectbox(
        "Timeframe",
        ["5-minute", "15-minute", "Daily"],
        index=0,
        help="Free Yahoo intraday history and availability can be limited."
    )
    refresh = st.selectbox("Auto-refresh", ["Off", "60 seconds", "5 minutes"], index=0)
    history = st.selectbox("Daily history", ["6 months", "1 year", "2 years", "5 years"], index=1)
    run = st.button("Fetch / refresh analysis", type="primary", use_container_width=True)
    st.caption("This is a free prototype. Yahoo data may be delayed, incomplete, throttled, or unavailable.")

PERIOD_MAP = {"6 months": "6mo", "1 year": "1y", "2 years": "2y", "5 years": "5y"}
INTERVAL_MAP = {"5-minute": "5m", "15-minute": "15m", "Daily": "1d"}
IST = ZoneInfo("Asia/Kolkata")

def normalise_symbol(raw):
    s = raw.strip().upper()
    if not s:
        raise ValueError("Enter an NSE stock symbol.")
    if "." not in s and "^" not in s:
        s += ".NS"
    return s

def fetch_data(symbol, tf, daily_history):
    interval = INTERVAL_MAP[tf]
    if interval == "1d":
        period = PERIOD_MAP[daily_history]
    elif interval == "5m":
        # Yahoo Finance typically limits 5-minute history to recent days.
        period = "5d"
    else:
        # Yahoo Finance typically limits 15-minute history to recent weeks.
        period = "60d"
    df = yf.download(
        symbol, period=period, interval=interval, auto_adjust=True,
        progress=False, threads=False, prepost=False
    )
    if df is None or df.empty:
        raise RuntimeError(
            "No data returned. Check the ticker, try again later, or switch timeframe. "
            "Free data providers can throttle or temporarily block requests."
        )
    # yfinance may return MultiIndex columns even for one ticker.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise RuntimeError(f"Provider response is missing columns: {', '.join(missing)}")
    df = df[needed].copy()
    for c in needed:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if len(df) < 30:
        raise RuntimeError(f"Only {len(df)} candles received; at least 30 are needed for this analysis.")
    return df

def add_indicators(df):
    d = df.copy()
    close = d["Close"]
    d["SMA20"] = close.rolling(20).mean()
    d["SMA50"] = close.rolling(50).mean()
    d["EMA12"] = close.ewm(span=12, adjust=False).mean()
    d["EMA26"] = close.ewm(span=26, adjust=False).mean()
    d["MACD"] = d["EMA12"] - d["EMA26"]
    d["MACD_signal"] = d["MACD"].ewm(span=9, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI"] = 100 - (100 / (1 + rs))
    prev_close = close.shift(1)
    tr = pd.concat([
        d["High"] - d["Low"],
        (d["High"] - prev_close).abs(),
        (d["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    d["ATR"] = tr.rolling(14).mean()
    d["VolumeAvg20"] = d["Volume"].rolling(20).mean()
    d["VolumeRatio"] = d["Volume"] / d["VolumeAvg20"].replace(0, np.nan)
    return d

def detect_patterns(d):
    if len(d) < 3:
        return []
    a, b = d.iloc[-2], d.iloc[-1]
    patterns = []
    body = abs(b["Close"] - b["Open"])
    candle_range = max(b["High"] - b["Low"], 1e-9)
    upper = b["High"] - max(b["Open"], b["Close"])
    lower = min(b["Open"], b["Close"]) - b["Low"]
    prev_body = abs(a["Close"] - a["Open"])
    # Engulfing patterns require opposite candle colours and body engulfing.
    if a["Close"] < a["Open"] and b["Close"] > b["Open"] and b["Open"] <= a["Close"] and b["Close"] >= a["Open"]:
        patterns.append(("Bullish engulfing", "Bullish", "Potential reversal; needs confirmation."))
    if a["Close"] > a["Open"] and b["Close"] < b["Open"] and b["Open"] >= a["Close"] and b["Close"] <= a["Open"]:
        patterns.append(("Bearish engulfing", "Bearish", "Potential reversal; needs confirmation."))
    if lower >= 2 * max(body, candle_range * 0.02) and upper <= candle_range * 0.25:
        patterns.append(("Hammer-like candle", "Bullish", "Long lower wick; context and next-candle confirmation matter."))
    if upper >= 2 * max(body, candle_range * 0.02) and lower <= candle_range * 0.25:
        patterns.append(("Shooting-star-like candle", "Bearish", "Long upper wick; context and next-candle confirmation matter."))
    if body / candle_range <= 0.10:
        patterns.append(("Doji / small body", "Neutral", "Indecision candle; not a direction signal by itself."))
    return patterns

def score_signal(d):
    last = d.iloc[-1]
    score = 0
    evidence = []
    risks = []
    if pd.notna(last["SMA20"]):
        if last["Close"] > last["SMA20"]:
            score += 1; evidence.append("Close is above the 20-candle average.")
        else:
            score -= 1; evidence.append("Close is below the 20-candle average.")
    if pd.notna(last["SMA50"]):
        if last["Close"] > last["SMA50"]:
            score += 1; evidence.append("Close is above the 50-candle average.")
        else:
            score -= 1; evidence.append("Close is below the 50-candle average.")
    if pd.notna(last["MACD"]) and pd.notna(last["MACD_signal"]):
        if last["MACD"] > last["MACD_signal"]:
            score += 1; evidence.append("MACD is above its signal line.")
        else:
            score -= 1; evidence.append("MACD is below its signal line.")
    if pd.notna(last["RSI"]):
        if 55 <= last["RSI"] < 70:
            score += 1; evidence.append(f"RSI {last['RSI']:.1f} shows positive momentum without being extremely overbought.")
        elif last["RSI"] < 45:
            score -= 1; evidence.append(f"RSI {last['RSI']:.1f} indicates weak momentum.")
        elif last["RSI"] >= 70:
            risks.append(f"RSI is {last['RSI']:.1f}; momentum may be overextended.")
        else:
            evidence.append(f"RSI {last['RSI']:.1f} is in a middle/neutral zone.")
    if pd.notna(last["VolumeRatio"]) and last["VolumeRatio"] >= 1.5:
        evidence.append(f"Volume is {last['VolumeRatio']:.1f}× its 20-candle average.")
    else:
        risks.append("No strong volume expansion confirmed by the current candle.")
    if score >= 2:
        label = "Bullish bias"
    elif score <= -2:
        label = "Bearish bias"
    else:
        label = "Mixed / neutral"
    return label, score, evidence, risks

def forecast_scenarios(d, timeframe):
    # ATR-based scenario bands, not a trained prediction model.
    last = d.iloc[-1]
    price = float(last["Close"])
    atr = float(last["ATR"]) if pd.notna(last["ATR"]) else np.nan
    if not np.isfinite(atr) or atr <= 0:
        returns = d["Close"].pct_change().dropna()
        atr = price * float(returns.tail(20).std()) if len(returns) >= 5 else price * 0.01
    if timeframe == "5-minute":
        horizons = [("Next 15 minutes", 3), ("Next 1 hour", 12)]
    elif timeframe == "15-minute":
        horizons = [("Next 1 hour", 4), ("Next 1 trading day", 26)]
    else:
        horizons = [("Next 1 trading day", 1), ("Next 5 trading days", 5)]
    rows = []
    for name, n in horizons:
        # Square-root-of-time scaling is a rough volatility assumption, not a directional forecast.
        move = atr * np.sqrt(n)
        rows.append({
            "Horizon": name,
            "Lower scenario": max(0, price - move),
            "Reference price": price,
            "Upper scenario": price + move,
            "Range width (%)": 200 * move / price if price else np.nan
        })
    return pd.DataFrame(rows), atr

def format_price(v):
    return f"₹{v:,.2f}"

# Refresh is user-controlled; Streamlit Community Cloud may sleep while inactive.
if refresh != "Off":
    try:
        from streamlit_autorefresh import st_autorefresh
        interval_ms = 60_000 if refresh == "60 seconds" else 300_000
        st_autorefresh(interval=interval_ms, key="market_refresh")
    except Exception:
        st.info("Auto-refresh component isn't available yet. Use the Fetch / refresh button.")

symbol = ""
try:
    symbol = normalise_symbol(symbol_input)
    with st.spinner(f"Fetching {symbol} data…"):
        raw = fetch_data(symbol, timeframe, history)
    d = add_indicators(raw)
    last = d.iloc[-1]
    label, score, evidence, risks = score_signal(d)
    patterns = detect_patterns(d)
    scenarios, atr = forecast_scenarios(d, timeframe)
except Exception as e:
    st.error(str(e))
    st.info("Try a common NSE symbol such as RELIANCE, TCS, INFY or SBIN. If this keeps failing, the free provider may be unavailable or rate-limited.")
    st.stop()

# Data freshness warning
last_stamp = d.index[-1]
try:
    if last_stamp.tzinfo is None:
        last_stamp = last_stamp.tz_localize("UTC")
    last_ist = last_stamp.tz_convert(IST)
    now_ist = datetime.now(IST)
    age_minutes = max(0, (now_ist - last_ist.to_pydatetime()).total_seconds() / 60)
    stamp_text = last_ist.strftime("%d %b %Y, %I:%M:%S %p IST")
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
