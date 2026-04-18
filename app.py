import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ===============================
# PAGE CONFIGURATION
# ===============================
st.set_page_config(page_title="Pro Terminal", layout="wide", page_icon="📈")
st.title("🧠 CA Dilip's Pro Terminal")

# ===============================
# CORE STRATEGY LOGIC
# ===============================
def clean_dataframe(df):
    if df is None or df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

def scalping_logic_9_15(df):
    df = clean_dataframe(df)
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA15"] = df["Close"].ewm(span=15).mean()
    df_clean = df.dropna()
    if df_clean.empty: return df, "NO DATA", 0, "Wait", "Insufficient data."
    df = df_clean
    buy_cross = (df['EMA9'] > df['EMA15']) & (df['EMA9'].shift(1) <= df['EMA15'].shift(1))
    sell_cross = (df['EMA9'] < df['EMA15']) & (df['EMA9'].shift(1) >= df['EMA15'].shift(1))
    df['Buy_Signal'] = df['Low'][buy_cross] * 0.998
    df['Sell_Signal'] = df['High'][sell_cross] * 1.002
    curr = df.iloc[-1]
    price, e9, e15 = float(curr["Close"]), float(curr["EMA9"]), float(curr["EMA15"])
    signal = "BUY" if (e9 > e15 and price > e9) else "SELL" if (e9 < e15 and price < e9) else "NO TRADE"
    return df, signal, price, f"{round(price, 2)}", f"EMA9 ({round(e9,1)}) vs EMA15 ({round(e15,1)})"

def swing_logic_10_ema(df):
    df = clean_dataframe(df)
    df["EMA10"] = df["Close"].ewm(span=10).mean()
    df_clean = df.dropna()
    if df_clean.empty: return df, "NO DATA", 0, "Wait", "Insufficient data."
    df = df_clean
    buy_cross = (df['Close'].shift(1) < df['EMA10'].shift(1)) & (df['Close'] > df['EMA10'])
    sell_cross = (df['Close'].shift(1) > df['EMA10'].shift(1)) & (df['Close'] < df['EMA10'])
    df['Buy_Signal'] = df['Low'][buy_cross] * 0.995
    df['Sell_Signal'] = df['High'][sell_cross] * 1.005
    curr, prev = df.iloc[-1], df.iloc[-2]
    price, e10 = float(curr["Close"]), float(curr["EMA10"])
    p_close, p_e10 = float(prev["Close"]), float(prev["EMA10"])
    signal = "BUY (JACKPOT)" if (p_close < p_e10 and price > e10) else "SELL (JACKPOT)" if (p_close > p_e10 and price < e10) else "NO TRADE"
    return df, signal, price, f"{round(price, 2)}", f"10 EMA at {round(e10,2)}"

def buffett_logic_active(df, symbol):
    df = clean_dataframe(df)
    df["SMA200"] = df["Close"].rolling(window=200).mean()
    df_clean = df.dropna()
    if df_clean.empty: return df, "TECHNICAL", float(df.iloc[-1]["Close"]), "N/A", "Need 200 days."
    price, sma200 = float(df.iloc[-1]["Close"]), float(df["SMA200"].iloc[-1])
    return df, "INVEST" if price > sma200 else "WATCH", price, f"{round(sma200, 2)}", "Buffett View Active"

# ===============================
# SIDEBAR & RISK MANAGER
# ===============================
with st.sidebar:
    st.header("⚙️ Controls")
    market_type = st.selectbox("Asset Class", ["Indian Stocks (NSE)", "Forex", "Commodities"])
    
    st.divider()
    st.subheader("🛡️ Risk Manager")
    total_cap = st.number_input("Total Capital (₹)", value=100000, step=5000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0, 0.5)
    
    st.divider()
    comm_map = {"GOLD": "GC", "SILVER": "SI", "COPPER": "HG", "CRUDE": "CL", "NATGAS": "NG"}
    fx_map = {"EUR": "EURUSD", "GBP": "GBPUSD", "JPY": "USDJPY", "INR": "USDINR"}
    
    raw_input = st.text_input("Search Name", value="RELIANCE").upper().strip().replace(" ", "")
    mode = st.selectbox("Strategy", ["Scalping (9/15)", "Swing (10 EMA)", "Long Term (Buffett)"])
    
    if st.button("Generate Fundamental Audit", type="primary"):
        st.session_state['show_audit'] = True

# ===============================
# DATA FETCHING
# ===============================
if raw_input:
    clean_sym = raw_input
    curr_prefix = "₹" if market_type == "Indian Stocks (NSE)" else "$"
    
    if market_type == "Indian Stocks (NSE)":
        legacy = {"TATAMOTORS": "TMPV", "TATA": "TMPV", "IRADA": "IREDA"}
        clean_sym = legacy.get(clean_sym, clean_sym)
        fetch_sym = clean_sym + ".NS" if ".NS" not in clean_sym else clean_sym
    elif market_type == "Forex":
        clean_sym = fx_map.get(clean_sym, clean_sym)
        fetch_sym = clean_sym + "=X" if "=X" not in clean_sym else clean_sym
    else: # Commodities
        clean_sym = comm_map.get(clean_sym, clean_sym)
        fetch_sym = clean_sym + "=F" if "=F" not in clean_sym else clean_sym

    interval, period = ("15m", "5d") if "Scalping" in mode else ("1d", "1y")
    raw_df = yf.download(fetch_sym, period=period, interval=interval, auto_adjust=True, progress=False)

    if not raw_df.empty:
        if "Scalping" in mode: df, signal, price, entry, reason = scalping_logic_9_15(raw_df)
        elif "Swing" in mode: df, signal, price, entry, reason = swing_logic_10_ema(raw_df)
        else: df, signal, price, entry, reason = buffett_logic_active(raw_df, fetch_sym)

        # ATR & Quantity Math
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        atr = float(df['ATR'].iloc[-1])
        sl_price = (price - atr) if "BUY" in signal else (price + atr) if "SELL" in signal else 0
        risk_amt = total_cap * (risk_pct / 100)
        risk_per_sh = abs(price - sl_price) if sl_price != 0 else 0
        qty = int(risk_amt / risk_per_sh) if risk_per_sh > 0 else 0

        # UI DASHBOARD
        dec = 4 if market_type == "Forex" else 2
        c1, c2, c3 = st.columns(3)
        c1.metric("Price", f"{curr_prefix}{price:,.{dec}f}")
        c2.metric("Signal", signal)
        c3.metric("Qty to Buy", f"{qty} units")

        st.write("")
        c4, c5 = st.columns(2)
        c4.metric("Target (2R)", f"{curr_prefix}{round(price + 2*atr if 'BUY' in signal else price - 2*atr, dec)}" if "TRADE" in signal else "Wait")
        c5.metric("Stop Loss", f"{curr_prefix}{round(sl_price, dec)}" if sl_price != 0 else "Wait")
        
        st.info(f"🛡️ Risk: {curr_prefix}{risk_amt:,.0f} | 💡 {reason}")

        # CHARTING
        display_df = df.tail(80)
        fig = go.Figure(data=[go.Candlestick(x=display_df.index, open=display_df['Open'], high=display_df['High'], low=display_df['Low'], close=display_df['Close'], name='Price')])
        
        if "Scalping" in mode:
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA9'], line=dict(color='yellow', width=1), name='EMA 9'))
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA15'], line=dict(color='cyan', width=1), name='EMA 15'))
        elif "Swing" in mode:
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA10'], line=dict(color='orange', width=2), name='EMA 10'))
        
        if 'Buy_Signal' in display_df.columns:
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Buy_Signal'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='Buy'))
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Sell_Signal'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'), name='Sell'))

        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

# ===============================
# FUNDAMENTAL AUDIT MODAL
# ===============================
if st.session_state.get('show_audit', False):
    @st.dialog("Fundamental Audit Report", width="large")
    def show_audit_dialog():
        st.markdown(f"### 📑 Audit Report: **{fetch_sym}**")
        try:
            info = yf.Ticker(fetch_sym).info
            def fmt(v, k="num"):
                if v is None: return "N/A"
                if k == "curr": return f"{curr_prefix}{v:,.2f}"
                if k == "pct": return f"{v * 100:.2f}%"
                return f"{v:.2f}"

            c1, c2, c3 = st.columns(3)
            c1.metric("Current Price", fmt(info.get('currentPrice'), "curr"))
            eps, bvps = info.get('trailingEps'), info.get('bookValue')
            graham = (22.5 * eps * bvps)**0.5 if eps and bvps and eps > 0 else 0
            c2.metric("Graham Value", fmt(graham, "curr"))
            c3.metric("ROE", fmt(info.get('returnOnEquity'), "pct"))

            st.divider()
            st.subheader("Profitability & Debt")
            d1, d2, d3 = st.columns(3)
            d1.metric("Debt-to-Equity", fmt(info.get('debtToEquity')))
            d2.metric("Operating Margin", fmt(info.get('operatingMargins'), "pct"))
            d3.metric("Free Cash Flow", fmt(info.get('freeCashflow')))
            
            if st.button("Close Audit"):
                st.session_state['show_audit'] = False
                st.rerun()
        except: st.error("Audit data unavailable for this asset class.")

    show_audit_dialog()
