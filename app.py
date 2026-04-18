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
# DATA CLEANING & LOGIC
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
    if df_clean.empty:
        return df, "NO DATA", 0, "N/A", "Insufficient data for Scalping Strategy."
    df = df_clean
    
    buy_cross = (df['EMA9'] > df['EMA15']) & (df['EMA9'].shift(1) <= df['EMA15'].shift(1))
    sell_cross = (df['EMA9'] < df['EMA15']) & (df['EMA9'].shift(1) >= df['EMA15'].shift(1))
    
    df['Buy_Signal'] = df['Low'][buy_cross] * 0.995
    df['Sell_Signal'] = df['High'][sell_cross] * 1.005

    curr = df.iloc[-1]
    price, e9, e15 = float(curr["Close"]), float(curr["EMA9"]), float(curr["EMA15"])
    
    signal = "BUY" if (e9 > e15 and price > e9) else "SELL" if (e9 < e15 and price < e9) else "NO TRADE"
    entry_point = f"{round(price, 4)}" if signal != "NO TRADE" else "Wait for Crossover"
    reason = f"EMA9 ({round(e9,2)}) {' > ' if e9>e15 else ' < '} EMA15 ({round(e15,2)}) | Price vs EMA9: {round(price-e9,2)}"
    
    return df, signal, price, entry_point, reason

def swing_logic_10_ema(df):
    df = clean_dataframe(df)
    df["EMA10"] = df["Close"].ewm(span=10).mean()
    
    df_clean = df.dropna()
    if df_clean.empty:
        return df, "NO DATA", 0, "N/A", "Insufficient data for Swing Strategy."
    df = df_clean
    
    buy_cross = (df['Close'].shift(1) < df['EMA10'].shift(1)) & (df['Close'] > df['EMA10'])
    sell_cross = (df['Close'].shift(1) > df['EMA10'].shift(1)) & (df['Close'] < df['EMA10'])
    
    df['Buy_Signal'] = df['Low'][buy_cross] * 0.995
    df['Sell_Signal'] = df['High'][sell_cross] * 1.005

    curr, prev = df.iloc[-1], df.iloc[-2]
    price, e10 = float(curr["Close"]), float(curr["EMA10"])
    p_close, p_e10 = float(prev["Close"]), float(prev["EMA10"])

    signal = "BUY (JACKPOT)" if (p_close < p_e10 and price > e10) else "SELL (JACKPOT)" if (p_close > p_e10 and price < e10) else "NO TRADE"
    entry_point = f"{round(price, 4)}" if signal != "NO TRADE" else "Wait for Reversal"
    reason = f"Prev C({round(p_close,2)}) vs E10({round(p_e10,2)}) | Curr C({round(price,2)}) vs E10({round(e10,2)})"
    
    return df, signal, price, entry_point, reason

def buffett_logic_active(df, symbol):
    df = clean_dataframe(df)
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["SMA200"] = df["Close"].rolling(window=200).mean()
    
    df_clean = df.dropna()
    if df_clean.empty:
        last_price = float(df.iloc[-1]["Close"]) if not df.empty else 0
        return df, "INSUFFICIENT DATA", last_price, "N/A", "Not enough historical data to calculate the 200 DMA. Need at least 200 trading days."
    
    df = df_clean
    df['Buy_Signal'] = float('nan')
    df['Sell_Signal'] = float('nan')
    
    price = float(df.iloc[-1]["Close"])
    sma200 = float(df["SMA200"].iloc[-1])
    
    try:
        info = yf.Ticker(symbol).info
        roe = (info.get('returnOnEquity') or 0) * 100
        de = info.get('debtToEquity') or 0
        pe = info.get('trailingPE') or 0
        eps = info.get('trailingEps') or 0
        bvps = info.get('bookValue') or 0
        
        # If data is completely missing (like for Forex/Commodities), it fails safely
        if not info.get('trailingEps'):
            return df, "TECHNICAL ONLY", price, f"Wait for {round(sma200, 2)} (200 DMA)", f"Fundamentals NA for this asset class. Trading {'Above' if price > sma200 else 'Below'} 200 DMA."
            
        graham_value = (22.5 * eps * bvps) ** 0.5 if (eps > 0 and bvps > 0) else 0
        exp_gain = ((graham_value - price) / price) * 100 if graham_value > 0 else 0
        
        score = sum([roe >= 15, de <= 50, 0 < pe <= 25])
        
        if score == 3:
            if price < sma200 and exp_gain > 15:
                action = "STRONG INVEST"
                entry_point = f"{round(price, 2)} (Now)"
            else:
                action = "HOLD / SIP"
                entry_point = f"{round(sma200, 2)} (200 DMA)"
        elif score == 2:
            action = "WATCHLIST"
            entry_point = f"{round(sma200, 2)} (200 DMA)"
        else:
            action = "DIVEST / AVOID"
            entry_point = "N/A (Fundamentals Weak)"

        reason = f"ROE: {round(roe,2)}% | D/E: {round(de,2)} | P/E: {round(pe,2)} | Tech: {'Above' if price > sma200 else 'Below'} 200 DMA"
    except Exception:
        action, entry_point, reason = "TECHNICAL ONLY", f"Wait for {round(sma200, 2)}", f"Fundamental Data Unavailable. Trading {'Above' if price > sma200 else 'Below'} 200 DMA."

    return df, action, price, entry_point, reason

# ===============================
# UI LAYOUT & INTERACTIVITY
# ===============================
# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    # NEW: Asset Class Selector
    market_type = st.selectbox("Asset Class", ["Indian Stocks (NSE)", "Forex", "Commodities"])
    
    symbol = st.text_input("Symbol", value="RELIANCE" if market_type == "Indian Stocks (NSE)" else "EURUSD" if market_type == "Forex" else "GC").upper()
    
    # Helper Text
    if market_type == "Forex":
        st.caption("Try: EURUSD, USDJPY, GBPUSD, USDINR")
    elif market_type == "Commodities":
        st.caption("Try: GC (Gold), CL (Crude Oil), SI (Silver), NG (Nat Gas)")
    
    mode = st.selectbox("Strategy Mode", ["Scalping (9/15)", "Swing (10 EMA)", "Long Term (Buffett)"])
    
    if st.button("Generate Fundamental Audit", type="primary"):
        if market_type != "Indian Stocks (NSE)":
            st.warning("⚠️ Fundamentals (P/E, ROE, etc.) only apply to Stocks. Audit report may be blank for Forex/Commodities.")
        st.session_state['show_audit'] = True
        
    with st.expander("Warren Buffett Checklist"):
        st.markdown("""
        1. **Understandable Business**
        2. **Durable Moat** (Brand, Network)
        3. **Management Integrity**
        4. **ROE > 15%**
        5. **Debt-to-Equity < 0.5**
        6. **Margin of Safety**
        """)

# Main Execution
if symbol:
    clean_symbol = symbol.strip().replace(" ", "").upper()
    
    # Currency Formatting Logic
    curr_symbol = "₹" if market_type == "Indian Stocks (NSE)" else "$" if market_type == "Commodities" else ""
    
    # TICKER FORMATTING ENGINE
    if market_type == "Indian Stocks (NSE)":
        legacy_tickers = {"TATAMOTORS": "TMPV", "TATA": "TMPV", "IRADA": "IREDA", "COCHINSHIPYARD": "COCHINSHIP", "COCHIN": "COCHINSHIP"}
        if clean_symbol in legacy_tickers:
            clean_symbol = legacy_tickers[clean_symbol]
        fetch_sym = clean_symbol + '.NS' if not any(x in clean_symbol for x in ['.NS', '.BO', '=X', '^']) else clean_symbol
    
    elif market_type == "Forex":
        fetch_sym = clean_symbol + '=X' if '=X' not in clean_symbol else clean_symbol
        
    elif market_type == "Commodities":
        fetch_sym = clean_symbol + '=F' if '=F' not in clean_symbol else clean_symbol

    # Strategy Timeframes
    interval, period = ("15m", "5d") if "Scalping" in mode else ("1d", "1y") if "Swing" in mode else ("1d", "2y")
    
    with st.spinner(f"Fetching data for {fetch_sym}..."):
        raw_df = yf.download(fetch_sym, period=period, interval=interval, auto_adjust=True, progress=False)

    if raw_df is None or raw_df.empty:
        st.error(f"Data Error: No data found for {fetch_sym}. Check if valid.")
    else:
        # Apply Logic
        if "Scalping" in mode:
            df, signal, price, entry_point, reason = scalping_logic_9_15(raw_df)
        elif "Swing" in mode:
            df, signal, price, entry_point, reason = swing_logic_10_ema(raw_df)
        else:
            df, signal, price, entry_point, reason = buffett_logic_active(raw_df, fetch_sym)

        sl_text = "N/A"
        tgt_text = "N/A"
        
        if "Long Term" not in mode and df is not None and len(df) >= 14:
            df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
            atr = float(df['ATR'].iloc[-1])
            
            if "BUY" in signal:
                sl_text = f"{curr_symbol}{round(price - atr, 4)} (-1 ATR)"
                tgt_text = f"{curr_symbol}{round(price + (2 * atr), 4)} (+2 ATR)"
            elif "SELL" in signal:
                sl_text = f"{curr_symbol}{round(price + atr, 4)} (+1 ATR)"
                tgt_text = f"{curr_symbol}{round(price - (2 * atr), 4)} (-2 ATR)"
            else:
                sl_text = "Wait for Signal"
                tgt_text = "Wait for Signal"
        elif "Long Term" in mode:
            sl_text = "Long Term Hold"
            tgt_text = "See Audit Report"

        col1, col2, col3, col4, col5 = st.columns(5)
        # Use 4 decimal places for Forex since pip movements are tiny
        decimals = 4 if market_type == "Forex" else 2
        col1.metric("Current Price", f"{curr_symbol}{price:,.{decimals}f}")
        col2.metric("Action Signal", signal)
        col3.metric("Entry Point", f"{curr_symbol}{entry_point}")
        col4.metric("Target Exit", tgt_text)
        col5.metric("Stop Loss", sl_text)
        
        st.info(reason)

        st.subheader(f"{fetch_sym} Chart")
        
        if df is not None and not df.empty:
            display_df = df.tail(100)
            
            fig = go.Figure()
            
            fig.add_trace(go.Candlestick(x=display_df.index, open=display_df['Open'], high=display_df['High'], 
                                         low=display_df['Low'], close=display_df['Close'], name='Price'))
            
            if "Scalping" in mode and "EMA9" in display_df.columns:
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA9'], line=dict(color='yellow', width=1), name='EMA 9'))
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA15'], line=dict(color='cyan', width=1), name='EMA 15'))
            elif "Swing" in mode and "EMA10" in display_df.columns:
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA10'], line=dict(color='orange', width=2), name='EMA 10'))
            elif "Long Term" in mode and "SMA200" in display_df.columns:
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['SMA50'], line=dict(color='cyan', width=1), name='SMA 50'))
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['SMA200'], line=dict(color='magenta', width=2), name='SMA 200'))

            if 'Buy_Signal' in display_df.columns and not display_df['Buy_Signal'].isna().all():
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Buy_Signal'], mode='markers', 
                                         marker=dict(symbol='triangle-up', size=15, color='lime'), name='Buy'))
            if 'Sell_Signal' in display_df.columns and not display_df['Sell_Signal'].isna().all():
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Sell_Signal'], mode='markers', 
                                         marker=dict(symbol='triangle-down', size=15, color='red'), name='Sell'))

            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

# ===============================
# AUDIT MODAL HANDLING
# ===============================
if st.session_state.get('show_audit', False):
    @st.dialog("Fundamental Audit Report", width="large")
    def show_audit_dialog():
        st.markdown(f"### 📑 Comprehensive Financial Audit: **{clean_symbol}**")
        
        with st.spinner("Pulling deep fundamental data..."):
            try:
                info = yf.Ticker(fetch_sym).info
                
                def fmt(val, kind="num"):
                    if val is None or pd.isna(val): return "N/A"
                    try:
                        v = float(val)
                        if kind == "curr": return f"{curr_symbol}{v:,.2f}"
                        if kind == "pct": return f"{v * 100:.2f}%"
                        if kind == "x": return f"{v:.2f}x"
                        if kind == "large_curr": 
                            if abs(v) >= 1e7: return f"{curr_symbol}{v/1e7:,.2f} Cr"
                            return f"{curr_symbol}{v:,.0f}"
                        return f"{v:.2f}"
                    except:
                        return "N/A"

                current_price = info.get('currentPrice')
                if current_price is None and 'raw_df' in locals() and not raw_df.empty:
                    current_price = float(raw_df.iloc[-1]['Close'])
                elif current_price is None:
                    current_price = 0
                    
                eps = info.get('trailingEps')
                bvps = info.get('bookValue')
                
                graham_val = 0
                if eps and bvps and float(eps) > 0 and float(bvps) > 0:
                    graham_val = (22.5 * float(eps) * float(bvps)) ** 0.5
                
                exp_return = 0
                if graham_val > 0 and current_price > 0:
                    exp_return = (graham_val - current_price) / current_price

                st.subheader("📊 Valuation & Pricing")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Price", fmt(current_price, "curr"))
                c2.metric("Graham Fair Value", fmt(graham_val, "curr") if graham_val else "N/A")
                c3.metric("Trailing P/E", fmt(info.get('trailingPE'), "x"))
                c4.metric("Price to Book (P/B)", fmt(info.get('priceToBook'), "x"))
                
                if graham_val > 0:
                    if exp_return > 0:
                        st.success(f"**Undervalued:** Asset is trading below Graham intrinsic value. Expected Return: **{fmt(exp_return, 'pct')}**")
                    else:
                        st.error(f"**Overvalued:** Asset is trading above Graham intrinsic value. Premium: **{fmt(abs(exp_return), 'pct')}**")
                elif market_type != "Indian Stocks (NSE)":
                    st.info("Valuation metrics (Graham Value, P/E, P/B) are not applicable to Forex and Commodities.")
                
                st.divider()
                
                st.subheader("💰 Profitability & Returns")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Return on Equity (ROE)", fmt(info.get('returnOnEquity'), "pct"))
                c2.metric("Return on Assets (ROA)", fmt(info.get('returnOnAssets'), "pct"))
                c3.metric("Operating Margin", fmt(info.get('operatingMargins'), "pct"))
                c4.metric("Profit Margin", fmt(info.get('profitMargins'), "pct"))
                
                st.divider()
                
                st.subheader("⚖️ Solvency & Cash Flow")
                c1, c2, c3 = st.columns(3)
                c1.metric("Debt-to-Equity", fmt(info.get('debtToEquity'), "num"))
                c2.metric("Current Ratio", fmt(info.get('currentRatio'), "x"))
                c3.metric("Free Cash Flow", fmt(info.get('freeCashflow'), "large_curr"))

                st.divider()

                st.subheader("📈 Market Profile")
                c1, c2, c3 = st.columns(3)
                c1.metric("Market Cap", fmt(info.get('marketCap'), "large_curr"))
                c2.metric("Dividend Yield", fmt(info.get('dividendYield'), "pct"))
                c3.metric("Beta (1Y)", fmt(info.get('beta'), "num"))

                st.write("")
                if st.button("Close Audit", type="primary"):
                    st.session_state['show_audit'] = False
                    st.rerun()

            except Exception as e:
                st.error(f"Failed to fetch detailed audit data.\nError Details: {e}")
            
    show_audit_dialog()
