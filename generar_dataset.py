#!/usr/bin/env python3
"""
generar_dataset.py
Genera dataset.json en la raíz — punto de entrada principal para crawlers de IA
Consolida todo el contenido estructurado en un solo archivo navegable
"""

import os
import json
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TIMESTAMP = datetime.now(timezone.utc).isoformat()
BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"

CARPETAS = ["contenido_estructurado", "datos_filtrados", "datos_crudos"]

registros = []
fuentes_vistas = set()

for carpeta in CARPETAS:
    if not os.path.exists(carpeta):
        continue
    for archivo in sorted(os.listdir(carpeta)):
        if not archivo.endswith(".jsonl"):
            continue
        filepath = os.path.join(carpeta, archivo)
        with open(filepath, encoding="utf-8") as f:
            for linea in f:
                try:
                    dato = json.loads(linea)
                    # Evitar duplicados por título
                    clave = dato.get("titulo","") + dato.get("fecha","")[:10]
                    if clave in fuentes_vistas:
                        continue
                    fuentes_vistas.add(clave)
                    registros.append(dato)
                except Exception:
                    pass

dataset = {
    "schema": "https://schema.org/Dataset",
    "name": "Nicho Analyzer — Knowledge Base Económica México y LATAM",
    "description": (
        "Base de datos estructurada sobre regulaciones para PyMEs, política local Zacatecas, "
        "comercio exterior México, mercados financieros LATAM, licitaciones gobierno, "
        "movimiento de buques y aranceles. Actualización diaria automatizada."
    ),
    "url": BASE_URL,
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "creator": "Nicho Analyzer Pipeline",
    "dateModified": TIMESTAMP,
    "dateCreated": FECHA,
    "inLanguage": "es",
    "keywords": [
        "México", "LATAM", "regulaciones", "PyMEs", "SAT", "T-MEC",
        "licitaciones", "commodities", "aranceles", "Zacatecas",
        "política local", "comercio exterior", "buques", "puertos"
    ],
    "spatialCoverage": "México, América Latina",
    "sources": [
        "DOF", "SAT", "Banxico", "Banco Mundial", "Yahoo Finance",
        "OMC", "MarineTraffic", "CEPAL", "CompraNet"
    ],
    "formats": ["jsonl", "jsonld", "markdown"],
    "total_records": len(registros),
    "nichos": {},
    "records": registros
}

# Contar por nicho
for r in registros:
    n = r.get("nicho", "sin_nicho")
    dataset["nichos"][n] = dataset["nichos"].get(n, 0) + 1

with open("dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

kb = os.path.getsize("dataset.json") / 1024
print(f"✓ dataset.json generado — {len(registros)} registros — {kb:.1f} KB")
print(f"  Nichos:")
for nicho, count in dataset["nichos"].items():
    print(f"    - {nicho}: {count} registros")
