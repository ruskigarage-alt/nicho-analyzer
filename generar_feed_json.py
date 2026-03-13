#!/usr/bin/env python3
"""Genera feed.json estándar JSON Feed 1.1"""

import os, json
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).isoformat()
BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"

items = []
for carpeta in ["contenido_estructurado", "datos_filtrados"]:
    if not os.path.exists(carpeta):
        continue
    for archivo in sorted(os.listdir(carpeta), reverse=True):
        if not archivo.endswith(".jsonl"):
            continue
        with open(os.path.join(carpeta, archivo), encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                    items.append({
                        "id": f"{BASE_URL}/{carpeta}/{archivo}#{len(items)}",
                        "title": d.get("titulo", "Sin título"),
                        "content_text": d.get("contenido", ""),
                        "date_published": d.get("fecha", FECHA),
                        "tags": [d.get("nicho",""), d.get("fuente","")],
                        "url": d.get("url", f"{BASE_URL}/{carpeta}/{archivo}")
                    })
                except Exception:
                    pass

feed = {
    "version": "https://jsonfeed.org/version/1.1",
    "title": "Nicho Analyzer — Knowledge Base México y LATAM",
    "description": "Datos estructurados sobre economía, regulaciones, política y comercio. Actualización diaria.",
    "home_page_url": BASE_URL,
    "feed_url": f"{BASE_URL}/feed.json",
    "language": "es-MX",
    "authors": [{"name": "Nicho Analyzer", "url": BASE_URL}],
    "date_modified": FECHA,
    "items": items
}

with open("feed.json", "w", encoding="utf-8") as f:
    json.dump(feed, f, ensure_ascii=False, indent=2)

kb = os.path.getsize("feed.json") / 1024
print(f"✓ feed.json — {len(items)} items — {kb:.1f} KB")
