import feedparser
import requests
from bs4 import BeautifulSoup
import PyPDF2
import json
import os
from datetime import datetime
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from fuentes import FUENTES_RSS, FUENTES_PDF

os.makedirs("datos_crudos", exist_ok=True)
FECHA = datetime.now().strftime("%Y-%m-%d")


def minar_rss(fuente):
    print(f"  Minando RSS: {fuente['nombre']}...")
    try:
        if not fuente.get("ssl", True):
            feedparser.api._FeedParserMixin = feedparser.api._FeedParserMixin
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context

        feed = feedparser.parse(fuente["url"])

        if not feed.entries:
            print(f"    Sin entradas")
            return None

        entradas = []
        for entry in feed.entries[:20]:
            entradas.append({
                "titulo": entry.get("title", ""),
                "resumen": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "fecha_publicacion": entry.get("published", ""),
            })

        return {
            "fuente": fuente["nombre"],
            "url": fuente["url"],
            "nicho": fuente["nicho"],
            "fecha_minado": FECHA,
            "tipo": "rss",
            "entradas": entradas,
            "total_entradas": len(entradas)
        }

    except Exception as e:
        print(f"    ERROR: {e}")
        return None


def minar_pdf(fuente):
    print(f"  Minando PDF: {fuente['nombre']}...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        verificar_ssl = fuente.get("ssl", True)
        r = requests.get(fuente["url"], headers=headers, timeout=30, verify=verificar_ssl)
        r.raise_for_status()

        ruta_tmp = f"/tmp/{fuente['nombre']}.pdf"
        with open(ruta_tmp, "wb") as f:
            f.write(r.content)

        reader = PyPDF2.PdfReader(ruta_tmp)
        paginas = []
        for i, pagina in enumerate(reader.pages[:20]):
            texto = pagina.extract_text()
            if texto and len(texto.strip()) > 50:
                paginas.append({
                    "pagina": i + 1,
                    "texto": texto.strip()
                })

        return {
            "fuente": fuente["nombre"],
            "url": fuente["url"],
            "nicho": fuente["nicho"],
            "fecha_minado": FECHA,
            "tipo": "pdf",
            "paginas": paginas,
            "total_paginas": len(reader.pages)
        }

    except Exception as e:
        print(f"    ERROR: {e}")
        return None


resultados = []

print("\n=== MINANDO FUENTES RSS ===")
for fuente in FUENTES_RSS:
    datos = minar_rss(fuente)
    if datos:
        resultados.append(datos)
    time.sleep(1)

print("\n=== MINANDO FUENTES PDF ===")
for fuente in FUENTES_PDF:
    datos = minar_pdf(fuente)
    if datos:
        resultados.append(datos)
    time.sleep(2)

archivo_salida = f"datos_crudos/minado_{FECHA}.json"
with open(archivo_salida, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"\n✓ Datos guardados en: {archivo_salida}")
print(f"✓ Total fuentes minadas: {len(resultados)}")

for r in resultados:
    print(f"  - {r['fuente']}: {r['total_entradas'] if r['tipo'] == 'rss' else r['total_paginas']} entradas")
