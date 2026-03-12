#!/usr/bin/env python3
"""minador_economico.py v2 — Yahoo Finance + fuentes corregidas"""

import os, json, time, requests
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TIMESTAMP = datetime.now(timezone.utc).isoformat()
OUTPUT_DIR = "datos_crudos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NichoAnalyzer/1.0)"}
resultados = []

def guardar(nicho, fuente, titulo, contenido, url="", extra=None):
    resultados.append({"fecha": TIMESTAMP, "nicho": nicho, "fuente": fuente,
        "titulo": titulo, "contenido": contenido, "url": url, "extra": extra or {}})
    print(f"  ✓ [{nicho}] {titulo[:70]}")

def safe_get(url, params=None, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  ✗ {url[:55]}: {e}")
        return None

# ── 1. TIPOS DE CAMBIO ──────────────────────────────────────────
print("\n[ 1/4 ] Mercados financieros...")
r = safe_get("https://api.exchangerate-api.com/v4/latest/USD")
if r:
    tasas = r.json().get("rates", {})
    for codigo, moneda in [("MXN","Peso mexicano"),("BRL","Real brasileño"),
        ("ARS","Peso argentino"),("CLP","Peso chileno"),
        ("COP","Peso colombiano"),("PEN","Sol peruano")]:
        tasa = tasas.get(codigo)
        if tasa:
            guardar("mercados_latam","ExchangeRate-API",
                f"Tipo de cambio USD/{codigo} — {FECHA}",
                f"1 USD = {tasa} {codigo} ({moneda}) al {FECHA}.",
                "https://api.exchangerate-api.com",
                {"par": f"USD/{codigo}", "tasa": tasa})

# ── COMMODITIES VIA YAHOO FINANCE ───────────────────────────────
COMMODITIES = [
    ("CL=F","Petróleo WTI","crítico para México y Colombia"),
    ("BZ=F","Petróleo Brent","referencia global exportaciones LATAM"),
    ("HG=F","Cobre","crítico para Chile y Perú"),
    ("SI=F","Plata","México mayor productor mundial"),
    ("GC=F","Oro","reservas bancos centrales LATAM"),
    ("ZC=F","Maíz","crítico para México y Argentina"),
    ("ZS=F","Soya","crítico para Brasil y Argentina"),
    ("KC=F","Café","Colombia, Brasil, México"),
    ("NG=F","Gas natural","energía industria LATAM"),
]
for symbol, nombre, relevancia in COMMODITIES:
    r = safe_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"interval":"1d","range":"1d"}, timeout=10)
    if r:
        try:
            meta = r.json()["chart"]["result"][0]["meta"]
            precio = meta.get("regularMarketPrice","N/D")
            moneda_sym = meta.get("currency","USD")
            guardar("mercados_latam","Yahoo Finance",
                f"Commodity {nombre} — {FECHA}",
                f"{nombre}: {moneda_sym} {precio} al {FECHA}. Relevancia LATAM: {relevancia}.",
                f"https://finance.yahoo.com/quote/{symbol}",
                {"symbol": symbol, "precio": precio})
        except Exception as e:
            print(f"  ✗ Parse {symbol}: {e}")
    time.sleep(0.4)

# ── 2. LICITACIONES ─────────────────────────────────────────────
print("\n[ 2/4 ] Licitaciones y contratos gobierno...")
r = safe_get("https://search.worldbank.org/api/v2/projects",
    params={"format":"json","regioncode":"LCR","status":"Active",
            "rows":12,"os":0,"fl":"id,project_name,countryname,totalamt,sector1,objective"})
if r:
    try:
        proyectos = r.json().get("projects", {})
        items = list(proyectos.values()) if isinstance(proyectos, dict) else proyectos
        for item in items[:10]:
            nombre = item.get("project_name","Sin título")
            pais = item.get("countryname","LATAM")
            monto = item.get("totalamt","N/D")
            sector = item.get("sector1",{})
            sn = sector.get("Name","N/D") if isinstance(sector, dict) else str(sector)
            objetivo = str(item.get("objective",""))[:200]
            pid = item.get("id","")
            guardar("licitaciones_gobierno","Banco Mundial — LATAM",
                f"Proyecto BM [{pais}]: {nombre[:65]}",
                f"País: {pais}. Sector: {sn}. Monto: USD {monto}. Objetivo: {objetivo}.",
                f"https://projects.worldbank.org/en/projects-operations/project-detail/{pid}",
                {"pais": pais, "monto_usd": monto})
    except Exception as e:
        print(f"  ✗ Parse Banco Mundial: {e}")

for titulo, contenido, url in [
    ("CompraNet México — portal licitaciones",
     f"Sistema oficial de contrataciones APF México. Licitaciones públicas, invitaciones y adjudicaciones directas. URL: https://compranet.hacienda.gob.mx. Fecha: {FECHA}.",
     "https://compranet.hacienda.gob.mx"),
    ("UNGM — licitaciones ONU en LATAM",
     f"Licitaciones de UNOPS, PNUD, UNICEF, FAO activas en América Latina. URL: https://www.ungm.org/Public/Notice. Fecha: {FECHA}.",
     "https://www.ungm.org/Public/Notice"),
]:
    guardar("licitaciones_gobierno","Referencia portal",titulo,contenido,url)

# ── 3. BUQUES ───────────────────────────────────────────────────
print("\n[ 3/4 ] Movimiento de buques...")
PUERTOS = [
    ("MXVER","Veracruz","México","petrolero y carga general"),
    ("MXLZC","Lázaro Cárdenas","México","automotriz y granel"),
    ("MXATM","Altamira","México","petroquímico e industrial"),
    ("BRSSZ","Santos","Brasil","mayor puerto Sudamérica"),
    ("CLVAP","Valparaíso","Chile","cobre y frutas"),
    ("COBUN","Buenaventura","Colombia","Pacífico Colombia"),
    ("PECLL","Callao","Perú","mayor puerto peruano"),
    ("ARBUE","Buenos Aires","Argentina","Río de la Plata"),
    ("PAMIT","Balboa","Panamá","Canal de Panamá"),
]
for locode, nombre, pais, actividad in PUERTOS:
    guardar("movimiento_buques","AIS Público",
        f"Puerto {nombre}, {pais} ({locode})",
        f"Puerto {nombre} ({locode}), {pais}. Actividad: {actividad}. "
        f"Tráfico en vivo: https://www.marinetraffic.com/en/ais/details/ports/portid:{locode}. Fecha: {FECHA}.",
        f"https://www.marinetraffic.com/en/ais/details/ports/portid:{locode}",
        {"locode": locode, "pais": pais})

ZONAS = [
    ("Canal de Panamá",8.9943,-79.5674,"14,000+ buques/año, paso Asia-LATAM"),
    ("Golfo de México",25.0,-90.0,"exportaciones petróleo México y USA"),
    ("Puerto Santos Brasil",-23.95,-46.33,"mayor puerto América Latina"),
    ("Estrecho de Magallanes",-52.6,-70.9,"ruta alternativa al Canal"),
]
for zona, lat, lon, desc in ZONAS:
    guardar("movimiento_buques","AIS Zonas Estratégicas",
        f"Zona marítima: {zona}",
        f"{zona} ({lat},{lon}): {desc}. "
        f"Monitor: https://www.marinetraffic.com/en/ais/home/centerx:{lon}/centery:{lat}/zoom:7. Fecha: {FECHA}.",
        f"https://www.marinetraffic.com/en/ais/home/centerx:{lon}/centery:{lat}/zoom:7",
        {"lat": lat, "lon": lon})

# ── 4. ARANCELES ────────────────────────────────────────────────
print("\n[ 4/4 ] Aranceles y aduanas...")
PAISES = [
    ("MEX","México","T-MEC, TLCUEM, 12 TLCs vigentes"),
    ("BRA","Brasil","MERCOSUR, arancel externo común"),
    ("ARG","Argentina","MERCOSUR, restricciones importación activas"),
    ("CHL","Chile","65+ TLCs — economía más abierta LATAM"),
    ("COL","Colombia","TLC con USA, UE, Alianza del Pacífico"),
    ("PER","Perú","Alianza del Pacífico, TLC con China"),
]
for codigo, pais, desc in PAISES:
    guardar("aranceles_aduanas","OMC — Perfiles arancelarios",
        f"Perfil arancelario {pais} — {FECHA}",
        f"{pais} (OMC: {codigo}): {desc}. "
        f"Datos: https://tariffanalysis.wto.org. Fecha: {FECHA}.",
        f"https://tariffanalysis.wto.org/summary/index.aspx?lang=1&rg={codigo}",
        {"pais": pais, "codigo_omc": codigo})

guardar("aranceles_aduanas","DOF México",
    f"Cambios arancelarios DOF — {FECHA}",
    f"El DOF publica modificaciones a la LIGIE y acuerdos comerciales. "
    f"Consulta: https://www.dof.gob.mx. Fecha: {FECHA}.",
    "https://www.dof.gob.mx")

guardar("aranceles_aduanas","USTR / Federal Register",
    f"Aranceles USA impacto LATAM — {FECHA}",
    f"Cambios arancelarios EE.UU. con impacto en exportaciones LATAM (2025-2026): "
    f"acero, aluminio, productos agrícolas. "
    f"Fuente: https://ustr.gov/tariff-actions. Fecha: {FECHA}.",
    "https://ustr.gov/tariff-actions",
    {"relevancia": "alta_2026"})

guardar("aranceles_aduanas","CEPAL",
    f"Monitor comercio exterior LATAM — {FECHA}",
    f"CEPAL publica estadísticas trimestrales de comercio exterior para ALC. "
    f"Base de datos: https://statistics.cepal.org/portal/cepalstat/. Fecha: {FECHA}.",
    "https://statistics.cepal.org/portal/cepalstat/")

# ── GUARDAR ─────────────────────────────────────────────────────
archivo = os.path.join(OUTPUT_DIR, f"economico_global_{FECHA}.jsonl")
with open(archivo, "w", encoding="utf-8") as f:
    for reg in resultados:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")

print(f"\n✓ {len(resultados)} registros → {archivo}")
nichos = {}
for reg in resultados:
    nichos[reg["nicho"]] = nichos.get(reg["nicho"], 0) + 1
for n, c in nichos.items():
    print(f"  - {n}: {c} registros")
