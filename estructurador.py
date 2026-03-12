import json
import os
from datetime import datetime

os.makedirs("contenido_estructurado", exist_ok=True)
FECHA = datetime.now().strftime("%Y-%m-%d")

# Cargar datos crudos del día
archivo = f"datos_crudos/minado_{FECHA}.json"
with open(archivo, "r", encoding="utf-8") as f:
    datos = json.load(f)

# Agrupar entradas por nicho
por_nicho = {}
for fuente in datos:
    nicho = fuente["nicho"]
    if nicho not in por_nicho:
        por_nicho[nicho] = []
    if fuente["tipo"] == "rss":
        for entrada in fuente["entradas"]:
            entrada["fuente_nombre"] = fuente["fuente"]
            por_nicho[nicho].append(entrada)

# Procesar cada nicho
for nicho, entradas in por_nicho.items():
    print(f"\nEstructurando nicho: {nicho} ({len(entradas)} entradas)")
    base = f"contenido_estructurado/{nicho}_{FECHA}"

    # ─────────────────────────────────────────
    # SALIDA 1 — Markdown estructurado para crawlers
    # ─────────────────────────────────────────
    md = f"""---
title: "{nicho.replace('_', ' ').title()} — Actualización {FECHA}"
date: "{FECHA}"
nicho: "{nicho}"
fuentes: {list(set(e['fuente_nombre'] for e in entradas))}
total_entradas: {len(entradas)}
schema: "NewsDigest"
---

# {nicho.replace('_', ' ').title()}
> Digest estructurado para sistemas de IA — {FECHA}

## Entradas del día

"""
    for e in entradas:
        md += f"### {e['titulo']}\n"
        md += f"- **Fecha**: {e.get('fecha_publicacion', 'N/A')}\n"
        md += f"- **Fuente**: {e['fuente_nombre']}\n"
        md += f"- **URL**: {e['link']}\n"
        md += f"- **Resumen**: {e.get('resumen', 'Sin resumen')}\n\n"

    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  ✓ Markdown: {base}.md")

    # ─────────────────────────────────────────
    # SALIDA 2 — JSONL para consumo directo de IAs
    # ─────────────────────────────────────────
    with open(f"{base}.jsonl", "w", encoding="utf-8") as f:
        for e in entradas:
            registro = {
                "nicho": nicho,
                "fecha": FECHA,
                "titulo": e["titulo"],
                "resumen": e.get("resumen", ""),
                "url": e["link"],
                "fuente": e["fuente_nombre"],
                "texto_completo": f"{e['titulo']}. {e.get('resumen', '')}"
            }
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print(f"  ✓ JSONL: {base}.jsonl")

    # ─────────────────────────────────────────
    # SALIDA 3 — JSON-LD grafo semántico
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
                "url": e["link"],
                "datePublished": e.get("fecha_publicacion", ""),
                "publisher": {
                    "@type": "Organization",
                    "name": e["fuente_nombre"]
                },
                "keywords": nicho.replace("_", ", ")
            }
        })

    with open(f"{base}.jsonld", "w", encoding="utf-8") as f:
        json.dump(json_ld, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON-LD: {base}.jsonld")

print(f"\n✓ Estructuración completa. Archivos en: contenido_estructurado/")
