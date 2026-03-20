import feedparser
import requests
from datetime import datetime

feeds = {
    "ntr_zacatecas": "https://ntrzacatecas.com/feed/",
    "aristegui": "https://editorial.aristeguinoticias.com/feed/",
    "jornada": "https://www.jornada.com.mx/rss/edicion.xml",
    "excelsior": "https://www.excelsior.com.mx/rss.xml"
}

today = datetime.now().date()

report = []

for name, url in feeds.items():

    print("\nChecking:", name)

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            print("Feed not reachable")
            continue

        feed = feedparser.parse(r.text)

        if len(feed.entries) == 0:
            print("No entries found")
            continue

        for entry in feed.entries[:15]:

            title = entry.get("title", "")
            link = entry.get("link", "")

            date = None
            if "published_parsed" in entry and entry.published_parsed:
                date = datetime(*entry.published_parsed[:6]).date()

            report.append({
                "source": name,
                "date": str(date),
                "title": title,
                "link": link
            })

    except Exception as e:
        print("Error:", e)

print("\n--- ROBOT REPORT ---\n")

for item in report:
    print(f"SOURCE: {item['source']}")
    print(f"TITLE: {item['title']}")
    print(f"DATE: {item['date']}")
    print(f"LINK: {item['link']}")
    print()
