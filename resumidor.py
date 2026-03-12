import json
import os
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")

# Cargar datos crudos
archivo = f"datos_crudos/minado_{FECHA}.json"
with open(archivo, "r", encoding="utf-8") as f:
    datos = json.load(f)

# Agrupar por nicho
por_nicho = {}
for fuente in datos:
    nicho = fuente["nicho"]
    if nicho not in por_nicho:
        por_nicho[nicho] = []
    if fuente["tipo"] == "rss":
        for entrada in fuente["entradas"]:
            entrada["fuente_nombre"] = fuente["fuente"]
            por_nicho[nicho].append(entrada)

print("\n")
print("=" * 60)
print(f"  RESUMEN DEL DÍA — {FECHA}")
print("=" * 60)

for nicho, entradas in por_nicho.items():
    print(f"\n▶ {nicho.replace('_', ' ').upper()} ({len(entradas)} entradas)\n")
    for e in entradas:
        print(f"  • {e['titulo']}")
        if e.get("resumen"):
            # Truncar resumen a 100 caracteres
            resumen = e["resumen"]
            if len(resumen) > 100:
                resumen = resumen[:100] + "..."
            print(f"    {resumen}")
        print()

print("=" * 60)
print(f"  Total entradas: {sum(len(e) for e in por_nicho.values())}")
print(f"  Nichos cubiertos: {len(por_nicho)}")
print(f"  Archivos en: contenido_estructurado/")
print("=" * 60)
print()
