#!/usr/bin/env python3
"""
minador_electoral.py
Mina datos electorales de Zacatecas 2027
Corre junto con los demás minadores en actualizar.sh
"""

import feedparser
import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FECHA = datetime.now().strftime("%Y-%m-%d")
os.makedirs("datos_crudos", exist_ok=True)
os.makedirs("datos_electorales", exist_ok=True)

# ─────────────────────────────────────────
# ASPIRANTES RASTREADOS
# ─────────────────────────────────────────
ASPIRANTES = [
    {
        "id":      "mejia_haro",
        "nombre":  "Ulises Mejía Haro",
        "partido": "Morena",
        "cargo":   "Aspirante gobernador",
        "keywords": ["Ulises Mejía", "Mejía Haro"],
        "color":   "#C91A1A",
        "pct_base": 22.7,
    },
    {
        "id":      "saul_monreal",
        "nombre":  "Saúl Monreal Ávila",
        "partido": "PT/Morena",
        "cargo":   "Aspirante gobernador",
        "keywords": ["Saúl Monreal", "Monreal Ávila", "Monreal Avila"],
        "color":   "#E05C00",
        "pct_base": 20.5,
    },
    {
        "id":      "diaz_robles",
        "nombre":  "Verónica Díaz Robles",
        "partido": "Morena",
        "cargo":   "Aspirante gobernadora",
        "keywords": ["Verónica Díaz", "Veronica Diaz", "Díaz Robles"],
        "color":   "#C91A7A",
        "pct_base": 16.3,
    },
    {
        "id":      "narro_cespedes",
        "nombre":  "José Narro Céspedes",
        "partido": "PT",
        "cargo":   "Aspirante gobernador",
        "keywords": ["Narro Céspedes", "Narro Cespedes", "José Narro"],
        "color":   "#CC3300",
        "pct_base": 12.0,
    },
    {
        "id":      "varela_pinedo",
        "nombre":  "Miguel Varela Pinedo",
        "partido": "PAN",
        "cargo":   "Aspirante gobernador",
        "keywords": ["Miguel Varela", "Varela Pinedo"],
        "color":   "#005DAA",
        "pct_base": 38.6,
    },
    {
        "id":      "bonilla_gomez",
        "nombre":  "Adolfo Bonilla Gómez",
        "partido": "PRI",
        "cargo":   "Aspirante gobernador",
        "keywords": ["Adolfo Bonilla", "Bonilla Gómez", "Bonilla Gomez"],
        "color":   "#009E44",
        "pct_base": 35.3,
    },
    {
        "id":      "anaya_mota",
        "nombre":  "Claudia Anaya Mota",
        "partido": "PRI",
        "cargo":   "Aspirante gobernadora",
        "keywords": ["Claudia Anaya", "Anaya Mota"],
        "color":   "#007A33",
        "pct_base": 23.5,
    },
]

# ─────────────────────────────────────────
# KEYWORDS ELECTORALES GENERALES
# ─────────────────────────────────────────
KEYWORDS_ELECTORALES = [
    "Zacatecas elecciones", "gobernador Zacatecas", "alcalde Zacatecas",
    "Morena Zacatecas", "PAN Zacatecas", "PRI Zacatecas", "PT Zacatecas",
    "candidato Zacatecas", "campaña Zacatecas", "IEEZ", "INE Zacatecas",
    "David Monreal", "política Zacatecas", "municipios Zacatecas",
    "elecciones 2027", "proceso electoral Zacatecas", "encuesta Zacatecas",
    "nepotismo Morena Zacatecas", "TEPJF Zacatecas",
]

# ─────────────────────────────────────────
# KEYWORDS DE TEMAS QUE IMPACTAN ELECCIONES
# ─────────────────────────────────────────
KEYWORDS_CONTEXTO = [
    "seguridad Zacatecas", "CJNG Zacatecas", "minería Zacatecas",
    "presupuesto Zacatecas", "remesas Zacatecas", "migración Zacatecas",
    "obras Zacatecas", "economía Zacatecas", "agua Zacatecas",
    "educación Zacatecas", "salud Zacatecas", "corrupción Zacatecas",
]

# ─────────────────────────────────────────
# FUENTES RSS ELECTORALES
# ─────────────────────────────────────────
FUENTES_ELECTORALES = [
    # Locales Zacatecas
    {"nombre": "ljz_zacatecas",     "url": "https://ljz.mx/feed/",                              "tipo": "local"},
    {"nombre": "ntr_zacatecas",     "url": "https://www.ntrzacatecas.com/feed/",                 "tipo": "local"},
    {"nombre": "imagen_zac",        "url": "https://www.imagenzac.com.mx/feed/",                 "tipo": "local"},
    # Nacionales con cobertura política
    {"nombre": "jornada_politica",  "url": "https://www.jornada.com.mx/rss/politica.xml",        "tipo": "nacional"},
    {"nombre": "jornada_estados",   "url": "https://www.jornada.com.mx/rss/estados.xml",         "tipo": "nacional"},
    {"nombre": "expansion_politica","url": "https://expansion.mx/rss/politica",                  "tipo": "nacional"},
    {"nombre": "proceso",           "url": "https://www.proceso.com.mx/rss/",                    "tipo": "nacional"},
    {"nombre": "animal_politico",   "url": "https://www.animalpolitico.com/feed/",               "tipo": "nacional"},
    {"nombre": "infobae_mx",        "url": "https://www.infobae.com/mexico/feed/",               "tipo": "nacional"},
    {"nombre": "eltrochilero",  "url": "https://eltrochilero.com/feed/",                    "tipo": "local"},
    {"nombre": "ntv_zacatecas", "url": "https://ntv.com.mx/feed/",                          "tipo": "local"},
]

# ─────────────────────────────────────────
# FUNCIONES DE MINADO
# ─────────────────────────────────────────
def contiene_keywords(texto, keywords):
    texto_lower = texto.lower()
    for kw in keywords:
        if kw.lower() in texto_lower:
            return True
    return False

def detectar_aspirantes(texto):
    mencionados = []
    for asp in ASPIRANTES:
        for kw in asp["keywords"]:
            if kw.lower() in texto.lower():
                mencionados.append(asp["id"])
                break
    return mencionados

def clasificar_tema(texto):
    texto_l = texto.lower()
    if any(k.lower() in texto_l for k in ["encuesta", "preferencia", "popularidad", "sondeo", "%"]):
        return "encuesta"
    if any(k.lower() in texto_l for k in ["candidato", "candidatura", "registro", "postulación"]):
        return "candidatura"
    if any(k.lower() in texto_l for k in ["alianza", "coalición", "acuerdo", "frente"]):
        return "alianza"
    if any(k.lower() in texto_l for k in ["seguridad", "crimen", "violencia", "CJNG"]):
        return "seguridad"
    if any(k.lower() in texto_l for k in ["presupuesto", "obra", "inversión", "gasto"]):
        return "gasto_publico"
    if any(k.lower() in texto_l for k in ["corrupción", "irregularidad", "desvío"]):
        return "corrupcion"
    if any(k.lower() in texto_l for k in ["nepotismo", "familia", "parentesco"]):
        return "nepotismo"
    return "general"

def minar_fuente_electoral(fuente):
    print(f"  → {fuente['nombre']}...")
    try:
        feed = feedparser.parse(
            fuente["url"],
            request_headers={"User-Agent": "Mozilla/5.0"}
        )
        if not feed.entries:
            print(f"    sin entradas")
            return []

        entradas_relevantes = []
        for entry in feed.entries[:30]:
            titulo  = entry.get("title", "")
            resumen = entry.get("summary", "")
            texto   = f"{titulo} {resumen}"

            # Verificar si es relevante (electoral o contextual)
            es_electoral  = contiene_keywords(texto, KEYWORDS_ELECTORALES)
            es_contextual = contiene_keywords(texto, KEYWORDS_CONTEXTO)

            if not (es_electoral or es_contextual):
                continue

            aspirantes_mencionados = detectar_aspirantes(texto)
            tema = clasificar_tema(texto)

            entradas_relevantes.append({
                "titulo":      titulo,
                "resumen":     resumen[:400],
                "link":        entry.get("link", ""),
                "fecha":       entry.get("published", FECHA),
                "fuente":      fuente["nombre"],
                "tipo_fuente": fuente["tipo"],
                "nicho":       "electoral_zacatecas",
                "es_electoral":  es_electoral,
                "es_contextual": es_contextual,
                "aspirantes_mencionados": aspirantes_mencionados,
                "tema":        tema,
                "fecha_minado": FECHA,
            })

        print(f"    {len(entradas_relevantes)} entradas relevantes")
        return entradas_relevantes

    except Exception as e:
        print(f"    ERROR: {e}")
        return []

# ─────────────────────────────────────────
# CALCULAR SCORE DE MOMENTUM POR ASPIRANTE
# ─────────────────────────────────────────
def calcular_momentum(todas_entradas):
    """
    Score basado en menciones del día.
    Positivo si el tema es candidatura/alianza/encuesta.
    Negativo si el tema es corrupcion/nepotismo.
    """
    conteo    = defaultdict(int)
    positivo  = defaultdict(int)
    negativo  = defaultdict(int)
    temas     = defaultdict(list)

    for e in todas_entradas:
        for asp_id in e["aspirantes_mencionados"]:
            conteo[asp_id] += 1
            temas[asp_id].append(e["tema"])
            if e["tema"] in ["candidatura", "alianza", "encuesta"]:
                positivo[asp_id] += 1
            if e["tema"] in ["corrupcion", "nepotismo"]:
                negativo[asp_id] += 1

    resultado = {}
    for asp in ASPIRANTES:
        aid = asp["id"]
        menciones = conteo.get(aid, 0)
        pos = positivo.get(aid, 0)
        neg = negativo.get(aid, 0)
        momentum = (pos * 2) - (neg * 3) + menciones
        resultado[aid] = {
            "menciones":   menciones,
            "positivo":    pos,
            "negativo":    neg,
            "momentum":    momentum,
            "temas":       list(set(temas.get(aid, []))),
        }
    return resultado

# ─────────────────────────────────────────
# EJECUTAR MINADO
# ─────────────────────────────────────────
print("\n=== MINANDO FUENTES ELECTORALES ZACATECAS ===")
todas_entradas = []

for fuente in FUENTES_ELECTORALES:
    entradas = minar_fuente_electoral(fuente)
    todas_entradas.extend(entradas)
    time.sleep(1)

momentum = calcular_momentum(todas_entradas)

# ─────────────────────────────────────────
# GUARDAR DATOS CRUDOS ELECTORALES
# ─────────────────────────────────────────
salida_cruda = f"datos_crudos/electoral_{FECHA}.json"
with open(salida_cruda, "w", encoding="utf-8") as f:
    json.dump({
        "fecha":      FECHA,
        "total":      len(todas_entradas),
        "entradas":   todas_entradas,
        "momentum":   momentum,
        "aspirantes": ASPIRANTES,
    }, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────
# GUARDAR HISTORIAL DE MOMENTUM
# ─────────────────────────────────────────
historial_path = "datos_electorales/historial_momentum.json"
historial = {}
if os.path.exists(historial_path):
    with open(historial_path, encoding="utf-8") as f:
        historial = json.load(f)

historial[FECHA] = momentum

with open(historial_path, "w", encoding="utf-8") as f:
    json.dump(historial, f, ensure_ascii=False, indent=2)

print(f"\n✓ Electoral: {len(todas_entradas)} entradas relevantes")
print(f"✓ Datos guardados: {salida_cruda}")
print(f"✓ Historial actualizado: {historial_path}")

for asp in ASPIRANTES:
    aid = asp["id"]
    m = momentum.get(aid, {})
    print(f"  {asp['nombre']}: {m.get('menciones',0)} menciones | momentum {m.get('momentum',0):+d}")
