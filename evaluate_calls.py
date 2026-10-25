import json
import os
from datetime import datetime
import yfinance as yf

DB_FILE = "market_intelligence.json"
if not os.path.exists(DB_FILE):
    print("Database not found.")
    exit()

with open(DB_FILE, "r", encoding="utf-8") as f:
    database = json.load(f)

updated = False
today = datetime.now()

for call in database:
    if call.get("status") == "PENDING":
        ticker = call.get("ticker", "")
        symbol = f"{ticker}.NS" if not ticker.endswith(".NS") else ticker
        
        try:
            stock = yf.Ticker(symbol)
            call_date = datetime.strptime(call["date"], "%Y-%m-%d")
            days_elapsed = (today - call_date).days
            
            hist = stock.history(start=call["date"])
            if hist.empty:
                continue

            if not call.get("base_price"):
                call["base_price"] = round(float(hist['Open'].iloc[0]), 2)
            
            base = call["base_price"]
            target_pct = call.get("target_pct", 3.0) / 100.0
            sl_pct = 0.02
            
            max_high = float(hist['High'].max())
            min_low = float(hist['Low'].min())
            is_bull = "bull" in call.get("direction", "").lower()

            if is_bull:
                target_price = base * (1 + target_pct)
                sl_price = base * (1 - sl_pct)

                if max_high >= target_price:
                    call["status"] = "HIT"
                    call["resolved_date"] = today.strftime("%Y-%m-%d")
                    call["result_note"] = f"Target Hit: High ₹{max_high:.2f} reached Target ₹{target_price:.2f}"
                    updated = True
                elif min_low <= sl_price:
                    call["status"] = "MISSED"
                    call["resolved_date"] = today.strftime("%Y-%m-%d")
                    call["result_note"] = f"Invalidated: Low ₹{min_low:.2f} breached SL ₹{sl_price:.2f}"
                    updated = True
            else:
                target_price = base * (1 - target_pct)
                sl_price = base * (1 + sl_pct)

                if min_low <= target_price:
                    call["status"] = "HIT"
                    call["resolved_date"] = today.strftime("%Y-%m-%d")
                    call["result_note"] = f"Target Hit: Low ₹{min_low:.2f} hit Target ₹{target_price:.2f}"
                    updated = True
                elif max_high >= sl_price:
                    call["status"] = "MISSED"
                    call["resolved_date"] = today.strftime("%Y-%m-%d")
                    call["result_note"] = f"Invalidated: High ₹{max_high:.2f} hit SL ₹{sl_price:.2f}"
                    updated = True

            if call["status"] == "PENDING" and days_elapsed > call.get("max_tracking_days", 3):
                call["status"] = "MISSED"
                call["resolved_date"] = today.strftime("%Y-%m-%d")
                call["result_note"] = f"Time Horizon Expired ({days_elapsed} days passed)"
                updated = True

        except Exception as e:
            print(f"Skipping {ticker}: {e}")

if updated:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print("Database updated.")
