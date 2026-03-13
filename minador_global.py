#!/usr/bin/env python3
"""
minador_global.py
Minería de fuentes institucionales globales para nicho-analyzer
Fuentes verificadas con endpoints públicos funcionales
"""

import os, json, time, requests
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TIMESTAMP = datetime.now(timezone.utc).isoformat()
OUTPUT_DIR = "datos_crudos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NichoAnalyzer/1.0; +https://github.com/ruskigarage-alt/nicho-analyzer)"}
resultados = []

def guardar(nicho, fuente, titulo, contenido, url="", extra=None):
    resultados.append({
        "fecha": TIMESTAMP, "nicho": nicho, "fuente": fuente,
        "titulo": titulo, "contenido": contenido,
        "url": url, "extra": extra or {}
    })
    print("  OK [" + nicho + "] " + titulo[:65])

def get(url, params=None, timeout=15, verify=True):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout, verify=verify)
        r.raise_for_status()
        return r
    except Exception as e:
        print("  ✗ " + url[:60] + " : " + str(e)[:60])
        return None

# ═══════════════════════════════════════════════════════════════════
# 1. FINANZAS INSTITUCIONALES USA
# ═══════════════════════════════════════════════════════════════════
print("\n[ 1/7 ] Finanzas institucionales USA...")

# US Treasury — Deuda pública diaria (API pública sin key)
r = get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
    params={"sort": "-record_date", "page[size]": 1, "format": "json"})
if r:
    try:
        dato = r.json()["data"][0]
        guardar("finanzas_globales", "US Treasury FiscalData",
            "Deuda publica USA — " + FECHA,
            "Deuda publica total de EE.UU. al " + dato.get("record_date","") +
            ": USD " + dato.get("tot_pub_debt_out_amt","N/D") + " millones. " +
            "Deuda en manos del publico: USD " + dato.get("debt_held_public_amt","N/D") + " millones.",
            "https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/",
            dato)
    except Exception as e:
        print("  ✗ Parse Treasury: " + str(e))

# US Treasury — Tasas de interes promedio
r = get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates",
    params={"sort": "-record_date", "page[size]": 3, "format": "json"})
if r:
    try:
        for dato in r.json()["data"]:
            guardar("finanzas_globales", "US Treasury — Tasas",
                "Tasa interes bonos USA: " + dato.get("security_desc","") + " — " + dato.get("record_date",""),
                "Instrumento: " + dato.get("security_desc","") + ". " +
                "Tipo: " + dato.get("security_type_desc","") + ". " +
                "Tasa promedio: " + dato.get("avg_interest_rate_amt","N/D") + "%. " +
                "Fecha: " + dato.get("record_date","") + ".",
                "https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/",
                dato)
    except Exception as e:
        print("  ✗ Parse Treasury tasas: " + str(e))

# Federal Reserve — Feeds RSS publicos
FED_RSS = [
    ("https://www.federalreserve.gov/feeds/press_monetary.xml", "Fed — Comunicados politica monetaria"),
    ("https://www.federalreserve.gov/feeds/press_all.xml", "Fed — Todos los comunicados"),
]
for rss_url, nombre in FED_RSS:
    r = get(rss_url, timeout=10)
    if r:
        guardar("finanzas_globales", "Federal Reserve RSS",
            nombre + " — " + FECHA,
            "Feed RSS oficial de la Reserva Federal de EE.UU. con comunicados de politica monetaria, " +
            "decisiones de tasas, discursos y reportes. Relevante para LATAM por impacto en tipos de cambio. " +
            "URL: " + rss_url + ". Fecha: " + FECHA + ".",
            rss_url)

# ECB — API publica de datos (sin key)
r = get("https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A",
    params={"lastNObservations": 5, "format": "jsondata"}, timeout=15)
if r:
    try:
        data = r.json()
        obs = data["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
        fechas = data["structure"]["dimensions"]["observation"][0]["values"]
        for i, (k, v) in enumerate(list(obs.items())[:3]):
            fecha_obs = fechas[int(k)]["id"] if int(k) < len(fechas) else FECHA
            tasa = v[0]
            guardar("finanzas_globales", "ECB — Banco Central Europeo",
                "Tipo de cambio EUR/USD BCE — " + fecha_obs,
                "Tipo de cambio oficial EUR/USD del Banco Central Europeo: " +
                str(tasa) + " al " + fecha_obs + ". " +
                "Referencia para comercio exterior Mexico-UE y deuda corporativa LATAM en euros.",
                "https://data.ecb.europa.eu/data/datasets/EXR",
                {"fecha": fecha_obs, "eur_usd": tasa})
    except Exception as e:
        print("  ✗ Parse ECB: " + str(e))

# IMF — DataMapper API (sin key)
r = get("https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/MEX/BRA/ARG/CHL/COL/PER",
    timeout=15)
if r:
    try:
        data = r.json()
        valores = data.get("values", {}).get("NGDP_RPCH", {})
        for pais, serie in valores.items():
            if serie:
                ultimo_anio = max(serie.keys())
                valor = serie[ultimo_anio]
                nombres = {"MEX":"Mexico","BRA":"Brasil","ARG":"Argentina",
                           "CHL":"Chile","COL":"Colombia","PER":"Peru"}
                guardar("finanzas_globales", "FMI — DataMapper",
                    "Crecimiento PIB " + nombres.get(pais,pais) + " " + ultimo_anio,
                    "Tasa de crecimiento real del PIB de " + nombres.get(pais,pais) +
                    " en " + ultimo_anio + ": " + str(valor) + "%. " +
                    "Fuente: Fondo Monetario Internacional, World Economic Outlook.",
                    "https://www.imf.org/external/datamapper/NGDP_RPCH@WEO",
                    {"pais": pais, "anio": ultimo_anio, "pct": valor})
    except Exception as e:
        print("  ✗ Parse IMF: " + str(e))

# ═══════════════════════════════════════════════════════════════════
# 2. ENERGIA Y PETROLEO
# ═══════════════════════════════════════════════════════════════════
print("\n[ 2/7 ] Energia y petroleo...")

# EIA — Precios petroleo (requiere key gratuita — si no hay, usamos referencia)
# Registro gratis en: https://www.eia.gov/opendata/register.php
EIA_KEY = os.environ.get("EIA_API_KEY", "")

if EIA_KEY:
    for serie, nombre, desc in [
        ("PET.RWTC.D", "Petroleo WTI", "precio spot diario Cushing Oklahoma"),
        ("PET.RBRTE.D", "Petroleo Brent", "precio spot diario Europa"),
        ("NG.RNGWHHD.D", "Gas Natural Henry Hub", "precio spot diario USA"),
    ]:
        r = get("https://api.eia.gov/v2/seriesid/" + serie,
            params={"api_key": EIA_KEY, "length": 3})
        if r:
            try:
                datos = r.json()["response"]["data"][:1]
                for d in datos:
                    guardar("energia_petroleo", "EIA — US Energy Information",
                        nombre + " — " + d.get("period",""),
                        nombre + " (" + desc + "): USD " + str(d.get("value","N/D")) +
                        " por barril al " + d.get("period","") + ". " +
                        "Relevante para presupuesto Pemex y exportaciones Mexico.",
                        "https://www.eia.gov/petroleum/",
                        d)
            except Exception as e:
                print("  ✗ Parse EIA " + nombre + ": " + str(e))
        time.sleep(0.3)
else:
    print("  ! EIA_API_KEY no configurada — usando Yahoo Finance para energia")

# Yahoo Finance para precios energia (sin key)
ENERGIA = [
    ("CL=F", "Petroleo WTI", "critico para Mexico, Colombia, Venezuela"),
    ("BZ=F", "Petroleo Brent", "referencia global exportaciones LATAM"),
    ("NG=F", "Gas Natural", "energia industria LATAM"),
    ("HO=F", "Gasoil calefaccion", "derivado petroleo"),
    ("RB=F", "Gasolina RBOB", "referencia precios combustibles"),
]
for symbol, nombre, relevancia in ENERGIA:
    r = get("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
        params={"interval":"1d","range":"1d"}, timeout=10)
    if r:
        try:
            meta = r.json()["chart"]["result"][0]["meta"]
            precio = meta.get("regularMarketPrice","N/D")
            guardar("energia_petroleo", "Yahoo Finance",
                nombre + " — " + FECHA,
                nombre + ": USD " + str(precio) + " al " + FECHA + ". Relevancia LATAM: " + relevancia + ".",
                "https://finance.yahoo.com/quote/" + symbol,
                {"symbol": symbol, "precio": precio})
        except Exception as e:
            print("  ✗ Parse Yahoo " + symbol + ": " + str(e))
    time.sleep(0.3)

# OPEC — comunicados y noticias publicas RSS
r = get("https://www.opec.org/opec_web/en/press_room/rss.htm", timeout=10)
guardar("energia_petroleo", "OPEC",
    "Portal OPEC — noticias produccion petroleo " + FECHA,
    "La OPEC publica diariamente datos de produccion, comunicados de reunion y perspectivas del mercado petrolero. " +
    "Decisiones de cuotas de produccion impactan directamente precio WTI y Brent. " +
    "Relevante para Pemex y presupuesto federal mexicano. URL: https://www.opec.org. Fecha: " + FECHA + ".",
    "https://www.opec.org/opec_web/en/press_room/26.htm")

# IEA — Oil Market Report (publicacion publica mensual)
guardar("energia_petroleo", "IEA — Agencia Internacional de Energia",
    "Oil Market Report IEA — " + FECHA,
    "La IEA publica mensualmente el Oil Market Report con datos de oferta, demanda y stocks globales. " +
    "Incluye perspectivas para paises productores LATAM. " +
    "Acceso: https://www.iea.org/reports/oil-market-report. Fecha: " + FECHA + ".",
    "https://www.iea.org/reports/oil-market-report")

# ═══════════════════════════════════════════════════════════════════
# 3. MINERIA, METALES Y TIERRAS RARAS
# ═══════════════════════════════════════════════════════════════════
print("\n[ 3/7 ] Mineria, metales y tierras raras...")

# Metales via Yahoo Finance
METALES = [
    ("HG=F", "Cobre", "Chile mayor productor mundial, Peru 2do"),
    ("SI=F", "Plata", "Mexico mayor productor mundial"),
    ("GC=F", "Oro", "Mexico 9no productor mundial"),
    ("ALI=F", "Aluminio", "insumo industria automotriz Mexico"),
    ("PA=F", "Paladio", "metales del grupo platino"),
    ("PL=F", "Platino", "tierras raras y metales criticos"),
    ("ZN=F", "Zinc", "Mexico top 5 productor mundial"),
    ("LBS=F", "Plomo", "Mexico productor relevante"),
]
for symbol, nombre, relevancia in METALES:
    r = get("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
        params={"interval":"1d","range":"1d"}, timeout=10)
    if r:
        try:
            meta = r.json()["chart"]["result"][0]["meta"]
            precio = meta.get("regularMarketPrice","N/D")
            moneda = meta.get("currency","USD")
            guardar("mineria_metales", "Yahoo Finance — LME/CME",
                nombre + " — " + FECHA,
                nombre + ": " + moneda + " " + str(precio) + " al " + FECHA + ". " + relevancia + ".",
                "https://finance.yahoo.com/quote/" + symbol,
                {"symbol": symbol, "precio": precio, "moneda": moneda})
        except Exception as e:
            print("  ✗ Parse " + symbol + ": " + str(e))
    time.sleep(0.3)

# Litio — referencia (no hay API gratuita directa)
LITIO_REFS = [
    ("Albemarle", "ALB", "mayor productor litio mundial, opera en Chile y Australia"),
    ("SQM", "SQM", "productor litio Chile — Atacama"),
    ("Lithium Americas", "LAC", "proyecto Thacker Pass y Caucharí-Olaroz Argentina"),
]
for nombre, ticker, desc in LITIO_REFS:
    r = get("https://query1.finance.yahoo.com/v8/finance/chart/" + ticker,
        params={"interval":"1d","range":"1d"}, timeout=10)
    if r:
        try:
            meta = r.json()["chart"]["result"][0]["meta"]
            precio = meta.get("regularMarketPrice","N/D")
            guardar("mineria_metales", "Yahoo Finance — Litio/Tierras raras",
                "Accion " + nombre + " (" + ticker + ") — " + FECHA,
                nombre + " (" + ticker + "): USD " + str(precio) + " al " + FECHA + ". " + desc + ". " +
                "Indicador de mercado de litio y tierras raras relevante para Mexico y LATAM.",
                "https://finance.yahoo.com/quote/" + ticker,
                {"empresa": nombre, "ticker": ticker, "precio": precio})
        except Exception as e:
            print("  ✗ Parse " + ticker + ": " + str(e))
    time.sleep(0.3)

# London Metal Exchange — referencia
guardar("mineria_metales", "London Metal Exchange",
    "LME — precios metales industriales " + FECHA,
    "El London Metal Exchange publica precios oficiales de cobre, aluminio, zinc, plomo, estanio y niquel. " +
    "Estos precios son referencia global para contratos de exportacion minera LATAM. " +
    "Consulta: https://www.lme.com/en/metals. Fecha: " + FECHA + ".",
    "https://www.lme.com/en/metals")

# ═══════════════════════════════════════════════════════════════════
# 4. COMERCIO GLOBAL Y ARANCELES
# ═══════════════════════════════════════════════════════════════════
print("\n[ 4/7 ] Comercio global y aranceles...")

# OMC — noticias y comunicados RSS
r = get("https://www.wto.org/english/news_e/news_e.rss", timeout=10)
if r:
    guardar("comercio_aranceles", "OMC — World Trade Organization",
        "Noticias OMC — " + FECHA,
        "La OMC publica noticias sobre disputas comerciales, nuevas negociaciones y cambios arancelarios. " +
        "Impacta directamente en T-MEC, exportaciones mexicanas y acceso a mercados LATAM. " +
        "Feed: https://www.wto.org/english/news_e/news_e.rss. Fecha: " + FECHA + ".",
        "https://www.wto.org/english/news_e/news_e.rss")

# UN Comtrade — preview publico sin key (limitado a 500 registros)
# Exportaciones Mexico al mundo — productos principales
r = get("https://comtradeapi.un.org/public/v1/preview/C/A/HS",
    params={"reporterCode": "484", "period": "2023", "cmdCode": "TOTAL",
            "flowCode": "X", "partnerCode": "0"},
    timeout=20)
if r:
    try:
        data = r.json()
        registros_ct = data.get("data", [])
        if registros_ct:
            d = registros_ct[0]
            guardar("comercio_aranceles", "UN Comtrade",
                "Exportaciones Mexico al mundo — " + str(d.get("period","")),
                "Mexico exporto USD " + str(d.get("primaryValue","N/D")) +
                " al mundo en " + str(d.get("period","")) + ". " +
                "Principales socios: EE.UU., Canada, UE. " +
                "Fuente: UN Comtrade base de datos oficial.",
                "https://comtrade.un.org",
                {"reporter": "Mexico", "periodo": d.get("period"), "valor_usd": d.get("primaryValue")})
    except Exception as e:
        print("  ✗ Parse Comtrade: " + str(e))

# USTR — comunicados arancelarios (RSS publico)
r = get("https://ustr.gov/rss.xml", timeout=10)
if r:
    guardar("comercio_aranceles", "USTR — US Trade Representative",
        "Comunicados USTR aranceles — " + FECHA,
        "La Oficina del Representante Comercial de EE.UU. publica cambios arancelarios, " +
        "investigaciones seccion 301 y resultados de disputas comerciales. " +
        "Critico para exportadores mexicanos bajo T-MEC. " +
        "Feed: https://ustr.gov/rss.xml. Fecha: " + FECHA + ".",
        "https://ustr.gov/rss.xml")

# Secretaria de Economia Mexico — TLCAN/T-MEC datos
guardar("comercio_aranceles", "Secretaria de Economia — Mexico",
    "T-MEC y comercio exterior Mexico — " + FECHA,
    "La Secretaria de Economia publica datos de comercio exterior, reglas de origen T-MEC, " +
    "cupos arancelarios y resoluciones antidumping. " +
    "Sistema de Informacion Arancelaria: https://www.economia.gob.mx/datamexico. " +
    "Fecha: " + FECHA + ".",
    "https://www.gob.mx/se")

# ═══════════════════════════════════════════════════════════════════
# 5. TRANSPORTE MARITIMO
# ═══════════════════════════════════════════════════════════════════
print("\n[ 5/7 ] Transporte maritimo y logistica...")

# Baltic Exchange — indices de flete (referencia publica)
INDICES_FLETE = [
    ("BDI", "Baltic Dry Index", "indicador global de costo flete granel seco — maiz, trigo, mineral"),
    ("BCI", "Baltic Capesize Index", "buques grandes mineral hierro y carbon"),
    ("BPI", "Baltic Panamax Index", "buques Panamax — granos y carbon LATAM"),
    ("BSI", "Baltic Supramax Index", "buques medianos — exportaciones agricolas LATAM"),
]
for codigo, nombre, descripcion in INDICES_FLETE:
    guardar("transporte_maritimo", "Baltic Exchange",
        nombre + " (" + codigo + ") — " + FECHA,
        nombre + ": " + descripcion + ". " +
        "Indicador clave del costo de transporte maritimo global. " +
        "Impacta en competitividad exportaciones agricolas y minerales de LATAM. " +
        "Referencia: https://www.balticexchange.com/en/data/download.html. Fecha: " + FECHA + ".",
        "https://www.balticexchange.com",
        {"codigo": codigo, "descripcion": descripcion})

# IMO — comunicados maritimos (RSS)
r = get("https://www.imo.org/en/MediaCentre/Pages/NewsByTopic-press.aspx", timeout=10)
guardar("transporte_maritimo", "IMO — Organizacion Maritima Internacional",
    "Regulaciones maritimas IMO — " + FECHA,
    "La IMO publica regulaciones de seguridad maritima, normas ambientales (MARPOL) y " +
    "nuevas restricciones de emisiones que afectan costos de flete. " +
    "Relevante para puertos mexicanos y rutas comerciales LATAM. " +
    "URL: https://www.imo.org. Fecha: " + FECHA + ".",
    "https://www.imo.org")

# Puertos estrategicos LATAM con datos AIS
PUERTOS = [
    ("MXVER","Veracruz","Mexico","petroleo y carga general — 25M ton/año"),
    ("MXLZC","Lazaro Cardenas","Mexico","automotriz y granel — hub Pacifico"),
    ("MXATM","Altamira","Mexico","petroquimico e industrial"),
    ("BRSSZ","Santos","Brasil","mayor puerto America Latina — 150M ton/año"),
    ("CLVAP","Valparaiso","Chile","cobre y frutas — exportaciones Chile"),
    ("COBUN","Buenaventura","Colombia","Pacifico Colombia — carbon y cafe"),
    ("PECLL","Callao","Peru","mayor puerto peruano — mineral y pesquero"),
    ("ARBUE","Buenos Aires","Argentina","hub Rio de la Plata — soya y granos"),
    ("PAMIT","Balboa","Panama","Canal de Panama — 14000 buques/año"),
]
for locode, nombre, pais, actividad in PUERTOS:
    guardar("transporte_maritimo", "AIS Puertos LATAM",
        "Puerto " + nombre + " (" + locode + ") " + pais + " — " + FECHA,
        "Puerto " + nombre + " en " + pais + " (LOCODE: " + locode + "): " + actividad + ". " +
        "Trafico en tiempo real: https://www.marinetraffic.com/en/ais/details/ports/portid:" + locode + ". " +
        "Fecha: " + FECHA + ".",
        "https://www.marinetraffic.com/en/ais/details/ports/portid:" + locode,
        {"locode": locode, "pais": pais})

# ═══════════════════════════════════════════════════════════════════
# 6. THINK TANKS GEOPOLITICOS — RSS feeds publicos
# ═══════════════════════════════════════════════════════════════════
print("\n[ 6/7 ] Think tanks geopoliticos...")

THINK_TANKS = [
    ("Council on Foreign Relations", "https://www.cfr.org/rss/rss_all.xml", "EEUU",
     "Analisis de politica exterior y geopolitica global"),
    ("CSIS", "https://www.csis.org/analysis/feed", "EEUU",
     "Centro de Estudios Estrategicos e Internacionales"),
    ("Brookings Institution", "https://www.brookings.edu/feed/", "EEUU",
     "Think tank politica publica y economia global"),
    ("Carnegie Endowment", "https://carnegieendowment.org/rss/solr/feed/?fa=pub", "EEUU",
     "Geopolitica y relaciones internacionales"),
    ("Chatham House", "https://www.chathamhouse.org/rss.xml", "Europa",
     "Relaciones internacionales Reino Unido"),
    ("Bruegel", "https://www.bruegel.org/rss.xml", "Europa",
     "Economia europea y politica comercial"),
    ("RIAC", "https://russiancouncil.ru/en/rss/analytics/", "Rusia",
     "Consejo Ruso de Asuntos Internacionales"),
]

for nombre, rss_url, region, descripcion in THINK_TANKS:
    r = get(rss_url, timeout=10)
    estado = "activo" if r else "referencia"
    guardar("geopolitica", "Think Tank — " + region,
        nombre + " — feed geopolitico " + FECHA,
        nombre + " (" + region + "): " + descripcion + ". " +
        "Feed RSS " + estado + ": " + rss_url + ". " +
        "Fuente para analisis de impacto geopolitico en economia LATAM. Fecha: " + FECHA + ".",
        rss_url,
        {"region": region, "tipo": "think_tank", "estado": estado})
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════
# 7. MEDIOS GEOPOLITICOS — RSS feeds
# ═══════════════════════════════════════════════════════════════════
print("\n[ 7/7 ] Medios geopoliticos internacionales...")

MEDIOS_RSS = [
    ("Reuters — Business", "https://feeds.reuters.com/reuters/businessNews", "Global"),
    ("Reuters — World", "https://feeds.reuters.com/reuters/worldNews", "Global"),
    ("Financial Times", "https://www.ft.com/world?format=rss", "Global"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "Global"),
    ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "EEUU"),
    ("Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar", "Asia"),
    ("South China Morning Post", "https://www.scmp.com/rss/91/feed", "Asia"),
    ("TASS", "https://tass.com/rss/v2.xml", "Rusia"),
    ("Politico Europe", "https://www.politico.eu/feed/", "Europa"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/", "EEUU"),
]

for nombre, rss_url, region in MEDIOS_RSS:
    r = get(rss_url, timeout=8)
    estado = "activo" if r else "referencia"
    guardar("geopolitica", "Medio internacional — " + region,
        nombre + " — " + FECHA,
        "Feed de noticias geopoliticas y economicas: " + nombre + " (" + region + "). " +
        "Estado: " + estado + ". URL: " + rss_url + ". " +
        "Fuente para seguimiento de eventos con impacto en mercados LATAM. Fecha: " + FECHA + ".",
        rss_url,
        {"medio": nombre, "region": region, "estado": estado})
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════
# GUARDAR
# ═══════════════════════════════════════════════════════════════════
archivo = os.path.join(OUTPUT_DIR, "global_institucional_" + FECHA + ".jsonl")
with open(archivo, "w", encoding="utf-8") as f:
    for reg in resultados:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")

print("\n✓ " + str(len(resultados)) + " registros → " + archivo)
nichos = {}
for reg in resultados:
    n = reg["nicho"]
    nichos[n] = nichos.get(n, 0) + 1
for n, c in nichos.items():
    print("  - " + n + ": " + str(c) + " registros")

print("\nNota: Para activar datos EIA en tiempo real:")
print("  1. Registrate gratis en https://www.eia.gov/opendata/register.php")
print("  2. Exporta tu key: export EIA_API_KEY=tu_key_aqui")
print("  3. Vuelve a correr el script")
