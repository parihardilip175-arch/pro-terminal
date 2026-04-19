import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ===============================
# PAGE CONFIGURATION
# ===============================
st.set_page_config(page_title="Pro Terminal Master", layout="wide", page_icon="🏦")
st.title("🧠 CA Dilip's Pro Terminal: High Probability Edition")

# ===============================
# CORE LOGIC
# ===============================
def clean_dataframe(df):
    if df is None or df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

def calc_rsi(df, period=2):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -1 * delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
    return df

def get_trend(symbol, interval):
    try:
        data = yf.download(symbol, period="2y", interval=interval, auto_adjust=True, progress=False)
        if data.empty: return "⚪"
        data = clean_dataframe(data)
        ema = data['Close'].ewm(span=10).mean().iloc[-1]
        price = data['Close'].iloc[-1]
        return "🟢" if price > ema else "🔴"
    except: return "⚪"

def run_market_radar():
    watch_list = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS", "ZOMATO.NS", "TRENT.NS", "HINDALCO.NS"]
    results = []
    for sym in watch_list:
        df = yf.download(sym, period="1y", interval="1d", auto_adjust=True, progress=False)
        df = clean_dataframe(df)
        if not df.empty and len(df) > 200:
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['SMA5'] = df['Close'].rolling(window=5).mean()
            df = calc_rsi(df, period=2)
            
            curr = df.iloc[-1]
            price = curr['Close']
            
            if price > curr['SMA200'] and curr['RSI_2'] < 10:
                df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
                atr = float(df['ATR'].iloc[-1])
                results.append({
                    "Symbol": sym.replace(".NS", ""), 
                    "Price": round(price,2), 
                    "Target": round(curr['SMA5'], 2),
                    "Stop Loss": round(price - (1.5 * atr), 2), 
                    "Setup": "🟢 High-Prob Extreme RSI Dip"
                })
    return pd.DataFrame(results)

def run_backtest(df):
    if len(df) < 200: return 0, 0, 0, 0
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    df = calc_rsi(df, period=2)
    
    buy_signals = df[(df['Close'] > df['SMA200']) & (df['RSI_2'] < 10)].copy()
    
    wins, losses = 0, 0
    for idx, row in buy_signals.iterrows():
        entry = row['Close']
        sl = entry - (2 * row['ATR']) 
        
        future_data = df.loc[idx:].head(15) 
        for f_idx, f_row in future_data.iterrows():
            dynamic_tgt = df.loc[f_idx, 'SMA5']
            if f_row['High'] >= dynamic_tgt:
                wins += 1
                break
            elif f_row['Low'] <= sl:
                losses += 1
                break
                
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    return total, wins, losses, win_rate

# ===============================
# SIDEBAR
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
    
    raw_input = st.text_input("Search Name", value="HINDALCO").upper().strip()
    mode = st.selectbox("Strategy", ["Swing (RSI-2 High-Win)", "Scalping (15m)", "Long Term (Buffett)"])
    
    if st.button("Generate CA Audit (In-Depth)", type="primary"): st.session_state['show_audit'] = True

# TABS SETUP
tab1, tab2, tab3 = st.tabs(["📊 Live Terminal", "📡 Market Radar", "🧪 Backtester"])

# ===============================
# TAB 1: LIVE TERMINAL
# ===============================
with tab1:
    if raw_input:
        curr_prefix = "₹" if market_type == "Indian Stocks (NSE)" else "$"
        
        if market_type == "Indian Stocks (NSE)":
            fetch_sym = raw_input + ".NS" if ".NS" not in raw_input else raw_input
        elif market_type == "Forex":
            fetch_sym = fx_map.get(raw_input, raw_input) + "=X"
        else:
            fetch_sym = comm_map.get(raw_input, raw_input) + "=F"

        with st.spinner("Analyzing Market Structure..."):
            t_d, t_w, t_m = get_trend(fetch_sym, "1d"), get_trend(fetch_sym, "1wk"), get_trend(fetch_sym, "1mo")
            
            try:
                info_cache = yf.Ticker(fetch_sym).info
                eps = info_cache.get('trailingEps') or info_cache.get('forwardEps') or 0
                bv = info_cache.get('bookValue') or 0
                graham_val = (22.5 * eps * bv)**0.5 if (eps > 0 and bv > 0) else 0
            except: graham_val = 0
        
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1: st.markdown(f"### Trend Status: Daily {t_d} | Weekly {t_w} | Monthly {t_m}")
        with col_t2: st.caption("🟢 Bullish | 🔴 Bearish | ⚪ No Data")

        interval, period = ("15m", "5d") if "Scalping" in mode else ("1d", "2y")
        df = yf.download(fetch_sym, period=period, interval=interval, auto_adjust=True, progress=False)
        df = clean_dataframe(df)

        if not df.empty:
            price = float(df['Close'].iloc[-1])
            dec = 4 if market_type == "Forex" else 2
            
            df['Buy_Signal'] = float('nan')
            df['Sell_Signal'] = float('nan')
            
            # STRATEGY LOGIC
            if "Scalping" in mode:
                df["EMA_Fast"], df["EMA_Slow"] = df["Close"].ewm(span=9).mean(), df["Close"].ewm(span=15).mean()
                buy_cross = (df['EMA_Fast'] > df['EMA_Slow']) & (df['EMA_Fast'].shift(1) <= df['EMA_Slow'].shift(1))
                sell_cross = (df['EMA_Fast'] < df['EMA_Slow']) & (df['EMA_Fast'].shift(1) >= df['EMA_Slow'].shift(1))
                df.loc[buy_cross, 'Buy_Signal'] = df['Low'][buy_cross] * 0.998
                df.loc[sell_cross, 'Sell_Signal'] = df['High'][sell_cross] * 1.002
                f, s = float(df["EMA_Fast"].iloc[-1]), float(df["EMA_Slow"].iloc[-1])
                signal = "BUY" if (f > s and price > f) else "SELL" if (f < s and price < f) else "NO TRADE"
                ema_label = "EMA 9"
                
            elif "Swing" in mode:
                df['SMA200'] = df['Close'].rolling(window=200).mean()
                df['SMA5'] = df['Close'].rolling(window=5).mean()
                df = calc_rsi(df, period=2)
                df["EMA_Fast"] = df['SMA5'] 
                
                if len(df) > 200:
                    curr = df.iloc[-1]
                    if price > curr['SMA200'] and curr['RSI_2'] < 10:
                        signal = "BUY (EXTREME RSI DIP)"
                    else:
                        signal = "NO TRADE (Awaiting Dip)"
                        
                    buy_cond = (df['Close'] > df['SMA200']) & (df['RSI_2'] < 10)
                    df.loc[buy_cond, 'Buy_Signal'] = df['Low'][buy_cond] * 0.98 
                else: signal = "NO TRADE (Insufficient Data)"
                ema_label = "5 DMA (Reversion Target)"
                
            else:
                df["EMA_Fast"] = df["Close"].rolling(window=200).mean()
                sma200 = float(df['EMA_Fast'].iloc[-1]) if not pd.isna(df['EMA_Fast'].iloc[-1]) else price
                signal = "BUY (VALUE)" if price < sma200 else "WATCH / SIP"
                ema_label = "200 DMA"

            # RISK MANAGEMENT & DYNAMIC LABELS
            df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
            atr = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else 0
            
            entry_label = "Entry Price"
            tgt_label = "Target Exit"
            sl_label = "Stop Loss / Invalidation"
            
            sl_text, tgt_text, entry_text = "Wait", "Wait", "Wait"
            qty = 0
            risk_amt = total_cap * (risk_pct/100)
            
            if "Long Term" in mode:
                sma200 = float(df['EMA_Fast'].iloc[-1])
                if price <= sma200:
                    entry_label = "Entry Price (Now)"
                    entry_text = f"{curr_prefix}{price:,.{dec}f}"
                else:
                    entry_label = "Wait for Dip (200 DMA)"
                    entry_text = f"{curr_prefix}{sma200:,.{dec}f}"
                    
                sl_price = sma200 * 0.90
                sl_label = "Stop Loss (Macro Support)"
                sl_text = f"{curr_prefix}{sl_price:,.{dec}f}"
                
                if graham_val > price:
                    tgt_label = "Target Exit (Graham Value)"
                    tgt_text = f"{curr_prefix}{graham_val:,.{dec}f}"
                else:
                    tgt_label = "Target Exit (+20%)"
                    tgt_text = f"{curr_prefix}{(price * 1.20):,.{dec}f}"
                    
                qty = int(risk_amt / abs(price - sl_price)) if sl_price > 0 and sl_price < price else 0
                
            elif "Swing" in mode and "NO TRADE" not in signal:
                sl_price = price - (1.5 * atr)
                tgt_price = float(df['SMA5'].iloc[-1]) 
                sl_text = f"{curr_prefix}{sl_price:,.{dec}f}"
                tgt_label = "Target Exit (Mean Reversion)"
                tgt_text = f"{curr_prefix}{tgt_price:,.{dec}f}"
                entry_text = f"{curr_prefix}{price:,.{dec}f}" 
                qty = int(risk_amt / abs(price - sl_price)) if abs(price - sl_price) > 0 else 0
                
            elif "NO TRADE" not in signal and "WATCH" not in signal:
                sl_price = (price - atr) if "BUY" in signal else (price + atr)
                tgt_price = (price + (2 * atr)) if "BUY" in signal else (price - (2 * atr)) 
                sl_text = f"{curr_prefix}{sl_price:,.{dec}f}"
                tgt_text = f"{curr_prefix}{tgt_price:,.{dec}f}"
                entry_text = f"{curr_prefix}{price:,.{dec}f}" 
                qty = int(risk_amt / abs(price - sl_price)) if abs(price - sl_price) > 0 else 0

            # DASHBOARD UI (Applying Dynamic Labels)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Live Price", f"{curr_prefix}{price:,.{dec}f}")
            c2.metric("Signal", signal)
            c3.metric(entry_label, entry_text)
            c4.metric("Qty to Trade", f"{qty} Units")

            st.write("")
            c5, c6 = st.columns(2)
            c5.metric(tgt_label, tgt_text)
            c6.metric(sl_label, sl_text)

            # CHARTING
            display_df = df.tail(150)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=display_df.index, open=display_df['Open'], high=display_df['High'], low=display_df['Low'], close=display_df['Close'], name='Price'))
            
            fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA_Fast'], line=dict(color='orange', width=2), name=ema_label))
            
            if "Scalping" in mode:
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['EMA_Slow'], line=dict(color='cyan', width=2), name='EMA 15'))
                if 'Sell_Signal' in df.columns:
                    fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Sell_Signal'], mode='markers', marker=dict(symbol='triangle-down', size=14, color='red'), name='Sell'))
            
            if 'Buy_Signal' in df.columns and "Long Term" not in mode:
                fig.add_trace(go.Scatter(x=display_df.index, y=display_df['Buy_Signal'], mode='markers', marker=dict(symbol='triangle-up', size=14, color='lime'), name='Buy'))

            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

# ===============================
# TAB 2: MARKET RADAR
# ===============================
with tab2:
    st.markdown("### 📡 RSI Mean Reversion Screener")
    st.write("Scanning Nifty stocks for the highest probability setup: **Long-Term Uptrends with an Extreme RSI(2) Dip**...")
    if st.button("Run Radar Scan", type="primary"):
        with st.spinner("Scanning real-time markets..."):
            radar_results = run_market_radar()
            if not radar_results.empty:
                st.success("High-Probability Setups Found! Market has overreacted on these names.")
                st.dataframe(radar_results, use_container_width=True)
            else:
                st.info("No extreme dips found in the uptrend. Patience protects capital.")

# ===============================
# TAB 3: BACKTESTER
# ===============================
with tab3:
    st.markdown(f"### 🧪 Strategy Backtest: {raw_input}")
    st.write("Testing the **RSI(2) High Win-Rate Reversion Strategy** over the last 2 years.")
    
    if st.button("Run Backtest"):
        if market_type == "Indian Stocks (NSE)":
            test_sym = raw_input + ".NS" if ".NS" not in raw_input else raw_input
        else: test_sym = raw_input
        
        with st.spinner("Calculating historical data..."):
            hist_df = yf.download(test_sym, period="2y", interval="1d", auto_adjust=True, progress=False)
            hist_df = clean_dataframe(hist_df)
            if not hist_df.empty:
                t, w, l, wr = run_backtest(hist_df)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Trades", t)
                c2.metric("Winning Trades", w)
                c3.metric("Losing Trades", l)
                c4.metric("Win Rate", f"{wr:.1f}%")
                
                if wr >= 65: st.success("✅ Elite Win Rate! This strategy perfectly exploits this asset's mean reversion behavior.")
                elif wr >= 50: st.info("Solid Win Rate. Buying the dips works well here.")
                elif t == 0: st.info("Zero trades. Stock hasn't dipped below the RSI criteria while in an uptrend.")
                else: st.warning("⚠️ High failure rate. This asset trends aggressively and ignores mean reversion.")
            else:
                st.error("Could not load history for backtesting.")

# ===============================
# IN-DEPTH CA LEVEL AUDIT MODAL
# ===============================
if st.session_state.get('show_audit', False):
    @st.dialog("Deep Statement Analysis (CA Level)", width="large")
    def show_audit():
        st.markdown(f"### 📑 Institutional Fundamental Audit: **{raw_input}**")
        try:
            fetch_sym = raw_input + ".NS" if market_type == "Indian Stocks (NSE)" and ".NS" not in raw_input else raw_input
            if market_type == "Forex": fetch_sym = fx_map.get(raw_input, raw_input) + "=X"
            elif market_type == "Commodities": fetch_sym = comm_map.get(raw_input, raw_input) + "=F"
            
            ticker = yf.Ticker(fetch_sym)
            
            with st.spinner("Pulling raw financial statements..."):
                info = ticker.info
                inc_stmt = ticker.financials
                bal_sheet = ticker.balance_sheet
                cf_stmt = ticker.cashflow
                
            def get_latest(df, row_names):
                if df is None or df.empty: return None
                for name in row_names:
                    if name in df.index:
                        series = df.loc[name].dropna()
                        if not series.empty: return float(series.iloc[0])
                return None

            revenue = get_latest(inc_stmt, ["Total Revenue", "Operating Revenue"])
            gross_profit = get_latest(inc_stmt, ["Gross Profit"])
            net_income = get_latest(inc_stmt, ["Net Income", "Net Income Common Stockholders"])
            
            tot_assets = get_latest(bal_sheet, ["Total Assets"])
            tot_liab = get_latest(bal_sheet, ["Total Liabilities Net Minority Interest", "Total Liabilities"])
            tot_debt = get_latest(bal_sheet, ["Total Debt"])
            equity = get_latest(bal_sheet, ["Stockholders Equity", "Total Equity Gross Minority Interest"])
            curr_assets = get_latest(bal_sheet, ["Current Assets"])
            curr_liab = get_latest(bal_sheet, ["Current Liabilities"])
            
            op_cf = get_latest(cf_stmt, ["Operating Cash Flow"])
            capex = get_latest(cf_stmt, ["Capital Expenditure"])
            
            roe = info.get('returnOnEquity')
            if (roe is None or roe == 0) and net_income and equity and equity > 0:
                roe = net_income / equity
            else: roe = roe or 0

            current_ratio = info.get('currentRatio')
            if (current_ratio is None or current_ratio == 0) and curr_assets and curr_liab and curr_liab > 0:
                current_ratio = curr_assets / curr_liab
            else: current_ratio = current_ratio or 0

            fcf = info.get('freeCashflow')
            if (fcf is None or fcf == 0) and op_cf:
                fcf = op_cf + (capex if capex else 0)
            else: fcf = fcf or 0

            pe = info.get('trailingPE') or info.get('forwardPE') or 0
            pb = info.get('priceToBook') or 0
            de_ratio = info.get('debtToEquity')
            if (de_ratio is None) and tot_debt and equity and equity > 0:
                de_ratio = (tot_debt / equity) * 100 
            else: de_ratio = de_ratio or 0
            
            margins = info.get('operatingMargins') or 0
            eps = info.get('trailingEps') or 0
            bv_per_share = info.get('bookValue') or 0
            graham = (22.5 * eps * bv_per_share)**0.5 if (eps > 0 and bv_per_share > 0) else 0

            def fmt_cr(val):
                if val is None: return "N/A"
                if abs(val) >= 1e12:
                    return f"{curr_prefix}{val/1e12:,.2f} LC" 
                if abs(val) >= 1e7:
                    return f"{curr_prefix}{val/1e7:,.0f} Cr" 
                return f"{curr_prefix}{val:,.0f}"

            st.info(f"**Business Summary:** {info.get('longBusinessSummary', 'Summary not available.')}")
            st.divider()

            col_inc, col_bs, col_cf = st.columns(3)
            
            with col_inc:
                st.markdown("#### 📉 Income Statement")
                st.write(f"**Revenue:** {fmt_cr(revenue)}")
                st.write(f"**Gross Profit:** {fmt_cr(gross_profit)}")
                st.write(f"**Net Income:** {fmt_cr(net_income)}")
                st.write(f"**Oper. Margin:** {margins*100:.2f}%")

            with col_bs:
                st.markdown("#### 🏛️ Balance Sheet")
                st.write(f"**Total Assets:** {fmt_cr(tot_assets)}")
                st.write(f"**Total Liab.:** {fmt_cr(tot_liab)}")
                st.write(f"**Total Debt:** {fmt_cr(tot_debt)}")
                st.write(f"**Total Equity:** {fmt_cr(equity)}")

            with col_cf:
                st.markdown("#### 💸 Cash Flow")
                st.write(f"**Oper. Cash Flow:** {fmt_cr(op_cf)}")
                st.write(f"**CapEx:** {fmt_cr(capex)}")
                st.write(f"**Free Cash Flow:** {fmt_cr(fcf)}")
                st.write(f"**Dividend Yield:** {info.get('dividendYield', 0)*100:.2f}%")

            st.divider()
            
            st.markdown("#### ⚖️ Valuation & Key Ratios")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("P/E Ratio", f"{pe:.2f}x" if pe else "N/A")
            r2.metric("Price-to-Book", f"{pb:.2f}x" if pb else "N/A")
            r3.metric("Return on Equity", f"{roe*100:.2f}%" if roe else "N/A")
            r4.metric("Current Ratio", f"{current_ratio:.2f}x" if current_ratio else "N/A")
            
            r5, r6, r7, r8 = st.columns(4)
            r5.metric("Graham Fair Value", f"{curr_prefix}{graham:.2f}" if graham else "N/A")
            r6.metric("EPS (TTM)", f"{curr_prefix}{eps:.2f}" if eps else "N/A")
            r7.metric("Debt-to-Equity", f"{de_ratio:.2f}" if de_ratio else "N/A")
            r8.metric("Market Cap", fmt_cr(info.get('marketCap')))

            st.write("")
            if st.button("Close Audit", type="primary"): 
                st.session_state['show_audit'] = False
                st.rerun()
                
        except Exception as e: 
            st.error(f"Failed to extract deep statements. Ensure the ticker symbol is correct. Error: {e}")
    show_audit()
