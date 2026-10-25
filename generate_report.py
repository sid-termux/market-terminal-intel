import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from google import genai
from google.genai import types

# 1. Fetch real-time Indian stock market & regulatory news feeds directly (100% Free)
rss_feeds = [
    "https://news.google.com/rss/search?q=BSE+NSE+stock+market+filing+quarterly+results+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=SEBI+order+CCI+RBI+investigation+listed+company+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Indian+equities+earnings+surprise+target+hike+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
]

collected_news = []
req_headers = {'User-Agent': 'Mozilla/5.0'}

for url in rss_feeds:
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item')[:10]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                collected_news.append(f"- Headline: {title}\n  Source Link: {link}\n  Date: {pub_date}")
    except Exception as e:
        print(f"Error fetching RSS: {e}")

news_context = "\n".join(collected_news[:25])
print(f"Collected {len(collected_news)} live market headlines.")

# 2. Setup Gemini Client without paid search tool (Uses standard Free Tier quota)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT = f"""
You are a senior institutional equity analyst specializing in Indian equities (NSE & BSE).
Analyze the following real-time breaking market news and exchange disclosures from the last 24 hours:

=== LATEST LIVE MARKET DISCLOSURES & NEWS ===
{news_context}
============================================

Based on these actual developments, extract the top actionable stock setups and structure them strictly into 3 time horizons:
- Instant Impact (Next Day to 2-3 Days): Intraday volatility (2%+ moves), opening gaps, order wins, raid rumors, or circuit risks.
- Short-Term Impact (Next Week to 1 Month): Regulatory probes, ongoing enforcement, post-earnings continuations.
- Quarterly Impact (Over the Quarter): Fundamental shifts affecting full-year guidance, credit ratings, or broad institutional rebalancing.

Return ONLY a valid JSON array of objects following this schema:
[
  {{
    "horizon": "Instant Impact", // Exactly one of: "Instant Impact", "Short-Term Impact", "Quarterly Impact"
    "company_name": "Full Company Name",
    "ticker": "NSE_TICKER",
    "sector": "Broad Sector (e.g., Banking, Auto, Energy, IT, Pharma, Metals, Infrastructure)",
    "industry": "Specific Industry (e.g., Renewable Energy, Private Banks, EV, CDMO)",
    "credibility": "VERIFIED - OFFICIAL", // "VERIFIED - OFFICIAL" or "FUD / MEDIA SPECULATION"
    "direction": "Bullish", // "Bullish" or "Bearish"
    "magnitude_bar": "[████░░░░░░] 3%–5%",
    "target_pct": 4.0, // numeric percentage estimate
    "catalyst": "Concise factual reason for the move based on the news",
    "invalidation_risk": "What could invalidate or reverse this setup",
    "source_url": "Real link from the provided news context"
  }}
]
"""

response = client.models.generate_content(
    model='gemini-3.8-flash',
    contents=PROMPT,
    config=types.GenerateContentConfig(
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
    # Clean potential markdown wrapping
    cleaned_text = response.text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]

    new_items = json.loads(cleaned_text.strip())
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
    print(f"Successfully processed and added {len(new_items)} fresh market setups.")
except Exception as e:
    print(f"Error parsing model response: {e}")
