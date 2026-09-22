import os
import time
import numpy as np
import pandas as pd
import yfinance as yf

WATCHLIST = {
    "BBCA.JK": "Indonesia", "BBRI.JK": "Indonesia", "BMRI.JK": "Indonesia",
    "ASII.JK": "Indonesia", "TLKM.JK": "Indonesia", "ICBP.JK": "Indonesia",
    "UNTR.JK": "Indonesia", "ADRO.JK": "Indonesia",
    "AAPL": "US", "MSFT": "US", "GOOGL": "US", "AMZN": "US",
    "NVDA": "US", "META": "US", "BRK-B": "US", "TSLA": "US",
}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_simple_piotroski(ticker_obj):
    score = 0
    try:
        fin = ticker_obj.financials
        bs = ticker_obj.balance_sheet
        cf = ticker_obj.cashflow
        if fin.empty or bs.empty: return np.nan

        net_income = fin.loc["Net Income"].iloc[0] if "Net Income" in fin.index else 0
        if net_income > 0: score += 1

        cfo = cf.loc["Operating Cash Flow"].iloc[0] if not cf.empty and "Operating Cash Flow" in cf.index else 0
        if cfo > 0: score += 1
        if cfo > net_income: score += 1

        assets = bs.loc["Total Assets"].iloc[0] if "Total Assets" in bs.index else 1
        if (net_income / assets) > 0: score += 1

        if "Long Term Debt" in bs.index and len(bs.columns) > 1:
            debt_now = bs.loc["Long Term Debt"].iloc[0]
            debt_prev = bs.loc["Long Term Debt"].iloc[1]
            if debt_now <= debt_prev: score += 1
        else: score += 1

        if "Current Assets" in bs.index and "Current Liabilities" in bs.index and len(bs.columns) > 1:
            cr_now = bs.loc["Current Assets"].iloc[0] / bs.loc["Current Liabilities"].iloc[0]
            cr_prev = bs.loc["Current Assets"].iloc[1] / bs.loc["Current Liabilities"].iloc[1]
            if cr_now > cr_prev: score += 1
        else: score += 1

        return score
    except Exception:
        return np.nan

def calculate_simple_dcf(ticker_obj, current_price, discount_rate=0.10, growth_rate=0.05, terminal_rate=0.02, years=5):
    try:
        cf = ticker_obj.cashflow
        info = ticker_obj.info
        shares_outstanding = info.get("sharesOutstanding")
        
        if "Free Cash Flow" in cf.index:
            fcf = cf.loc["Free Cash Flow"].iloc[0]
        else:
            cfo = cf.loc["Operating Cash Flow"].iloc[0]
            capex = abs(cf.loc["Capital Expenditure"].iloc[0]) if "Capital Expenditure" in cf.index else 0
            fcf = cfo - capex
            
        if pd.isna(fcf) or fcf <= 0 or not shares_outstanding:
            return np.nan, np.nan
            
        projected_fcf = [fcf * (1 + growth_rate)**i for i in range(1, years + 1)]
        pv_fcf = sum([cf / (1 + discount_rate)**i for i, cf in enumerate(projected_fcf, 1)])
        
        terminal_value = (projected_fcf[-1] * (1 + terminal_rate)) / (discount_rate - terminal_rate)
        pv_terminal_value = terminal_value / (1 + discount_rate)**years
        
        fair_value_total = pv_fcf + pv_terminal_value
        fair_value_per_share = fair_value_total / shares_outstanding
        
        margin_of_safety = ((fair_value_per_share - current_price) / fair_value_per_share) * 100
        return fair_value_per_share, margin_of_safety
    except Exception as e:
        return np.nan, np.nan

def run_pipeline():
    results = []
    print("Memulai pembaruan data kuantitatif dengan Analisa DCF...")

    for ticker_symbol, region in WATCHLIST.items():
        try:
            print(f"Memproses {ticker_symbol}...")
            t = yf.Ticker(ticker_symbol)
            hist = t.history(period="1y")

            if hist.empty or len(hist) < 200:
                continue

            last_close = hist["Close"].iloc[-1]
            ma200 = hist["Close"].rolling(200).mean().iloc[-1]
            rsi = calculate_rsi(hist["Close"]).iloc[-1]

            info = t.info
            pe = info.get("trailingPE", np.nan)
            pb = info.get("priceToBook", np.nan)
            roe = (info.get("returnOnEquity", np.nan) * 100) if info.get("returnOnEquity") else np.nan
            dy = (info.get("dividendYield", 0) * 100) if info.get("dividendYield") else 0.0
            
            f_score = calculate_simple_piotroski(t)
            fair_value, margin_of_safety = calculate_simple_dcf(t, last_close)

            trend = "Uptrend (Bullish)" if last_close > ma200 else "Downtrend (Bearish)"
            
            val_status = "Tidak Tersedia"
            if pd.notnull(margin_of_safety):
                val_status = "Undervalued (Diskon)" if margin_of_safety > 15 else ("Overvalued (Mahal)" if margin_of_safety < -15 else "Fair Valued (Wajar)")

            results.append({
                "Ticker": ticker_symbol,
                "Nama": info.get("shortName", ticker_symbol),
                "Region": region,
                "Harga": round(last_close, 2),
                "Fair Value": round(fair_value, 2) if pd.notnull(fair_value) else "-",
                "MoS (%)": round(margin_of_safety, 2) if pd.notnull(margin_of_safety) else "-",
                "Status Valuasi": val_status,
                "P/E": round(pe, 2) if pd.notnull(pe) else "-",
                "P/B": round(pb, 2) if pd.notnull(pb) else "-",
                "ROE (%)": round(roe, 2) if pd.notnull(roe) else "-",
                "Div Yield (%)": round(dy, 2),
                "RSI (14)": round(rsi, 2),
                "Tren (vs MA200)": trend,
                "F-Score": f_score if pd.notnull(f_score) else "-",
            })
            time.sleep(1)
        except Exception as e:
            print(f"Gagal memproses {ticker_symbol}: {e}")

    df_result = pd.DataFrame(results)
    df_result.to_csv("screener_data.csv", index=False)
    print("Selesai! File screener_data.csv berhasil diperbarui.")

if __name__ == "__main__":
    run_pipeline()