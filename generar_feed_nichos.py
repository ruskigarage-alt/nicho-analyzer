#!/usr/bin/env python3
import os, json, re
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TIMESTAMP = datetime.now(timezone.utc).isoformat()
BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"
CARPETAS = ["contenido_estructurado", "datos_filtrados", "datos_crudos"]

os.makedirs("feed", exist_ok=True)

nichos = {}
for carpeta in CARPETAS:
    if not os.path.exists(carpeta):
        continue
    for archivo in sorted(os.listdir(carpeta)):
        if not archivo.endswith(".jsonl"):
            continue
        with open(os.path.join(carpeta, archivo), encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                    n = d.get("nicho", "general")
                    if n not in nichos:
                        nichos[n] = []
                    nichos[n].append(d)
                except Exception:
                    pass

links_generados = []
for nicho, registros in nichos.items():
    vistos = set()
    unicos = []
    for r in registros:
        clave = r.get("titulo","") + r.get("fecha","")[:10]
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)

    titulo_nicho = nicho.replace("_", " ").title()
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Nicho Analyzer — " + titulo_nicho,
        "description": "Datos sobre " + titulo_nicho + " en Mexico y LATAM.",
        "home_page_url": BASE_URL,
        "feed_url": BASE_URL + "/feed/" + nicho + ".json",
        "language": "es-MX",
        "date_modified": TIMESTAMP,
        "total_records": len(unicos),
        "items": []
    }
    for i, r in enumerate(unicos):
        feed["items"].append({
            "id": BASE_URL + "/feed/" + nicho + ".json#" + str(i),
            "title": r.get("titulo", "Sin titulo"),
            "content_text": r.get("contenido", ""),
            "date_published": r.get("fecha", TIMESTAMP),
            "url": r.get("url", BASE_URL),
            "tags": [nicho, r.get("fuente","")]
        })

    archivo_salida = "feed/" + nicho + ".json"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

    kb = os.path.getsize(archivo_salida) / 1024
    print("  OK feed/" + nicho + ".json — " + str(len(unicos)) + " registros — " + str(round(kb,1)) + " KB")
    links_generados.append(nicho)

# Actualizar index.html
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

lineas_link = []
for n in links_generados:
    label = n.replace("_", " ").title()
    lineas_link.append('  <link rel="alternate" type="application/json" title="Feed ' + label + '" href="feed/' + n + '.json">')

bloque = "\n".join(lineas_link)

if 'href="feed/' in html:
    html = re.sub(r'  <link rel="alternate"[^\n]+href="feed/[^\n]+\n', '', html)

html = html.replace('</head>', bloque + "\n</head>")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("\nOK index.html actualizado con " + str(len(links_generados)) + " link rel=alternate")
for n in links_generados:
    print("  " + BASE_URL + "/feed/" + n + ".json")
