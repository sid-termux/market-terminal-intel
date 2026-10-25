import os
import json
from datetime import datetime
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT = """
Conduct a comprehensive pre-market search across the web, exchange disclosures (BSE/NSE), regulatory portals (RBI, SEBI, USFDA, IRDAI, CCI), investigative media, and market sentiment channels for news, filings, or reports affecting companies listed on Indian exchanges.

Return ONLY a valid JSON array of objects representing high-impact setups found in the last 24 hours.
Each object must follow this exact schema:
[
  {
    "horizon": "Instant Impact", // Exactly one of: "Instant Impact", "Short-Term Impact", "Quarterly Impact"
    "company_name": "Adani Enterprises Ltd",
    "ticker": "ADANIENT",
    "sector": "Energy & Infrastructure",
    "industry": "Mining & Trading",
    "credibility": "VERIFIED - OFFICIAL", // "VERIFIED - OFFICIAL" or "FUD / MEDIA SPECULATION"
    "direction": "Bullish", // "Bullish" or "Bearish"
    "magnitude_bar": "[████░░░░░░] 3%–5%",
    "target_pct": 4.0,
    "catalyst": "Brief detailed reason of news/filing",
    "invalidation_risk": "What could invalidate this setup",
    "source_url": "https://www.bseindia.com/..."
  }
]
"""

response = client.models.generate_content(
    model='gemini-3.8-flash',
    contents=PROMPT,
    config=types.GenerateContentConfig(
        tools=[{"google_search": {}}],
        response_mime_type="application/json",
        temperature=0.2,
    )
)

today_str = datetime.now().strftime("%Y-%m-%d")
DB_FILE = "market_intelligence.json"

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            database = json.load(f)
    except:
        database = []
else:
    database = []

try:
    new_items = json.loads(response.text)
    for idx, item in enumerate(new_items):
        horizon = item.get("horizon", "Instant Impact")
        max_days = 3 if "Instant" in horizon else (30 if "Short-Term" in horizon else 90)
        
        call_obj = {
            "id": f"{today_str}_{item.get('ticker')}_{idx}",
            "date": today_str,
            "horizon": horizon,
            "company_name": item.get("company_name"),
            "ticker": item.get("ticker", "").strip().upper(),
            "sector": item.get("sector", "General"),
            "industry": item.get("industry", "Diversified"),
            "credibility": item.get("credibility", "VERIFIED - OFFICIAL"),
            "direction": item.get("direction", "Bullish"),
            "magnitude_bar": item.get("magnitude_bar", "[████░░░░░░] 3%"),
            "target_pct": float(item.get("target_pct", 3.0)),
            "catalyst": item.get("catalyst"),
            "invalidation_risk": item.get("invalidation_risk"),
            "source_url": item.get("source_url", "#"),
            "base_price": None,
            "status": "PENDING",
            "max_tracking_days": max_days,
            "resolved_date": None,
            "result_note": "Awaiting market price validation"
        }
        database.insert(0, call_obj)

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print(f"Added {len(new_items)} new calls.")
except Exception as e:
    print(f"Error parsing calls: {e}")
