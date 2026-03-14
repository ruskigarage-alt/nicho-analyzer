#!/usr/bin/env python3
"""
generar_candidatos_json.py
──────────────────────────────────────────────────
Lee la salida de minador_electoral.py y genera
candidatos.json para el radar HTML.

No toca minador_electoral.py — solo consume su output.

Uso:
    python3 generar_candidatos_json.py

Se debe correr DESPUÉS de minador_electoral.py en actualizar.sh.
"""

import json
import os
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")

# ─────────────────────────────────────────
# HISTORIAL ACUMULADO DE MENCIONES
# ─────────────────────────────────────────
HISTORIAL_PATH = "datos_electorales/menciones_acumuladas.json"

def cargar_historial_acumulado():
    if os.path.exists(HISTORIAL_PATH):
        with open(HISTORIAL_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_historial_acumulado(historial):
    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────
# ENCUESTAS — actualiza aquí cuando salga nueva encuesta
# El minador no toca estos valores.
# ─────────────────────────────────────────
ENCUESTAS = {
    "varela_pinedo":  {"pct": 39.5, "fuente": "Cripeso · Marzo 2026"},
    "bonilla_gomez":  {"pct": 35.3, "fuente": "Cripeso · Marzo 2026"},
    "mejia_haro":     {"pct": 23.6, "fuente": "Cripeso · Marzo 2026"},
    "anaya_mota":     {"pct": 23.5, "fuente": "Cripeso · Marzo 2026"},
    "saul_monreal":   {"pct": 21.7, "fuente": "Medios locales"},
    "diaz_robles":    {"pct": 16.3, "fuente": "Referencia general"},
    "narro_cespedes": {"pct": 12.0, "fuente": "Referencia general"},
}

PARTY_CLASS = {
    "Morena":    "morena",
    "PT/Morena": "ptmorena",
    "PT":        "pt",
    "PAN":       "pan",
    "PRI":       "pri",
}

def cargar_electoral():
    """Carga el archivo generado por minador_electoral.py."""
    archivo = f"datos_crudos/electoral_{FECHA}.json"

    # Si no existe el de hoy, usa el más reciente
    if not os.path.exists(archivo):
        archivos = sorted([
            f for f in os.listdir("datos_crudos")
            if f.startswith("electoral_")
        ], reverse=True)
        if not archivos:
            print("⚠ No hay datos electorales. Corre minador_electoral.py primero.")
            return None
        archivo = f"datos_crudos/{archivos[0]}"
        print(f"  Usando archivo anterior: {archivo}")

    with open(archivo, encoding="utf-8") as f:
        return json.load(f)

def cargar_historial():
    """Carga el historial de momentum para calcular tendencia."""
    path = "datos_electorales/historial_momentum.json"
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def calcular_momentum_tendencia(historial, asp_id):
    """
    Compara menciones de hoy vs ayer.
    Devuelve diferencia como momentum de tendencia.
    """
    fechas = sorted(historial.keys(), reverse=True)
    if len(fechas) < 2:
        return 0

    hoy  = historial[fechas[0]].get(asp_id, {}).get("momentum", 0)
    ayer = historial[fechas[1]].get(asp_id, {}).get("momentum", 0)
    return hoy - ayer

def extraer_noticias(entradas, asp_id):
    """Extrae las noticias más relevantes para un candidato."""
    noticias = []
    for e in entradas:
        if asp_id in e.get("aspirantes_mencionados", []):
            noticias.append({
                "fuente": e["fuente"].replace("_", ""),
                "tag":    e.get("tema", "general"),
                "texto":  e["titulo"][:120],
                "link":   e.get("link", "")
            })
    return noticias[:3]  # máximo 3

def main():
    print(f"\n=== GENERANDO candidatos.json — {FECHA} ===")

    datos = cargar_electoral()
    if not datos:
        return

    historial = cargar_historial()
    entradas  = datos.get("entradas", [])
    momentum  = datos.get("momentum", {})
    aspirantes = datos.get("aspirantes", [])

    candidatos = []

    for asp in aspirantes:
        aid  = asp["id"]
        enc  = ENCUESTAS.get(aid, {"pct": 0, "fuente": "sin datos"})
        mom_data = momentum.get(aid, {})

        menciones = mom_data.get("menciones", 0)
        positivas = mom_data.get("positivo",  0)
        negativas = mom_data.get("negativo",  0)

        # Momentum de tendencia (vs día anterior)
        tendencia = calcular_momentum_tendencia(historial, aid)

        noticias = extraer_noticias(entradas, aid)

        # Tags dinámicos según temas detectados hoy
        temas_hoy = mom_data.get("temas", [])
        tags = temas_hoy if temas_hoy else asp.get("tags", ["general"])

        candidatos.append({
            "id":        asp["id"],
            "nombre":    asp["nombre"],
            "partido":   asp["partido"],
            "partyClass": PARTY_CLASS.get(asp["partido"], "default"),
            "pct":       enc["pct"],
            "momentum":  tendencia,
            "menciones": menciones,
            "positivas": positivas,
            "negativas": negativas,
            "fuente":    enc["fuente"],
            "tags":      tags,
            "noticias":  noticias,
        })

        estado = f"  {asp['nombre']}: {menciones} menciones"
        if noticias:
            estado += f" · {len(noticias)} noticias detectadas"
        print(estado)

    # ─────────────────────────────────────────
    # HISTORIAL ACUMULADO
    # ─────────────────────────────────────────
    historial_acum = cargar_historial_acumulado()
    for c in candidatos:
        aid = c["id"]
        menciones_hoy = c["menciones"]
        # Actualizar acumulado sin duplicar el mismo día
        if aid not in historial_acum:
            historial_acum[aid] = {"total": 0, "por_fecha": {}}

        menciones_previas_hoy = historial_acum[aid]["por_fecha"].get(FECHA, 0)
        # Restar lo que ya habíamos sumado hoy (si corremos 2 veces)
        historial_acum[aid]["total"] -= menciones_previas_hoy
        # Registrar las menciones de hoy (reemplaza)
        historial_acum[aid]["por_fecha"][FECHA] = menciones_hoy
        historial_acum[aid]["total"] += menciones_hoy

        c["menciones_total"] = historial_acum[aid]["total"]
        c["menciones_hoy"]   = menciones_hoy

        # Fix 3: Score compuesto — encuesta + peso por menciones
        # Cada 10 menciones acumuladas = +1 punto al score
        pct_base = c["pct"]
        bonus = min(round(historial_acum[aid]["total"] / 10, 1), 5.0)
        c["score_compuesto"] = round(pct_base + bonus, 1)
    guardar_historial_acumulado(historial_acum)

    # Ordenar por pct descendente
    candidatos.sort(key=lambda c: c["pct"], reverse=True)

    total_menciones = sum(c["menciones"] for c in candidatos)
    lider = candidatos[0]

    output = {
        "meta": {
            "fuente":               lider["fuente"],
            "actualizado":          FECHA,
            "total_menciones_hoy":  total_menciones,
            "entradas_analizadas":  len(entradas),
            "nota": "Generado automáticamente. Edita ENCUESTAS en generar_candidatos_json.py para actualizar porcentajes."
        },
        "candidatos": candidatos
    }

    with open("candidatos.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ candidatos.json generado")
    print(f"  Candidatos: {len(candidatos)}")
    print(f"  Menciones totales hoy: {total_menciones}")
    print(f"  Líder en encuestas: {lider['nombre']} ({lider['pct']}%)")

if __name__ == "__main__":
    main()
