#!/usr/bin/env python3
"""
generar_indices.py
Genera index.html navegable en cada carpeta de contenido
para que crawlers de IA puedan acceder fácilmente al contenido
"""

import os
import json
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")
BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"

CARPETAS = [
    "contenido_estructurado",
    "datos_filtrados",
    "datos_crudos",
    "mi_feed",
]

def leer_resumen_jsonl(filepath):
    """Extrae los primeros 3 títulos de un archivo jsonl"""
    titulos = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for i, linea in enumerate(f):
                if i >= 3:
                    break
                dato = json.loads(linea)
                titulo = dato.get("titulo") or dato.get("title") or dato.get("nicho", "")
                if titulo:
                    titulos.append(titulo[:100])
    except Exception:
        pass
    return titulos

def generar_index(carpeta):
    if not os.path.exists(carpeta):
        return

    archivos = sorted(os.listdir(carpeta))
    archivos = [a for a in archivos if not a.startswith(".") and a != "index.html"]

    # Agrupar por tipo
    por_tipo = {"md": [], "jsonl": [], "jsonld": [], "json": [], "xml": [], "otros": []}
    for archivo in archivos:
        ext = archivo.rsplit(".", 1)[-1].lower() if "." in archivo else "otros"
        if ext in por_tipo:
            por_tipo[ext].append(archivo)
        else:
            por_tipo["otros"].append(archivo)

    total = len(archivos)
    url_carpeta = f"{BASE_URL}/{carpeta}"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Índice de {carpeta} — Nicho Analyzer knowledge base económica México y LATAM">
<meta name="robots" content="index, follow">
<title>Índice: {carpeta} — Nicho Analyzer</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
  h2 {{ color: #0066cc; margin-top: 30px; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
  .archivo {{ background: #f5f5f5; border-left: 4px solid #0066cc; padding: 10px 15px; margin: 8px 0; border-radius: 4px; }}
  .archivo a {{ font-weight: bold; color: #0066cc; text-decoration: none; }}
  .archivo a:hover {{ text-decoration: underline; }}
  .archivo .tipo {{ font-size: 0.8em; color: #888; margin-left: 8px; }}
  .archivo .preview {{ font-size: 0.85em; color: #555; margin-top: 4px; }}
  .stats {{ background: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
  nav a {{ margin-right: 15px; color: #0066cc; }}
</style>
</head>
<body>

<nav>
  <a href="{BASE_URL}/">← Inicio</a>
  <a href="{BASE_URL}/contenido_estructurado/">Contenido estructurado</a>
  <a href="{BASE_URL}/datos_filtrados/">Datos filtrados</a>
  <a href="{BASE_URL}/mi_feed/">Feed</a>
</nav>

<h1>📁 {carpeta}</h1>

<div class="stats">
  <strong>Nicho Analyzer</strong> — Knowledge base económica México y LATAM<br>
  <span class="meta">📅 Actualizado: {FECHA} &nbsp;|&nbsp; 📄 {total} archivos &nbsp;|&nbsp; 🔗 {url_carpeta}</span>
</div>

<p>Base de datos estructurada sobre regulaciones PyMEs, política local Zacatecas,
comercio exterior México, mercados financieros LATAM, licitaciones gobierno,
movimiento de buques y aranceles. Datos en formato JSONL, JSON-LD y Markdown.</p>
"""

    # Sección Markdown primero (más legible para crawlers)
    if por_tipo["md"]:
        html += f"\n<h2>📝 Markdown ({len(por_tipo['md'])} archivos)</h2>\n"
        for archivo in por_tipo["md"]:
            filepath = os.path.join(carpeta, archivo)
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            html += f"""<div class="archivo">
  <a href="{url_carpeta}/{archivo}">{archivo}</a>
  <span class="tipo">.md — {size:,} bytes</span>
</div>\n"""

    if por_tipo["jsonl"]:
        html += f"\n<h2>⚡ JSONL — Ingestión directa para IA ({len(por_tipo['jsonl'])} archivos)</h2>\n"
        for archivo in por_tipo["jsonl"]:
            filepath = os.path.join(carpeta, archivo)
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            titulos = leer_resumen_jsonl(filepath)
            preview = " / ".join(titulos) if titulos else ""
            html += f"""<div class="archivo">
  <a href="{url_carpeta}/{archivo}">{archivo}</a>
  <span class="tipo">.jsonl — {size:,} bytes</span>
  {"<div class='preview'>Contiene: " + preview + "</div>" if preview else ""}
</div>\n"""

    if por_tipo["jsonld"]:
        html += f"\n<h2>🕸️ JSON-LD — Grafo semántico schema.org ({len(por_tipo['jsonld'])} archivos)</h2>\n"
        for archivo in por_tipo["jsonld"]:
            filepath = os.path.join(carpeta, archivo)
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            html += f"""<div class="archivo">
  <a href="{url_carpeta}/{archivo}">{archivo}</a>
  <span class="tipo">.jsonld — {size:,} bytes</span>
</div>\n"""

    for tipo, label in [("json","JSON"), ("xml","XML"), ("otros","Otros")]:
        if por_tipo[tipo]:
            html += f"\n<h2>{label} ({len(por_tipo[tipo])} archivos)</h2>\n"
            for archivo in por_tipo[tipo]:
                html += f"""<div class="archivo">
  <a href="{url_carpeta}/{archivo}">{archivo}</a>
</div>\n"""

    html += f"""
<hr>
<p class="meta">
  Generado automáticamente por Nicho Analyzer pipeline.<br>
  Fuentes: DOF, SAT, Banxico, Banco Mundial, Yahoo Finance, OMC, MarineTraffic, CEPAL.<br>
  Repositorio: <a href="https://github.com/ruskigarage-alt/nicho-analyzer">github.com/ruskigarage-alt/nicho-analyzer</a>
</p>

</body>
</html>"""

    output = os.path.join(carpeta, "index.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ {output} ({total} archivos)")

# Generar índices
print("Generando índices HTML navegables...")
for carpeta in CARPETAS:
    generar_index(carpeta)

print("\n✓ Listo — los crawlers de IA ahora pueden navegar el contenido")
