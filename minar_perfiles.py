#!/usr/bin/env python3
"""
minar_perfiles.py
──────────────────────────────────────────────────
Mina datos biográficos de candidatos desde Wikipedia
y genera perfiles JSON en datos_electorales/perfiles/

Fuentes:
  1. Wikipedia (artículo directo si existe)
  2. Wikipedia API de búsqueda (para nombres alternativos)
  3. Datos base manuales (fallback para quien no tiene Wikipedia)

Uso:
    python3 minar_perfiles.py

Agrega este script a actualizar.sh (se puede correr 1 vez por semana,
no necesita correr diario).
"""

import requests
import json
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) NichoAnalyzer/1.0"}
os.makedirs("datos_electorales/perfiles", exist_ok=True)

# ─────────────────────────────────────────
# DATOS BASE DE CANDIDATOS
# Completa manualmente lo que Wikipedia no tenga.
# Los campos de Wikipedia sobreescriben estos si se encuentran.
# ─────────────────────────────────────────
CANDIDATOS = [
    {
        "id": "varela_pinedo",
        "nombre": "Miguel Varela Pinedo",
        "partido": "PAN",
        "partyClass": "pan",
        "wikipedia_url": None,  # No tiene artículo — completar si se crea
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["Derecho"],
            "partido_actual": "Partido Acción Nacional (PAN)",
            "militancia_desde": "—",
            "cargo_actual": "Aspirante a la gubernatura de Zacatecas 2027",
            "cargos": [
                {"cargo": "Candidato a gobernador de Zacatecas", "periodo": "2027", "partido": "PAN"}
            ],
            "bio_corta": "Político zacatecano del PAN, aspirante a la gubernatura de Zacatecas para las elecciones de 2027.",
            "vinculos": []
        }
    },
    {
        "id": "bonilla_gomez",
        "nombre": "Adolfo Bonilla Gómez",
        "partido": "PRI",
        "partyClass": "pri",
        "wikipedia_url": None,
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["Derecho"],
            "partido_actual": "Partido Revolucionario Institucional (PRI)",
            "militancia_desde": "—",
            "cargo_actual": "Aspirante a la gubernatura de Zacatecas 2027",
            "cargos": [
                {"cargo": "Candidato a gobernador de Zacatecas", "periodo": "2027", "partido": "PRI"}
            ],
            "bio_corta": "Político priista zacatecano, aspirante a la gubernatura de Zacatecas para las elecciones de 2027.",
            "vinculos": []
        }
    },
    {
        "id": "mejia_haro",
        "nombre": "Ulises Mejía Haro",
        "partido": "Morena",
        "partyClass": "morena",
        "wikipedia_url": None,
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["Derecho"],
            "partido_actual": "Morena",
            "militancia_desde": "—",
            "cargo_actual": "Aspirante a la gubernatura de Zacatecas 2027",
            "cargos": [
                {"cargo": "Presidente municipal de Zacatecas", "periodo": "2022-2025", "partido": "Morena"},
                {"cargo": "Candidato a gobernador de Zacatecas", "periodo": "2027", "partido": "Morena"}
            ],
            "bio_corta": "Político morenista, ex presidente municipal de Zacatecas, aspirante a la gubernatura 2027.",
            "vinculos": []
        }
    },
    {
        "id": "anaya_mota",
        "nombre": "Claudia Anaya Mota",
        "partido": "PRI",
        "partyClass": "pri",
        "wikipedia_url": "https://es.wikipedia.org/wiki/Claudia_Anaya_Mota",
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["Derecho"],
            "partido_actual": "Partido Revolucionario Institucional (PRI)",
            "militancia_desde": "—",
            "cargo_actual": "Senadora de la República",
            "cargos": [],
            "bio_corta": "Política priista zacatecana, senadora de la República.",
            "vinculos": []
        }
    },
    {
        "id": "saul_monreal",
        "nombre": "Saúl Monreal Ávila",
        "partido": "PT/Morena",
        "partyClass": "ptmorena",
        "wikipedia_url": "https://es.wikipedia.org/wiki/Sa%C3%BAl_Monreal_%C3%81vila",
        "datos_base": {
            "nacimiento": "Fresnillo, Zacatecas",
            "educacion": ["Licenciatura en Derecho — UAZ", "Maestría en Derecho Político — IIDE"],
            "partido_actual": "Morena",
            "militancia_desde": "2016",
            "cargo_actual": "Senador de la República",
            "cargos": [
                {"cargo": "Senador de la República", "periodo": "2024-2030", "partido": "Morena"},
                {"cargo": "Presidente municipal de Fresnillo", "periodo": "2017-2021", "partido": "Morena"},
                {"cargo": "Diputado federal", "periodo": "2015-2018", "partido": "Movimiento Ciudadano"},
            ],
            "bio_corta": "Político mexicano miembro de Morena, senador desde 2024. Hermano del gobernador David Monreal.",
            "vinculos": ["David Monreal Ávila (gobernador de Zacatecas, hermano)", "Ricardo Monreal Ávila (senador, hermano)"]
        }
    },
    {
        "id": "diaz_robles",
        "nombre": "Verónica Díaz Robles",
        "partido": "Morena",
        "partyClass": "morena",
        "wikipedia_url": None,
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["—"],
            "partido_actual": "Morena",
            "militancia_desde": "—",
            "cargo_actual": "Aspirante a la gubernatura de Zacatecas 2027",
            "cargos": [
                {"cargo": "Diputada federal", "periodo": "—", "partido": "Morena"}
            ],
            "bio_corta": "Política morenista zacatecana, aspirante a la gubernatura 2027.",
            "vinculos": []
        }
    },
    {
        "id": "narro_cespedes",
        "nombre": "José Narro Céspedes",
        "partido": "PT",
        "partyClass": "pt",
        "wikipedia_url": None,
        "datos_base": {
            "nacimiento": "Zacatecas, México",
            "educacion": ["—"],
            "partido_actual": "Partido del Trabajo (PT)",
            "militancia_desde": "—",
            "cargo_actual": "Diputado federal",
            "cargos": [
                {"cargo": "Diputado federal", "periodo": "2021-2024", "partido": "PT"}
            ],
            "bio_corta": "Político del Partido del Trabajo, diputado federal por Zacatecas.",
            "vinculos": []
        }
    },
]

# ─────────────────────────────────────────
# FUNCIONES DE EXTRACCIÓN DE WIKIPEDIA
# ─────────────────────────────────────────
def extraer_infobox(soup):
    """Extrae datos estructurados de la infobox de Wikipedia."""
    datos = {}
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return datos

    for row in infobox.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        clave = th.get_text(strip=True).lower()
        valor = td.get_text(" ", strip=True)[:300]

        if "nacimiento" in clave:
            datos["nacimiento_raw"] = valor
        elif "educado en" in clave or "universidad" in clave:
            datos["educacion_raw"] = valor
        elif "educación" in clave or "estudios" in clave:
            datos["estudios_raw"] = valor
        elif "partido" in clave:
            datos["partido_raw"] = valor
        elif "cargo" in clave or "puesto" in clave:
            if "cargos_raw" not in datos:
                datos["cargos_raw"] = []
            datos["cargos_raw"].append(valor)
        elif "familiares" in clave or "familia" in clave:
            datos["familiares_raw"] = valor

    return datos

def extraer_cargos_de_secciones(soup):
    """Extrae cargos de las secciones del artículo."""
    cargos = []
    contenido = soup.find("div", class_="mw-parser-output")
    if not contenido:
        return cargos

    cargo_actual = None
    for elem in contenido.find_all(["h2", "h3", "p", "li"]):
        texto = elem.get_text(strip=True)
        if any(kw in texto.lower() for kw in ["diputad", "senador", "presidente municipal",
                                               "gobernador", "secretari", "regidor", "síndico"]):
            # Filtrar notas al pie y referencias bibliográficas
            if len(texto) < 200 and not texto.startswith("↑") and "«" not in texto[:5]:
                cargos.append(texto)

    return cargos[:8]  # máximo 8 cargos

def extraer_bio_parrafos(soup):
    """Extrae los primeros párrafos del artículo como bio."""
    contenido = soup.find("div", class_="mw-parser-output")
    if not contenido:
        return ""
    parrafos = []
    for p in contenido.find_all("p", recursive=False):
        texto = p.get_text(strip=True)
        if len(texto) > 50:
            parrafos.append(texto)
        if len(parrafos) >= 2:
            break
    return " ".join(parrafos)[:600]

def parsear_educacion(raw):
    """Convierte texto crudo de educación en lista limpia."""
    if not raw:
        return []
    # Separar por saltos de línea o puntos y coma
    partes = [p.strip() for p in raw.replace(";", "\n").split("\n") if p.strip()]
    return [p for p in partes if len(p) > 3][:5]

def parsear_partido(raw):
    """Extrae el partido más reciente del texto crudo."""
    if not raw:
        return "—"
    # Tomar la primera línea (partido más reciente)
    lineas = [l.strip() for l in raw.split("\n") if l.strip()]
    return lineas[0][:80] if lineas else raw[:80]

def minar_wikipedia(url):
    """Mina datos de un artículo de Wikipedia."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        infobox = extraer_infobox(soup)
        cargos_texto = extraer_cargos_de_secciones(soup)
        bio = extraer_bio_parrafos(soup)
        return {
            "infobox": infobox,
            "cargos_texto": cargos_texto,
            "bio": bio,
            "url": url
        }
    except Exception as e:
        print(f"    ERROR Wikipedia: {e}")
        return None

def buscar_wikipedia(nombre):
    """Busca un candidato en Wikipedia API si no hay URL directa."""
    try:
        api = "https://es.wikipedia.org/api/rest_v1/page/summary/"
        nombre_url = nombre.replace(" ", "_")
        r = requests.get(f"{api}{nombre_url}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "bio": data.get("extract", "")[:600],
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "infobox": {},
                "cargos_texto": []
            }
    except Exception:
        pass
    return None

# ─────────────────────────────────────────
# CONSTRUIR PERFIL FINAL
# ─────────────────────────────────────────
def construir_perfil(candidato, wiki_data):
    base = candidato["datos_base"]
    perfil = {
        "id":          candidato["id"],
        "nombre":      candidato["nombre"],
        "partido":     candidato["partido"],
        "partyClass":  candidato["partyClass"],
        "actualizado": FECHA,
        "fuente_wiki": None,
        "bio_corta":   base["bio_corta"],
        "nacimiento":  base["nacimiento"],
        "educacion":   base["educacion"],
        "partido_actual":    base["partido_actual"],
        "militancia_desde":  base["militancia_desde"],
        "cargo_actual":      base["cargo_actual"],
        "cargos":            base["cargos"],
        "vinculos":          base.get("vinculos", []),
        "cargos_detectados": []
    }

    if wiki_data:
        perfil["fuente_wiki"] = wiki_data.get("url", "")
        infobox = wiki_data.get("infobox", {})

        # Sobreescribir con datos de Wikipedia donde existan
        if wiki_data.get("bio"):
            perfil["bio_corta"] = wiki_data["bio"][:600]

        if infobox.get("nacimiento_raw"):
            perfil["nacimiento"] = infobox["nacimiento_raw"][:100]

        edu_raw = infobox.get("educacion_raw") or infobox.get("estudios_raw")
        if edu_raw:
            perfil["educacion"] = parsear_educacion(edu_raw)

        if infobox.get("partido_raw"):
            perfil["partido_actual"] = parsear_partido(infobox["partido_raw"])

        if infobox.get("familiares_raw"):
            import re
            # Wikipedia pega los nombres juntos: "RicardoMonrealDavidMonreal..."
            # Separar por mayúscula que sigue a minúscula
            texto = infobox["familiares_raw"]
            nombres = re.findall(r"[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)+", texto)
            perfil["vinculos"] = [n for n in nombres if len(n) > 5][:6]

        if wiki_data.get("cargos_texto"):
            perfil["cargos_detectados"] = wiki_data["cargos_texto"]

    return perfil

# ─────────────────────────────────────────
# PROCESO PRINCIPAL
# ─────────────────────────────────────────
print(f"\n=== MINANDO PERFILES ELECTORALES — {FECHA} ===")

perfiles_generados = []

for candidato in CANDIDATOS:
    print(f"\n  {candidato['nombre']}")
    wiki_data = None

    if candidato["wikipedia_url"]:
        print(f"    → Wikipedia directa...")
        wiki_data = minar_wikipedia(candidato["wikipedia_url"])
        if wiki_data:
            print(f"    ✓ Wikipedia OK — bio: {len(wiki_data.get('bio',''))} chars")
    else:
        print(f"    → Buscando en Wikipedia API...")
        wiki_data = buscar_wikipedia(candidato["nombre"])
        if wiki_data and wiki_data.get("bio"):
            print(f"    ✓ Encontrado via API — bio: {len(wiki_data['bio'])} chars")
        else:
            print(f"    — Sin artículo Wikipedia, usando datos base")
            wiki_data = None

    perfil = construir_perfil(candidato, wiki_data)

    # Guardar perfil individual
    ruta = f"datos_electorales/perfiles/{candidato['id']}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(perfil, f, ensure_ascii=False, indent=2)

    perfiles_generados.append(perfil)
    print(f"    ✓ Guardado: {ruta}")
    time.sleep(1)  # respetar rate limit de Wikipedia

# Guardar índice de todos los perfiles
indice = {
    "actualizado": FECHA,
    "total": len(perfiles_generados),
    "candidatos": [
        {
            "id":           p["id"],
            "nombre":       p["nombre"],
            "partido":      p["partido"],
            "cargo_actual": p["cargo_actual"],
            "fuente_wiki":  p["fuente_wiki"]
        }
        for p in perfiles_generados
    ]
}

with open("datos_electorales/perfiles/indice.json", "w", encoding="utf-8") as f:
    json.dump(indice, f, ensure_ascii=False, indent=2)

print(f"\n✓ {len(perfiles_generados)} perfiles generados")
print(f"✓ Índice guardado: datos_electorales/perfiles/indice.json")
