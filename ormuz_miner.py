# import requests
import feedparser
import pandas as pd
from datetime import datetime, UTC, UTC
import re

OUTPUT_FILE = "ormuz_intelligence.json"

# =========================
# CONFIG
# =========================

NEWS_FEEDS = [
    "https://feeds.reuters.com/reuters/worldNews",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
]

KEYWORDS = [
    "iran","hormuz","strait","oil","tanker",
    "military","attack","retaliation","escalation",
    "navy","missile","drone"
]

# =========================
# OIL DATA (EIA proxy)
# =========================

def get_oil_spread():
    try:
        brent = requests.get("https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY&frequency=daily&data[0]=value&facets[product][]=EPCBRENT&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1").json()
        wti = requests.get("https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY&frequency=daily&data[0]=value&facets[product][]=EPCWTI&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1").json()

        brent_price = float(brent['response']['data'][0]['value'])
        wti_price = float(wti['response']['data'][0]['value'])

        return {
            "brent": brent_price,
            "wti": wti_price,
            "spread": round(brent_price - wti_price, 2)
        }
    except:
        return {"error": "oil unavailable"}

# =========================
# NEWS + NARRATIVE
# =========================

def mine_news():
    results = []
    for url in NEWS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            text = (entry.title + " " + entry.get("summary","")).lower()
            score = sum(1 for k in KEYWORDS if k in text)

            if score > 0:
                results.append({
                    "title": entry.title,
                    "score": score,
                    "source": url
                })
    return results

def narrative_density(news):
    if not news:
        return 0
    escalation = sum(1 for n in news if n["score"] >= 3)
    return round((escalation / len(news)) * 100, 2)

# =========================
# SHIPPING (MarineTraffic proxy)
# =========================

def shipping_signal(news):
    tanker = sum(1 for n in news if "tanker" in n["title"].lower())
    ship = sum(1 for n in news if "ship" in n["title"].lower())
    return tanker + ship

# =========================
# INSURANCE (Lloyd's proxy)
# =========================

def insurance_signal(news):
    words = ["insurance","premium","war risk","shipping risk"]
    return sum(
        1 for n in news
        if any(w in n["title"].lower() for w in words)
    )

# =========================
# MILITARY (NOTAM proxy)
# =========================

def military_signal(news):
    words = ["missile","navy","drone","exercise","airspace"]
    return sum(
        1 for n in news
        if any(w in n["title"].lower() for w in words)
    )

# =========================
# TWITTER/X (scraping ligero sin API)
# =========================

def twitter_signal():
    try:
        url = "https://nitter.net/search?f=tweets&q=iran+hormuz"
        r = requests.get(url, timeout=5)
        matches = re.findall(r'tweet-content', r.text)
        return len(matches)
    except:
        return 0

# =========================
# MAIN
# =========================

def calculate_risk_score(data):

    score = 0

    score += data.get("oil_spread", 0) * 0.3

    score += data.get("insurance_spike", 0) * 0.3

    score += data.get("military_activity", 0) * 0.4

    return score

def main():
    now = datetime.now(UTC).isoformat()

    news = mine_news()
    oil = get_oil_spread()

    data = {
        "timestamp": now,
    "source_count": len(news),
        "oil": oil,
        "signals": {
            "narrative_density": narrative_density(news),
            "shipping_activity": shipping_signal(news),
            "insurance_risk": insurance_signal(news),
            "military_activity": military_signal(news),
            "twitter_signal": twitter_signal()
        },
        "news_sample": news[:20]
    }

    pd.DataFrame([data]).to_json(OUTPUT_FILE, indent=2)

    print("✅ Intelligence generated:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
