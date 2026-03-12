import json
import os
from datetime import datetime

os.makedirs("contenido_estructurado", exist_ok=True)
FECHA = datetime.now().strftime("%Y-%m-%d")

# Cargar datos filtrados
archivo = f"datos_filtrados/filtrado_{FECHA}.json"
with open(archivo, "r", encoding="utf-8") as f:
    por_nicho = json.load(f)

# Procesar cada nicho
for nicho, entradas in por_nicho.items():
    if not entradas:
        continue

    print(f"\nEstructurando nicho: {nicho} ({len(entradas)} entradas)")
    base = f"contenido_estructurado/{nicho}_{FECHA}"

    # ─────────────────────────────────────────
    # SALIDA 1 — Markdown
    # ─────────────────────────────────────────
    md = f"""---
title: "{nicho.replace('_', ' ').title()} — Actualización {FECHA}"
date: "{FECHA}"
nicho: "{nicho}"
total_entradas: {len(entradas)}
schema: "NewsDigest"
---

# {nicho.replace('_', ' ').title()}
> Digest estructurado para sistemas de IA — {FECHA}

## Entradas del día

"""
    for e in entradas:
        md += f"### {e['titulo']}\n"
        md += f"- **Fecha**: {e.get('fecha_publicacion', e.get('fecha', 'N/A'))}\n"
        md += f"- **Fuente**: {e.get('fuente_nombre', e.get('fuente', 'N/A'))}\n"
        md += f"- **URL**: {e.get('link', e.get('url', 'N/A'))}\n"
        md += f"- **Resumen**: {e.get('resumen', 'Sin resumen')}\n"
        md += f"- **Relevancia**: {e.get('relevancia_score', 'N/A')}\n\n"

    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  ✓ Markdown: {base}.md")

    # ─────────────────────────────────────────
    # SALIDA 2 — JSONL
    # ─────────────────────────────────────────
    with open(f"{base}.jsonl", "w", encoding="utf-8") as f:
        for e in entradas:
            registro = {
                "nicho": nicho,
                "fecha": FECHA,
                "titulo": e["titulo"],
                "resumen": e.get("resumen", ""),
                "url": e.get("link", e.get("url", "")),
                "fuente": e.get("fuente_nombre", e.get("fuente", "")),
                "relevancia_score": e.get("relevancia_score", 0),
                "texto_completo": f"{e['titulo']}. {e.get('resumen', '')}"
            }
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print(f"  ✓ JSONL: {base}.jsonl")

    # ─────────────────────────────────────────
    # SALIDA 3 — JSON-LD
    # ─────────────────────────────────────────
    json_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{nicho} — {FECHA}",
        "description": f"Digest semántico de {nicho} generado el {FECHA}",
        "datePublished": FECHA,
        "numberOfItems": len(entradas),
        "itemListElement": []
    }

    for i, e in enumerate(entradas):
        json_ld["itemListElement"].append({
            "@type": "ListItem",
            "position": i + 1,
            "item": {
                "@type": "NewsArticle",
                "headline": e["titulo"],
                "description": e.get("resumen", ""),
                "url": e.get("link", e.get("url", "")),
                "datePublished": e.get("fecha_publicacion", e.get("fecha", "")),
                "publisher": {
                    "@type": "Organization",
                    "name": e.get("fuente_nombre", e.get("fuente", ""))
                },
                "keywords": nicho.replace("_", ", "),
                "relevanceScore": e.get("relevancia_score", 0)
            }
        })

    with open(f"{base}.jsonld", "w", encoding="utf-8") as f:
        json.dump(json_ld, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON-LD: {base}.jsonld")

# ─────────────────────────────────────────
# ACTUALIZAR ÍNDICE WEB
# ─────────────────────────────────────────
archivos = sorted(os.listdir("contenido_estructurado"))
html = '''<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="UTF-8">
  <title>Contenido Estructurado — Nicho Analyzer</title>
  <meta name="robots" content="index, follow">
  <style>
    body { font-family: monospace; max-width: 800px; margin: 40px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }
    h1 { color: #58a6ff; }
    h2 { color: #79c0ff; margin-top: 24px; }
    a { color: #58a6ff; display: block; padding: 4px 0; }
    .meta { color: #8b949e; font-size: 0.85em; }
  </style>
</head>
<body>
<h1>Contenido Estructurado</h1>
<p class="meta">Archivos disponibles para consumo por IAs y crawlers</p>
'''

# Agrupar por nicho
por_nicho_html = {}
for archivo in archivos:
    if archivo.endswith(('.md', '.jsonl', '.jsonld')):
        partes = archivo.split('_')
        nicho_key = '_'.join(partes[:-1]) if partes[-1].startswith('2') else archivo
        if nicho_key not in por_nicho_html:
            por_nicho_html[nicho_key] = []
        por_nicho_html[nicho_key].append(archivo)

for nicho_key, files in por_nicho_html.items():
    html += f'<h2>{nicho_key.replace("_", " ").title()}</h2>\n'
    for f in files:
        html += f'<a href="{f}">{f}</a>\n'

html += '''
<br>
<a href="../index.html">← Volver al inicio</a>
<p class="meta">Actualizado: ''' + FECHA + '''</p>
</body>
</html>'''

with open("contenido_estructurado/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ Índice web actualizado")
print(f"✓ Estructuración completa")
