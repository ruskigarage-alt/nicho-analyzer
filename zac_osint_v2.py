#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
ZAC-OSINT v2.0 — Motor OSINT Geopolítico Personal tipo Stratfor/Palantir
Estado de Zacatecas | Elecciones Gobernatura 2027 | Mercados Globales
=============================================================================
Autor     : Nicho Analyzer / Alfred
Versión   : 2.0.0  (2026-03)

Módulos:
  1.  CatalogoFuentes      — 200+ feeds RSS organizados por región/tipo
  2.  MinadorRSS           — scraping con rate-limit, retry y caché
  3.  MinadorGoogleNews    — búsquedas RSS vía Google News
  4.  MinadorMercados      — precios de activos via Yahoo Finance / yfinance
  5.  AnalizadorOSINT      — clasificación multi-eje + detección de señales
  6.  MatrizCorrelaciones  — correlaciones geopolíticas (Brzezinski, Mearsheimer,
                             Friedman, Kissinger, Zeihan, Dalio)
  7.  DetectorPalabras     — keywords globales: Trump, Putin, Netanyahu, misiles…
  8.  PerfilCandidatos     — scoring compuesto 7 candidatos Zacatecas
  9.  HistorialDB          — base de datos SQLite local con serie temporal
  10. Exportador           — JSON/JSONL/JSONLD/CSV + estadísticas completas

Dependencias:
  pip install feedparser requests beautifulsoup4 pandas numpy \
              python-dateutil lxml yfinance sqlite3 schedule newsapi-python

Uso:
  python3 zac_osint_v2.py --run-all
  python3 zac_osint_v2.py --solo-mercados
  python3 zac_osint_v2.py --solo-electoral
  python3 zac_osint_v2.py --historial --dias 90
  python3 zac_osint_v2.py --exportar-csv output/
  python3 zac_osint_v2.py --daemon --intervalo 360
=============================================================================
"""

import json, re, time, logging, hashlib, argparse, sqlite3, csv, os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import quote_plus

# ─── DEPENDENCIAS OPCIONALES ─────────────────────────────────────────────────
try:
    import feedparser
    FEEDPARSER_OK = True
except ImportError:
    FEEDPARSER_OK = False
    print("[AVISO] pip install feedparser")

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False
    print("[AVISO] pip install requests beautifulsoup4")

try:
    from newsapi import NewsApiClient
    NEWSAPI_OK = True
except ImportError:
    NEWSAPI_OK = False
    print("[AVISO] pip install newsapi-python")

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv('NEWS_API_KEY')  # Obtén tu API key de https://newsapi.org

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False
    print("[AVISO] pip install yfinance  (mercados financieros)")

try:
    import pandas as pd
    import numpy as np
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("[AVISO] pip install pandas numpy")

try:
    import schedule
    SCHEDULE_OK = True
except ImportError:
    SCHEDULE_OK = False

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("zac_osint.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("ZAC-OSINT-v2")

# =============================================================================
#  MÓDULO 1: CATÁLOGO DE FUENTES — 200+ RSS
# =============================================================================

class CatalogoFuentes:
    """Registro centralizado de 200+ fuentes RSS organizadas por región y tipo."""

    # ── ZACATECAS LOCALES ──────────────────────────────────────────────────────
    LOCALES_ZAC = {
        "ntr_zacatecas":          "https://www.ntrzacatecas.com/feed/",
        "ljz_zacatecas":          "https://ljz.mx/feed/",
        "sol_zacatecas":          "https://www.elsoldezacatecas.com.mx/rss.xml",
        "imagen_zacatecas":       "https://imagenzacatecas.com/feed/",
        "zacatecas_en_imagen":    "https://www.zacatecasenimagen.com/feed/",
        "codigo_zacatecas":       "https://codigozacatecas.com/feed/",
        "meganoticias_zac":       "https://www.meganoticias.mx/zacatecas/rss.xml",
        "ecodiario_mx":           "https://ecodiario.mx/feed/",
        "oem_zacatecas":          "https://www.oem.com.mx/elsoldezacatecas/rss.xml",
        "milenio_zacatecas":      "https://www.milenio.com/rss/estados/zacatecas.xml",
    }

    # ── INSTITUCIONALES ZACATECAS ─────────────────────────────────────────────
    INSTITUCIONALES_ZAC = {
        "gobierno_zacatecas":     "https://www.zacatecas.gob.mx/feed/",
        "capital_zacatecas":      "https://portal.capitaldezacatecas.gob.mx/feed/",
        "ieez":                   "https://ieez.org.mx/noticias/feed/",
        "conago":                 "https://www.conago.org.mx/feed/",
        "compranet_zac":          "https://upcp-compranet.buengobierno.gob.mx/rss/",
    }

    # ── NACIONALES MÉXICO ─────────────────────────────────────────────────────
    NACIONALES_MX = {
        "la_jornada":             "https://www.jornada.com.mx/rss/politica.xml",
        "la_jornada_economia":    "https://www.jornada.com.mx/rss/economia.xml",
        "expansion":              "https://expansion.mx/rss",
        "expansion_economia":     "https://expansion.mx/economia/rss",
        "milenio_nacional":       "https://www.milenio.com/rss",
        "milenio_politica":       "https://www.milenio.com/rss/politica",
        "proceso":                "https://www.proceso.com.mx/rss/politica",
        "proceso_economia":       "https://www.proceso.com.mx/rss/economia",
        "animal_politico":        "https://animalpolitico.com/feed",
        "el_financiero":          "https://www.elfinanciero.com.mx/rss/ultima-hora.xml",
        "el_financiero_economia": "https://www.elfinanciero.com.mx/rss/economia.xml",
        "el_economista":          "https://www.eleconomista.com.mx/rss/rss.xml",
        "el_economista_mercados": "https://www.eleconomista.com.mx/rss/mercados.xml",
        "excelsior":              "https://www.excelsior.com.mx/rss.xml",
        "excelsior_nacional":     "https://www.excelsior.com.mx/nacional/rss.xml",
        "reforma":                "https://www.reforma.com/rss/portada.xml",
        "el_universal":           "https://www.eluniversal.com.mx/rss.xml",
        "el_universal_nacion":    "https://www.eluniversal.com.mx/nacion/rss.xml",
        "sin_embargo":            "https://www.sinembargo.mx/feed",
        "aristegui_noticias":     "https://aristeguinoticias.com/feed/",
        "nexos":                  "https://www.nexos.com.mx/feed/",
        "letras_libres":          "https://letraslibres.com/feed/",
        "capital_mexico":         "https://www.capital21.cdmx.gob.mx/noticias/feed/",
        "notimex":                "https://www.notimex.com.mx/rss/noticias.xml",
        "forbes_mx":              "https://www.forbes.com.mx/feed/",
        "bloomberg_linea_mx":     "https://www.bloomberglinea.com/rss/feed.xml",
        "oem_nacional":           "https://www.oem.com.mx/rss.xml",
        "meganoticias_nacional":  "https://www.meganoticias.mx/nacional/rss.xml",
    }

    # ── INSTITUCIONALES MÉXICO ────────────────────────────────────────────────
    INSTITUCIONALES_MX = {
        "ine":                    "https://www.ine.mx/informacion-para-medios/boletin-prensa/feed/",
        "banxico":                "https://www.banxico.org.mx/rss/comunicados.xml",
        "banxico_estadisticas":   "https://www.banxico.org.mx/rss/estadisticas.xml",
        "coneval":                "https://www.coneval.org.mx/Informes/Coordinacion/feed.aspx",
        "inegi":                  "https://www.inegi.org.mx/rss/noticias.xml",
        "sat":                    "https://home.sat.gob.mx/rss/noticias.xml",
        "shcp":                   "https://www.gob.mx/shcp/es/archivo/rss",
        "sre_mexico":             "https://www.gob.mx/sre/es/archivo/rss",
        "sedena":                 "https://www.gob.mx/sedena/es/archivo/rss",
        "pemex":                  "https://www.pemex.com/saladeprensa/boletines_nacionales/rss.xml",
        "cfe":                    "https://www.cfe.mx/noticias/rss",
        "gobierno_federal":       "https://www.gob.mx/presidencia/es/archivo/rss",
    }

    # ── LATINOAMÉRICA ─────────────────────────────────────────────────────────
    LATAM = {
        "infobae_latam":          "https://www.infobae.com/feeds/rss/",
        "infobae_economia":       "https://www.infobae.com/economia/rss/",
        "clarin_argentina":       "https://www.clarin.com/rss/lo-ultimo/",
        "la_nacion_ar":           "https://www.lanacion.com.ar/arcio/rss/",
        "folha_brasil":           "https://feeds.folha.uol.com.br/folha/mundo/rss091.xml",
        "el_tiempo_colombia":     "https://www.eltiempo.com/rss/politica.xml",
        "el_comercio_peru":       "https://elcomercio.pe/rss/",
        "la_tercera_chile":       "https://www.latercera.com/feed/",
        "el_pais_uruguay":        "https://www.elpais.com.uy/rss.xml",
        "el_nacional_venezuela":  "https://www.elnacional.com/rss/",
        "telesur":                "https://www.telesurtv.net/rss/noticias.xml",
        "nodal_latam":            "https://www.nodal.am/feed/",
        "nacla":                  "https://nacla.org/rss.xml",
    }

    # ── ESTADOS UNIDOS / ANGLOSAJÓN ────────────────────────────────────────────
    USA_UK = {
        "reuters_world":          "https://feeds.reuters.com/reuters/worldNews",
        "reuters_business":       "https://feeds.reuters.com/reuters/businessNews",
        "reuters_latam":          "https://feeds.reuters.com/reuters/latamNewsHeadlines",
        "ap_world":               "https://feeds.apnews.com/apnews/worldnews",
        "ap_politics":            "https://feeds.apnews.com/apnews/politics",
        "ap_economy":             "https://feeds.apnews.com/apnews/economy",
        "bloomberg_markets":      "https://feeds.bloomberg.com/markets/news.rss",
        "bloomberg_politics":     "https://feeds.bloomberg.com/politics/news.rss",
        "nyt_world":              "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "nyt_business":           "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "nyt_politics":           "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "washington_post":        "https://feeds.washingtonpost.com/rss/world",
        "guardian_world":         "https://www.theguardian.com/world/rss",
        "guardian_us":            "https://www.theguardian.com/us-news/rss",
        "guardian_economy":       "https://www.theguardian.com/business/economics/rss",
        "ft_world":               "https://www.ft.com/world?format=rss",
        "ft_markets":             "https://www.ft.com/markets?format=rss",
        "economist":              "https://www.economist.com/international/rss.xml",
        "wsj_world":              "https://feeds.content.dowjones.io/public/rss/mw_bulletins",
        "politico":               "https://www.politico.com/rss/politicopicks.xml",
        "politico_europe":        "https://www.politico.eu/feed/",
        "foreign_affairs":        "https://www.foreignaffairs.com/rss.xml",
        "foreign_policy":         "https://foreignpolicy.com/feed/",
        "council_foreign_rel":    "https://www.cfr.org/rss.xml",
        "brookings":              "https://www.brookings.edu/feed/",
        "rand_corp":              "https://www.rand.org/pubs/all.xml",
        "stratfor_free":          "https://worldview.stratfor.com/rss.xml",
        "atlantic_council":       "https://www.atlanticcouncil.org/feed/",
        "csis":                   "https://www.csis.org/feed",
        "chatham_house":          "https://www.chathamhouse.org/rss.xml",
        "bbc_world":              "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bbc_business":           "https://feeds.bbci.co.uk/news/business/rss.xml",
        "bbc_mundo":              "https://feeds.bbci.co.uk/mundo/rss.xml",
        "cnbc_world":             "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "cnbc_economy":           "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "npr_world":              "https://feeds.npr.org/1004/rss.xml",
        "pbs_newshour":           "https://www.pbs.org/newshour/feeds/rss/world",
    }

    # ── EUROPA ────────────────────────────────────────────────────────────────
    EUROPA = {
        "euronews_esp":           "https://es.euronews.com/rss?format=mrss&level=theme&name=news",
        "euronews_world":         "https://www.euronews.com/rss?format=mrss&level=theme&name=news",
        "bbc_europe":             "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "deutsche_welle_esp":     "https://rss.dw.com/rdf/rss-es-all",
        "deutsche_welle_eng":     "https://rss.dw.com/rdf/rss-en-all",
        "france24_esp":           "https://www.france24.com/es/rss",
        "france24_eng":           "https://www.france24.com/en/rss",
        "le_monde":               "https://www.lemonde.fr/rss/une.xml",
        "le_monde_economie":      "https://www.lemonde.fr/economie/rss_full.xml",
        "le_figaro":              "https://www.lefigaro.fr/rss/figaro_actualites.xml",
        "el_pais_esp":            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "el_pais_economia":       "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada",
        "el_mundo_esp":           "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
        "la_vanguardia":          "https://www.lavanguardia.com/mvc/feed/rss/home",
        "expansion_esp":          "https://www.expansion.com/rss/mercados.xml",
        "spiegel_intl":           "https://www.spiegel.de/international/index.rss",
        "suddeutsche_zeitung":    "https://rss.sueddeutsche.de/rss/TopThemen",
        "ansa_italia":            "https://www.ansa.it/sito/ansait_rss.xml",
        "corriere_della_sera":    "https://xml2.corrieredellasera.it/rss/homepage.xml",
        "swissinfo":              "https://www.swissinfo.ch/eng/rss/all",
        "rtve_esp":               "https://www.rtve.es/noticias/rss/",
        "arte_tv":                "https://www.arte.tv/en/rss/videos/all/",
        "euractiv":               "https://www.euractiv.com/feed/",
        "politico_eu":            "https://www.politico.eu/feed/",
    }

    # ── RUSIA / EURASIA ───────────────────────────────────────────────────────
    RUSIA_EURASIA = {
        "rt_espanol":             "https://actualidad.rt.com/rss",
        "rt_english":             "https://www.rt.com/rss/",
        "tass_english":           "https://tass.com/rss/v2.xml",
        "tass_world":             "https://tass.com/world?format=rss",
        "ria_novosti":            "https://ria.ru/export/rss2/world/index.xml",
        "sputnik_esp":            "https://sputniknews.lat/export/rss2/archive/index.xml",
        "sputnik_eng":            "https://sputnikglobe.com/export/rss2/world/index.xml",
        "rossiyskaya_gazeta_eng": "https://rg.ru/information/rss.html",
        "moscow_times":           "https://www.themoscowtimes.com/rss/news",
        "kyiv_independent":       "https://kyivindependent.com/feed/",
        "ukraine_pravda":         "https://www.pravda.com.ua/eng/rss/view_news/",
        "meduza":                 "https://meduza.io/rss/all",
    }

    # ── ASIA / PACÍFICO ───────────────────────────────────────────────────────
    ASIA_PACIFICO = {
        "scmp_hk":                "https://www.scmp.com/rss/91/feed",
        "scmp_china":             "https://www.scmp.com/rss/2/feed",
        "scmp_economy":           "https://www.scmp.com/rss/92/feed",
        "xinhua_english":         "http://www.xinhuanet.com/english/rss/worldrss.xml",
        "global_times":           "https://www.globaltimes.cn/rss/outbrain.xml",
        "peoples_daily_online":   "http://en.people.cn/rss/90001.xml",
        "caixin_global":          "https://www.caixinglobal.com/rss",
        "nikkei_asia":            "https://asia.nikkei.com/rss/feed/nar",
        "japan_times":            "https://www.japantimes.co.jp/feed/",
        "the_hindu":              "https://www.thehindu.com/feeder/default.rss",
        "hindustan_times":        "https://www.hindustantimes.com/feeds/rss/world/rssfeed.xml",
        "economic_times_india":   "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "straits_times_sg":       "https://www.straitstimes.com/news/asia/rss.xml",
        "channel_news_asia":      "https://www.channelnewsasia.com/rssfeeds/8395986",
        "korea_herald":           "https://www.koreaherald.com/rss/020100000000.xml",
        "yonhap_korea":           "https://en.yna.co.kr/RSS/news.xml",
        "sydney_morning_herald":  "https://www.smh.com.au/rss/feed.xml",
    }

    # ── MEDIO ORIENTE / AFRICA ────────────────────────────────────────────────
    MEDIO_ORIENTE_AFRICA = {
        "al_jazeera_eng":         "https://www.aljazeera.com/xml/rss/all.xml",
        "al_jazeera_esp":         "https://www.aljazeera.com/xml/rss/all-es.xml",
        "al_monitor":             "https://www.al-monitor.com/pulse/rss.xml",
        "middle_east_eye":        "https://www.middleeasteye.net/rss",
        "haaretz":                "https://www.haaretz.com/cmlink/1.628765",
        "jerusalem_post":         "https://www.jpost.com/rss/rssfeedsfrontpage.aspx",
        "arab_news":              "https://www.arabnews.com/rss.xml",
        "daily_sabah":            "https://www.dailysabah.com/rss",
        "iran_international":     "https://www.iranintl.com/en/rss",
        "al_arabiya":             "https://www.alarabiya.net/tools/rss",
        "africa_report":          "https://www.theafricareport.com/feed/",
        "allaf_africa":           "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
    }

    # ── MERCADOS / ECONOMÍA GLOBAL ────────────────────────────────────────────
    MERCADOS_GLOBALES = {
        "marketwatch":            "https://www.marketwatch.com/rss/topstories",
        "marketwatch_markets":    "https://www.marketwatch.com/rss/marketpulse",
        "investing_com":          "https://www.investing.com/rss/news.rss",
        "seeking_alpha":          "https://seekingalpha.com/market_currents.xml",
        "zero_hedge":             "https://feeds.feedburner.com/zerohedge/feed",
        "kitco_metals":           "https://www.kitco.com/rss/metals.rss",
        "kitco_gold":             "https://www.kitco.com/rss/gold.rss",
        "mining_com":             "https://www.mining.com/feed/",
        "oil_price":              "https://oilprice.com/rss/main",
        "rigzone":                "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
        "eia_petroleum":          "https://www.eia.gov/rss/news.xml",
        "imf_blog":               "https://www.imf.org/en/News/rss?language=eng",
        "world_bank_blog":        "https://blogs.worldbank.org/rss.xml",
        "bis_working_papers":     "https://www.bis.org/rss/press_all.rss",
        "federal_reserve_speech": "https://www.federalreserve.gov/feeds/speeches.xml",
        "federal_reserve_news":   "https://www.federalreserve.gov/feeds/press_all.xml",
        "ecb_news":               "https://www.ecb.europa.eu/rss/press.html",
        "wto_news":               "https://www.wto.org/english/news_e/rss_e.xml",
        "oecd_news":              "https://www.oecd.org/newsroom/rss/",
        "cepal":                  "https://repositorio.cepal.org/feed/rss_2.0",
        "silver_institute":       "https://www.silverinstitute.org/feed/",
        "world_silver_survey":    "https://www.silverinstitute.org/feed/",
        "zinc_industry":          "https://www.ilzsg.org/static/rss.aspx",
    }

    # ── GEOPOLÍTICA / THINK TANKS ─────────────────────────────────────────────
    THINK_TANKS = {
        "foreign_affairs":        "https://www.foreignaffairs.com/rss.xml",
        "foreign_policy":         "https://foreignpolicy.com/feed/",
        "cfr_org":                "https://www.cfr.org/rss.xml",
        "brookings":              "https://www.brookings.edu/feed/",
        "rand_corp":              "https://www.rand.org/pubs/all.xml",
        "heritage_foundation":    "https://www.heritage.org/rss/everything",
        "cato_institute":         "https://www.cato.org/feed.rss",
        "wilson_center":          "https://www.wilsoncenter.org/feed.xml",
        "sipri":                  "https://www.sipri.org/news/rss",
        "icg":                    "https://www.crisisgroup.org/rss.xml",
        "stimson_center":         "https://www.stimson.org/feed/",
        "carnegie":               "https://carnegieendowment.org/rss/",
        "belfer_center":          "https://www.belfercenter.org/feed",
        "orden_mundial":          "https://elordenmundial.com/feed/",
        "geopolitica_unir":       "https://www.unir.net/revista/feed/",
        "geopolitica_info":       "https://www.geopolitica.info/feed/",
        "poder_360":              "https://www.poder360.com.br/feed/",
        "the_diplomat":           "https://thediplomat.com/feed/",
        "war_on_rocks":           "https://warontherocks.com/feed/",
        "lawfare":                "https://www.lawfaremedia.org/feed",
        "defense_one":            "https://www.defenseone.com/rss/all/",
        "breaking_defense":       "https://breakingdefense.com/feed/",
        "jane_defense":           "https://www.janes.com/feeds/news",
        "real_clear_defense":     "https://www.realcleardefense.com/index.xml",
        "real_clear_world":       "https://www.realclearworld.com/index.xml",
    }

    # ── SEGURIDAD / CRIMEN ORGANIZADO MX ─────────────────────────────────────
    SEGURIDAD_MX = {
        "insight_crime":          "https://insightcrime.org/feed/",
        "mexico_seguro":          "https://www.gob.mx/sspc/es/archivo/rss",
        "iter_crimen":            "https://www.icrimewatch.org/rss",
        "zero_impunidad":         "https://zeroimp.org/feed/",
        "causa_en_comun":         "https://causaencomun.org.mx/beta/feed/",
        "animal_politico_seg":    "https://animalpolitico.com/seguridad/feed",
        "parametria":             "https://www.parametria.com.mx/feed/",
    }

    # ── COMPILADO TOTAL ───────────────────────────────────────────────────────
    @classmethod
    def todos(cls) -> dict:
        merged = {}
        for attr in [
            "LOCALES_ZAC", "INSTITUCIONALES_ZAC", "NACIONALES_MX",
            "INSTITUCIONALES_MX", "LATAM", "USA_UK", "EUROPA",
            "RUSIA_EURASIA", "ASIA_PACIFICO", "MEDIO_ORIENTE_AFRICA",
            "MERCADOS_GLOBALES", "THINK_TANKS", "SEGURIDAD_MX"
        ]:
            merged.update(getattr(cls, attr, {}))
        return merged

    @classmethod
    def por_region(cls, region: str) -> dict:
        MAPA = {
            "local":        cls.LOCALES_ZAC,
            "institucional":dict(**cls.INSTITUCIONALES_ZAC, **cls.INSTITUCIONALES_MX),
            "nacional":     cls.NACIONALES_MX,
            "latam":        cls.LATAM,
            "eeuu":         cls.USA_UK,
            "europa":       cls.EUROPA,
            "rusia":        cls.RUSIA_EURASIA,
            "asia":         cls.ASIA_PACIFICO,
            "mo_africa":    cls.MEDIO_ORIENTE_AFRICA,
            "mercados":     cls.MERCADOS_GLOBALES,
            "think_tanks":  cls.THINK_TANKS,
            "seguridad":    cls.SEGURIDAD_MX,
        }
        return MAPA.get(region, {})

    @classmethod
    def contar(cls) -> dict:
        total = 0
        conteos = {}
        for attr in ["LOCALES_ZAC","INSTITUCIONALES_ZAC","NACIONALES_MX",
                     "INSTITUCIONALES_MX","LATAM","USA_UK","EUROPA",
                     "RUSIA_EURASIA","ASIA_PACIFICO","MEDIO_ORIENTE_AFRICA",
                     "MERCADOS_GLOBALES","THINK_TANKS","SEGURIDAD_MX"]:
            n = len(getattr(cls, attr, {}))
            conteos[attr] = n
            total += n
        conteos["TOTAL"] = total
        return conteos

# =============================================================================
#  MÓDULO 2: PALABRAS CLAVE GLOBALES (KEYWORDS)
# =============================================================================

KEYWORDS_GLOBALES = {
    # ── LÍDERES MUNDIALES ────────────────────────────────────────────────────
    "trump":        ["Trump", "Donald Trump", "MAGA", "Make America Great Again",
                     "Casa Blanca", "White House", "administración Trump",
                     "tariff", "deportation", "America First"],
    "putin":        ["Putin", "Vladimir Putin", "Kremlin", "Moscú",
                     "Rusia lanza", "Rusia invade", "Rusia amenaza",
                     "OTAN vs Rusia", "NATO Russia"],
    "netanyahu":    ["Netanyahu", "Bibi", "Israel ataca", "Gaza ofensiva",
                     "IDF", "Hamas", "Hezbollah", "Irán Israel",
                     "Franja de Gaza", "Cisjordania"],
    "xi_jinping":   ["Xi Jinping", "Xi Jinpíng", "PCCh", "China lanza",
                     "Partido Comunista China", "Taiwán China", "PLA",
                     "China military", "BRICS China"],
    "zelensky":     ["Zelensky", "Zelenski", "Ucrania contraofensiva",
                     "Kyiv", "Kiev", "Ucrania recibe armas"],
    "sheinbaum":    ["Claudia Sheinbaum", "Sheinbaum", "presidenta México",
                     "gobierno federal México", "4T", "Palacio Nacional",
                     "Plan C", "Morena federal"],
    "lopez_obrador":["AMLO", "López Obrador", "legado AMLO", "políticas AMLO"],
    "milei":        ["Milei", "Javier Milei", "Argentina dolarización",
                     "motosierra Argentina", "recorte presupuesto Argentina"],
    "erdogan":      ["Erdogan", "Erdoğan", "Turquía", "OTAN Turquía"],
    "modi":         ["Modi", "Narendra Modi", "India BJP", "India China"],

    # ── EVENTOS MILITARES / CONFLICTOS ────────────────────────────────────────
    "guerra_ucrania":  ["Ucrania", "Ukraine", "frente Ucrania", "Bakhmut",
                        "Járkov", "Odessa", "ofensiva ucraniana",
                        "Zaporizhzhia", "ATACMS", "F-16 Ucrania"],
    "guerra_gaza":     ["Gaza", "Rafah", "Cisjordania", "Hamas ataca",
                        "IDF bombardeo", "tregua Gaza", "rehenes Israel",
                        "corredor humanitario Gaza"],
    "taiwan_estrecho": ["Taiwán", "Taiwan", "PLA Taiwan", "TSMC",
                        "independencia Taiwán", "China Taiwán", "semiconductores"],
    "iran_nucl":       ["Irán nuclear", "JCPOA", "enriquecimiento uranio",
                        "Natanz", "sanciones Irán", "Irán drones"],
    "misiles":         ["misil", "missile", "lanzamiento misil", "ICBM",
                        "hipersónico", "crucero", "Kinzhal", "Storm Shadow",
                        "Patriot", "THAAD", "Iron Dome", "David's Sling"],
    "drones":          ["drones", "UAV", "Shaheed", "Shahed", "ataque drone",
                        "enjambre drones", "kamikaze drone", "FPV drone"],
    "sanciones_glob":  ["sanciones", "sanción", "OFAC", "SWIFT excluido",
                        "embargo", "lista negra", "restricciones comerciales"],
    "armas_nucleares": ["nuclear", "cabeza nuclear", "OTAN nuclear",
                        "artículo 5", "disuasión nuclear", "bomba sucia"],

    # ── ENERGÍA Y RECURSOS ────────────────────────────────────────────────────
    "petroleo":        ["petróleo", "WTI", "Brent", "crudo", "barril",
                        "OPEP", "OPEC", "Arabia Saudita producción",
                        "recorte producción", "Pemex", "offshore"],
    "gas_natural":     ["gas natural", "LNG", "GNL", "gasoducto",
                        "Nord Stream", "gas Europa", "GNL México"],
    "litio":           ["litio", "lithium", "batería litio", "vehículo eléctrico",
                        "Bolivia litio", "Chile litio", "México litio",
                        "transición energética"],
    "plata_zinc":      ["plata", "silver", "zinc", "mineral estratégico",
                        "Fresnillo", "minería Zacatecas", "precio plata",
                        "silver futures", "producción plata México"],
    "cobre":           ["cobre", "copper", "cobre Chile", "Freeport",
                        "Codelco", "precio cobre"],
    "oro":             ["oro", "gold", "precio oro", "XAU", "reservas oro",
                        "banco central oro", "hedge inflación"],

    # ── COMERCIO / ECONOMÍA ───────────────────────────────────────────────────
    "aranceles":       ["arancel", "tariff", "arancel Trump", "arancel China",
                        "arancel acero", "reciprocal tariff", "guerra comercial"],
    "tmec":            ["TMEC", "T-MEC", "USMCA", "renegociación TMEC",
                        "revisión TMEC", "panel TMEC", "automóvil TMEC"],
    "nearshoring":     ["nearshoring", "relocalización", "friendshoring",
                        "supply chain Mexico", "manufactura México",
                        "inversión extranjera directa"],
    "inflacion":       ["inflación", "IPC", "CPI", "hiperinflación",
                        "deflación", "estanflación", "tasa inflación"],
    "fed_banxico":     ["Fed", "Federal Reserve", "tasa Fed",
                        "Banxico", "tasa referencia", "política monetaria",
                        "Jerome Powell", "Victoria Rodríguez Ceja"],
    "dolar_peso":      ["tipo de cambio", "dólar", "peso mexicano",
                        "devaluación", "fortaleza peso", "carry trade"],
    "remesas":         ["remesas", "envío dinero", "transferencias familiares",
                        "remesas México", "remesas Zacatecas", "Western Union"],
    "deuda":           ["deuda pública", "deuda soberana", "default",
                        "Moody's", "S&P rating", "Fitch rating",
                        "bonos gobierno", "spread"],

    # ── CADENAS DE SUMINISTRO ─────────────────────────────────────────────────
    "cadena_suministro":["supply chain", "cadena de suministro", "desabasto",
                         "escasez", "inventario", "logística",
                         "semiconductores escasez", "flete marítimo"],
    "semiconductores": ["semiconductor", "chip", "TSMC", "Intel", "NVIDIA",
                        "ARM", "ley CHIPS", "CHIPS Act", "exportación chips China"],

    # ── CRIMEN / SEGURIDAD MX ─────────────────────────────────────────────────
    "crimen_mx":       ["cártel", "cartel", "CJNG", "Sinaloa", "operativo",
                        "decomiso", "narco", "balacera", "extorsión",
                        "secuestro", "desaparición", "feminicidio"],
    "seguridad_zac":   ["inseguridad Zacatecas", "violencia Fresnillo",
                        "homicidio Zacatecas", "crimen organizado Zacatecas",
                        "operativo Zacatecas", "Guardia Nacional Zacatecas"],

    # ── IA / TECNOLOGÍA ───────────────────────────────────────────────────────
    "ia_tech":         ["inteligencia artificial", "AI", "ChatGPT", "Gemini",
                        "regulación IA", "automatización", "Silicon Valley",
                        "Big Tech", "NVIDIA mercado"],

    # ── CLIMA / AGUA ─────────────────────────────────────────────────────────
    "clima_agua":      ["cambio climático", "sequía", "inundación", "huracán",
                        "COP30", "escasez agua", "presa Zacatecas",
                        "agua Guadalupe Zacatecas"],
}

# =============================================================================
#  MÓDULO 3: ACTIVOS FINANCIEROS (Yahoo Finance / yfinance)
# =============================================================================

ACTIVOS_FINANCIEROS = {
    # Índices bursátiles
    "SP500":      {"ticker": "^GSPC",  "nombre": "S&P 500",         "tipo": "indice"},
    "DOW":        {"ticker": "^DJI",   "nombre": "Dow Jones",       "tipo": "indice"},
    "NASDAQ":     {"ticker": "^IXIC",  "nombre": "NASDAQ",          "tipo": "indice"},
    "IPC_BMV":    {"ticker": "^MXX",   "nombre": "IPC México (BMV)","tipo": "indice"},
    "BOVESPA":    {"ticker": "^BVSP",  "nombre": "Bovespa Brasil",  "tipo": "indice"},
    "FTSE100":    {"ticker": "^FTSE",  "nombre": "FTSE 100 UK",     "tipo": "indice"},
    "DAX":        {"ticker": "^GDAXI", "nombre": "DAX Alemania",    "tipo": "indice"},
    "NIKKEI":     {"ticker": "^N225",  "nombre": "Nikkei 225",      "tipo": "indice"},
    "HANG_SENG":  {"ticker": "^HSI",   "nombre": "Hang Seng HK",    "tipo": "indice"},
    # Divisas
    "USD_MXN":    {"ticker": "USDMXN=X","nombre": "Dólar/Peso MX", "tipo": "divisa"},
    "EUR_USD":    {"ticker": "EURUSD=X","nombre": "Euro/Dólar",     "tipo": "divisa"},
    "USD_CNY":    {"ticker": "USDCNY=X","nombre": "Dólar/Yuan",     "tipo": "divisa"},
    "USD_RUB":    {"ticker": "USDRUB=X","nombre": "Dólar/Rublo",    "tipo": "divisa"},
    "USD_JPY":    {"ticker": "USDJPY=X","nombre": "Dólar/Yen",      "tipo": "divisa"},
    # Materias primas
    "WTI":        {"ticker": "CL=F",   "nombre": "Petróleo WTI",    "tipo": "commodity"},
    "BRENT":      {"ticker": "BZ=F",   "nombre": "Petróleo Brent",  "tipo": "commodity"},
    "GOLD":       {"ticker": "GC=F",   "nombre": "Oro (XAU)",       "tipo": "metal"},
    "SILVER":     {"ticker": "SI=F",   "nombre": "Plata (XAG)",     "tipo": "metal"},
    "COPPER":     {"ticker": "HG=F",   "nombre": "Cobre",           "tipo": "metal"},
    "ZINC_ETF":   {"ticker": "ZINC",   "nombre": "Zinc ETF",        "tipo": "metal"},
    "NATURAL_GAS":{"ticker": "NG=F",   "nombre": "Gas Natural",     "tipo": "commodity"},
    "CORN":       {"ticker": "ZC=F",   "nombre": "Maíz",            "tipo": "agro"},
    "WHEAT":      {"ticker": "ZW=F",   "nombre": "Trigo",           "tipo": "agro"},
    # Cripto
    "BTC":        {"ticker": "BTC-USD","nombre": "Bitcoin",         "tipo": "cripto"},
    # Acciones estratégicas
    "NVIDIA":     {"ticker": "NVDA",   "nombre": "NVIDIA",          "tipo": "accion"},
    "TSMC":       {"ticker": "TSM",    "nombre": "TSMC",            "tipo": "accion"},
    "FRESNILLO":  {"ticker": "FRES.L", "nombre": "Fresnillo PLC",   "tipo": "accion"},
    "PEMEX_BOND": {"ticker": "PEMEX",  "nombre": "Pemex (ADR ref)","tipo": "bono"},
}

# =============================================================================
#  MÓDULO 4: MATRIZ DE CORRELACIONES GEOPOLÍTICAS
#  Basada en: Brzezinski, Mearsheimer, Friedman (G.), Kissinger, Zeihan, Dalio
# =============================================================================

class MatrizCorrelaciones:
    """
    Motor de correlaciones geopolíticas → impacto en Zacatecas.

    Fundamentos teóricos:
    - Brzezinski (El Gran Tablero): pivotes geográficos y jugadores activos
    - Mearsheimer (La Tragedia de la Política de las Grandes Potencias): ofensiva realismo
    - George Friedman (Stratfor): geopolítica predictiva basada en geografía
    - Kissinger (Orden Mundial): equilibrio de poder y diplomacia
    - Peter Zeihan (Accidentes de la Historia): demografía, logística y reshoring
    - Ray Dalio (Principios para el Orden Mundial): ciclos de deuda y hegemonía
    """

    # ── MATRIZ GLOBAL ─────────────────────────────────────────────────────────
    # Formato: señal_global → {sector_zac: coeficiente -1..1, fuente_teorica}
    MATRIZ = {
        # ── BRZEZINSKI: Tablero geopolítico ──────────────────────────────────
        "inestabilidad_eurasia": {
            "precio_plata_zac":       +0.70,  # Safe haven → sube plata
            "costo_energia_industria":+0.55,  # Petróleo sube
            "flujo_remesas":         -0.30,  # Diáspora en riesgo
            "inversion_extranjera":  -0.40,  # Risk-off
            "teoria": "Brzezinski: inestabilidad en 'tablero' central eleva primas de riesgo",
        },
        "hegemonía_eeuu_declive": {
            "nearshoring_oportunidad":+0.80,  # Zeihan: reshoring a MX
            "tmec_fortaleza":         +0.65,
            "vulnerabilidad_dolares_remesas": -0.50,  # Dalio: hegemonía ↓ = dólar ↓
            "teoria": "Zeihan/Dalio: relocalización industrial favorece México",
        },
        # ── MEARSHEIMER: Ofensiva realismo ───────────────────────────────────
        "ascenso_china": {
            "competencia_manufactura_zac": -0.60,
            "precio_metales_industriales": +0.50,  # China demanda minerales
            "nearshoring_zac":            +0.70,  # Relocalización fuera de China
            "semiconductores_zac":        +0.45,
            "teoria": "Mearsheimer: competencia EEUU-China impulsa relocalización hacia MX",
        },
        "confrontacion_eeuu_china": {
            "aranceles_impacto_exportaciones": -0.55,
            "nearshoring_zac":                +0.85,
            "precio_plata":                   +0.60,  # Safe haven
            "volatilidad_mercados":           +0.75,
            "teoria": "Friedman/Mearsheimer: tensión bifurcación cadenas → nearshoring MX",
        },
        # ── KISSINGER: Equilibrio de poder ───────────────────────────────────
        "multipolitud_emergente": {
            "diversificacion_mercados_export": +0.50,
            "dependencia_eeuu":               -0.40,
            "vulnerabilidad_tmec":            -0.30,
            "teoria": "Kissinger: multipolaridad obliga a México a diversificar alianzas",
        },
        "acuerdos_paz_oriente_medio": {
            "precio_petroleo":      -0.45,  # Baja al reducir tensión
            "costo_energia_mx":     -0.40,
            "inflacion_zac":        -0.35,
            "teoria": "Kissinger: estabilidad OM reduce presión energética global",
        },
        # ── ZEIHAN: Demografía y logística ───────────────────────────────────
        "crisis_demografica_china": {
            "nearshoring_zac":           +0.90,  # Zeihan: China pierde demografía productiva
            "manufactura_zac":           +0.70,
            "inversion_automotriz_zac":  +0.65,
            "teoria": "Zeihan: colapso demográfico chino → reconfiguración supply chain → MX gana",
        },
        "fractura_globalizacion": {
            "nearshoring_zac":           +0.85,
            "exportaciones_agro_zac":    +0.40,
            "vulnerabilidad_importaciones": -0.60,
            "teoria": "Zeihan: desglobalización crea bloques regionales; MX beneficia",
        },
        # ── DALIO: Ciclos de deuda ────────────────────────────────────────────
        "ciclo_deuda_eeuu_techo": {
            "tipo_cambio_peso_dolar":    -0.70,  # Dalio: dólar se debilita
            "precio_oro":               +0.80,
            "precio_plata":             +0.75,
            "remesas_valor_real":       -0.50,
            "teoria": "Dalio: ciclo deuda largo → depreciación USD → metales suben, remesas pierden poder",
        },
        "inflacion_global_alta": {
            "poder_adquisitivo_zac":     -0.85,
            "precio_materias_primas":    +0.70,
            "precio_plata":              +0.55,
            "salarios_reales_zac":       -0.60,
            "teoria": "Dalio: inflación crónica destruye clase media; beneficia activos reales",
        },
        # ── SEÑALES DIRECTAS ZAC ─────────────────────────────────────────────
        "conflicto_bélico_activo": {
            "precio_plata_zac":          +0.72,  # Plata = industrial + safe haven
            "precio_zinc_zac":           +0.65,
            "costo_energia_industrial":  +0.80,
            "inversion_minera_zac":      -0.40,  # Incertidumbre
            "turismo_zac":               -0.50,
            "teoria": "Correlación empírica: guerras activas → commodity rally",
        },
        "sanciones_rusia_europa": {
            "gas_natural_precio":        +0.85,
            "fertilizantes_precio":      +0.70,  # Rusia = exportador potasa/amoniaco
            "costo_agro_zac":            +0.55,
            "exportaciones_plata":       +0.40,  # Europa busca alternativas
            "teoria": "Sanciones Rusia → shock energético Europa → presión global commodities",
        },
        "guerra_comercial_eeuu": {
            "exportaciones_acero_plata":  -0.65,
            "nearshoring_positivo":       +0.75,
            "costo_insumos_importados":   +0.60,
            "tipo_cambio_volatilidad":    +0.70,
            "teoria": "Aranceles Trump: doble efecto sobre México (daño directo + desvío comercio)",
        },
    }

    # ── CICLOS HISTÓRICOS (Dalio) ─────────────────────────────────────────────
    CICLOS_DALIO = {
        "ciclo_deuda_corto":  {"duracion_anios": 7,   "fase_actual": "contraccion"},
        "ciclo_deuda_largo":  {"duracion_anios": 75,  "fase_actual": "transicion"},
        "ciclo_hegemonico":   {"duracion_anios": 250, "fase_actual": "declive_eeuu_ascenso_china"},
    }

    # ── PIVOTES GEOGRÁFICOS (Brzezinski) ──────────────────────────────────────
    PIVOTES_GEOGRAFICOS = {
        "ucrania":   {"relevancia_zac": 0.45, "razon": "conflicto → commodities → plata/zinc"},
        "taiwan":    {"relevancia_zac": 0.65, "razon": "semiconductores → nearshoring → MX"},
        "iran":      {"relevancia_zac": 0.40, "razon": "petróleo → energía → costos MX"},
        "turquia":   {"relevancia_zac": 0.25, "razon": "Bósforo → comercio global"},
        "arabia_saudita": {"relevancia_zac": 0.50, "razon": "OPEC → petróleo → energía MX"},
        "panama":    {"relevancia_zac": 0.55, "razon": "canal → logística MX exportaciones"},
        "mexico":    {"relevancia_zac": 1.00, "razon": "actor doméstico directo"},
    }

    def calcular_impacto_compuesto(self, señales_activas: dict) -> dict:
        """
        Calcula el impacto ponderado en sectores de Zacatecas.

        señales_activas: {nombre_señal: intensidad_0_1}
        Retorna: {sector: impacto_ponderado}
        """
        impactos = defaultdict(float)
        contribuciones = defaultdict(list)

        for señal, intensidad in señales_activas.items():
            if señal in self.MATRIZ:
                for sector, coef in self.MATRIZ[señal].items():
                    if sector == "teoria":
                        continue
                    impactos[sector]        += coef * intensidad
                    contribuciones[sector].append({
                        "señal": señal, "coef": coef,
                        "intensidad": intensidad,
                        "contribucion": round(coef * intensidad, 3)
                    })

        # Normalizar a -1..1
        resultado = {}
        for sector, val in impactos.items():
            resultado[sector] = {
                "impacto":        round(max(-1.0, min(1.0, val)), 3),
                "contribuciones": contribuciones[sector],
                "nivel": "critico" if abs(val) > 0.7 else "alto" if abs(val) > 0.4 else "moderado",
            }
        return dict(sorted(resultado.items(), key=lambda x: -abs(x[1]["impacto"])))

    def reporte_teorico(self, señal: str) -> str:
        if señal in self.MATRIZ:
            return self.MATRIZ[señal].get("teoria", "Sin marco teórico asignado")
        return "Señal no registrada en matriz"


# =============================================================================
#  MÓDULO 5: DATACLASSES
# =============================================================================

@dataclass
class Noticia:
    id:                   str   = ""
    titulo:               str   = ""
    resumen:              str   = ""
    url:                  str   = ""
    fuente:               str   = ""
    region_fuente:        str   = ""     # local|nacional|latam|eeuu|europa|rusia|asia|mo|mercados
    fecha:                str   = ""
    fecha_scraped:        str   = ""
    categoria:            str   = "no_clasificada"
    subcategoria:         str   = ""
    relevancia_zac:       float = 0.0
    menciones_candidatos: dict  = field(default_factory=dict)
    señales_geopoliticas: dict  = field(default_factory=dict)
    señales_electorales:  dict  = field(default_factory=dict)
    keywords_detectados:  list  = field(default_factory=list)
    personajes_detectados:list  = field(default_factory=list)
    partidos_detectados:  list  = field(default_factory=list)
    sentiment_score:      float = 0.0
    raw_text:             str   = ""
    idioma:               str   = "es"

@dataclass
class DatoMercado:
    ticker:      str   = ""
    nombre:      str   = ""
    tipo:        str   = ""
    precio:      float = 0.0
    cambio_pct:  float = 0.0
    cambio_abs:  float = 0.0
    volumen:     int   = 0
    alto_dia:    float = 0.0
    bajo_dia:    float = 0.0
    timestamp:   str   = ""
    moneda:      str   = "USD"

@dataclass
class PerfilCandidato:
    id:                  str   = ""
    nombre:              str   = ""
    partido:             str   = ""
    alianza:             str   = ""
    menciones_totales:   int   = 0
    menciones_7d:        int   = 0
    menciones_30d:       int   = 0
    sentiment_promedio:  float = 0.0
    señales_positivas:   int   = 0
    señales_negativas:   int   = 0
    eventos_escandalo:   int   = 0
    eventos_alianza:     int   = 0
    eventos_encuesta:    int   = 0
    eventos_declaracion: int   = 0
    score_momentum:      float = 0.0
    score_visibilidad:   float = 0.0
    score_compuesto:     float = 0.0
    noticias_recientes:  list  = field(default_factory=list)
    red_politica_activa: list  = field(default_factory=list)
    keywords_propios:    list  = field(default_factory=list)

@dataclass
class RadarSnapshot:
    timestamp:           str   = ""
    total_noticias:      int   = 0
    por_categoria:       dict  = field(default_factory=dict)
    por_region_fuente:   dict  = field(default_factory=dict)
    señal_guerra:        int   = 0
    señal_sanciones:     int   = 0
    señal_petroleo:      int   = 0
    señal_comercio:      int   = 0
    señal_inflacion:     int   = 0
    señal_suministro:    int   = 0
    keywords_frecuencia: dict  = field(default_factory=dict)
    personajes_frecuencia: dict= field(default_factory=dict)
    trend_morena:        int   = 0
    trend_pan:           int   = 0
    trend_pri:           int   = 0
    trend_mc:            int   = 0
    mercados:            dict  = field(default_factory=dict)
    impacto_zac:         dict  = field(default_factory=dict)
    ranking_candidatos:  list  = field(default_factory=list)
    alertas:             list  = field(default_factory=list)

# =============================================================================
#  MÓDULO 6: MINADOR RSS EXPANDIDO
# =============================================================================

class MinadorRSS:
    """Scraping de feeds RSS con retry, rate-limit y caché de hashes."""

    UA = "Mozilla/5.0 ZAC-OSINT/2.0 (+https://nicho-analyzer.github.io)"
    HEADERS = {"User-Agent": UA, "Accept-Language": "es-MX,es;q=0.9,en;q=0.7"}

    def __init__(self, timeout: int = 12, max_age_days: int = 30, delay: float = 0.4):
        self.timeout   = timeout
        self.max_age   = timedelta(days=max_age_days)
        self.delay     = delay
        self.hashes    = set()
        self.stats     = defaultdict(int)

    def _hash(self, titulo: str, url: str) -> str:
        return hashlib.md5(f"{titulo}{url}".encode("utf-8")).hexdigest()[:14]

    def _fecha(self, entry) -> str:
        for attr in ("published_parsed", "updated_parsed"):
            val = getattr(entry, attr, None)
            if val:
                try:
                    return datetime(*val[:6]).isoformat()
                except Exception:
                    pass
        return datetime.now().isoformat()

    def _reciente(self, fecha_str: str) -> bool:
        try:
            return (datetime.now() - datetime.fromisoformat(fecha_str)) <= self.max_age
        except Exception:
            return True

    def _limpiar_html(self, texto: str) -> str:
        if REQUESTS_OK:
            return BeautifulSoup(texto or "", "html.parser").get_text(" ", strip=True)[:600]
        return re.sub(r"<[^>]+>", " ", texto or "")[:600]

    def scrape_feed(self, nombre: str, url: str, region: str = "desconocida") -> list:
        if not FEEDPARSER_OK:
            return []
        noticias = []
        try:
            feed = feedparser.parse(
                url,
                request_headers=self.HEADERS,
                agent=self.UA,
            )
            for e in feed.entries[:60]:
                titulo  = getattr(e, "title",   "") or ""
                resumen = getattr(e, "summary", "") or ""
                link    = getattr(e, "link",    "") or ""
                fecha   = self._fecha(e)

                if not titulo or not self._reciente(fecha):
                    continue
                nid = self._hash(titulo, link)
                if nid in self.hashes:
                    continue
                self.hashes.add(nid)

                noticias.append(Noticia(
                    id=nid, titulo=titulo.strip(),
                    resumen=self._limpiar_html(resumen),
                    url=link, fuente=nombre, region_fuente=region,
                    fecha=fecha, fecha_scraped=datetime.now().isoformat(),
                    raw_text=f"{titulo} {resumen}".lower(),
                ))
                self.stats[nombre] += 1
        except Exception as e:
            log.warning(f"Feed {nombre}: {e}")
        return noticias

    def scrape_lote(self, feeds: dict, region: str = "general") -> list:
        todas = []
        total = len(feeds)
        for i, (nombre, url) in enumerate(feeds.items(), 1):
            log.info(f"  [{i}/{total}] {nombre}")
            noticias = self.scrape_feed(nombre, url, region)
            todas.extend(noticias)
            time.sleep(self.delay)
        return todas

    def scrape_todos(self, catalogo: CatalogoFuentes = None) -> list:
        """Scrape todas las fuentes del catálogo agrupadas por región."""
        cat = catalogo or CatalogoFuentes
        todas = []
        mapa_region = [
            (cat.LOCALES_ZAC,           "local"),
            (cat.INSTITUCIONALES_ZAC,    "institucional_zac"),
            (cat.NACIONALES_MX,          "nacional"),
            (cat.INSTITUCIONALES_MX,     "institucional_mx"),
            (cat.LATAM,                  "latam"),
            (cat.USA_UK,                 "eeuu_uk"),
            (cat.EUROPA,                 "europa"),
            (cat.RUSIA_EURASIA,          "rusia"),
            (cat.ASIA_PACIFICO,          "asia"),
            (cat.MEDIO_ORIENTE_AFRICA,   "mo_africa"),
            (cat.MERCADOS_GLOBALES,      "mercados"),
            (cat.THINK_TANKS,            "think_tanks"),
            (cat.SEGURIDAD_MX,           "seguridad"),
        ]
        for feeds_dict, region in mapa_region:
            log.info(f"Scraping región [{region}] — {len(feeds_dict)} fuentes")
            n = self.scrape_lote(feeds_dict, region)
            todas.extend(n)
            log.info(f"  → {len(n)} noticias nuevas")
        log.info(f"Total acumulado: {len(todas)} noticias únicas")
        return todas

# =============================================================================
#  MÓDULO 7: MINADOR GOOGLE NEWS
# =============================================================================

class MinadorGoogleNews:
    """
    Extrae resultados de Google News via RSS (sin API key) o NewsAPI (con API key).
    Si NEWS_API_KEY está configurada, usa NewsAPI; sino, RSS.
    """
    BASE = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

    CONSULTAS = {
        # Electoral Zacatecas
        "elecciones_zac_2027":   ("zacatecas gobernador 2027",            "es-MX", "MX", "MX:es"),
        "david_monreal_gnews":   ("David Monreal gobernador Zacatecas",   "es-MX", "MX", "MX:es"),
        "candidatos_zac_gnews":  ("candidatos gobernatura Zacatecas",     "es-MX", "MX", "MX:es"),
        "pri_pan_zac_gnews":     ("PRI PAN Zacatecas elecciones",         "es-MX", "MX", "MX:es"),
        "mc_zac_gnews":          ("Movimiento Ciudadano Zacatecas",       "es-MX", "MX", "MX:es"),
        # Geopolítica
        "trump_mexico_gnews":    ("Trump Mexico aranceles",               "es-MX", "MX", "MX:es"),
        "sheinbaum_gnews":       ("Claudia Sheinbaum gobierno",           "es-MX", "MX", "MX:es"),
        "guerra_ucrania_gnews":  ("guerra Ucrania impacto México",        "es-MX", "MX", "MX:es"),
        "nearshoring_gnews":     ("nearshoring México inversión",         "es-MX", "MX", "MX:es"),
        "plata_zacatecas_gnews": ("plata Zacatecas minería precio",       "es-MX", "MX", "MX:es"),
        "trump_tariffs_global":  ("Trump tariffs economy",               "en-US", "US", "US:en"),
        "oil_price_gnews":       ("oil price OPEC crude",                "en-US", "US", "US:en"),
        "gold_silver_gnews":     ("gold silver price market",            "en-US", "US", "US:en"),
        "geopolitica_esp_gnews": ("geopolítica elordenmundial",          "es-MX", "MX", "MX:es"),
    }

    def __init__(self, delay: float = 1.5):
        self.minador = MinadorRSS(timeout=10, delay=delay)
        self.newsapi = None
        if NEWS_API_KEY and NEWSAPI_OK:
            self.newsapi = NewsApiClient(api_key=NEWS_API_KEY)
            log.info("MinadorGoogleNews: Usando NewsAPI")
        else:
            log.info("MinadorGoogleNews: Usando RSS (sin API key)")

    def scrape_todas_consultas(self) -> list:
        noticias = []
        for nombre, (query, hl, gl, ceid) in self.CONSULTAS.items():
            if self.newsapi:
                ns = self._scrape_con_newsapi(nombre, query, hl)
            else:
                url = self.BASE.format(
                    q=quote_plus(query), hl=hl, gl=gl, ceid=ceid
                )
                ns = self.minador.scrape_feed(nombre, url, "google_news")
            noticias.extend(ns)
            log.info(f"  Google News [{nombre}]: {len(ns)} resultados")
            time.sleep(self.minador.delay)
        return noticias

    def _scrape_con_newsapi(self, nombre: str, query: str, hl: str) -> list:
        """Scrape usando NewsAPI."""
        try:
            language = 'es' if 'es' in hl else 'en'
            response = self.newsapi.get_everything(
                q=query,
                language=language,
                sort_by='relevancy',
                page_size=20
            )
            noticias = []
            for article in response.get('articles', []):
                n = Noticia(
                    titulo=article['title'],
                    resumen=article['description'] or '',
                    url=article['url'],
                    fuente=nombre,
                    fecha_publicacion=article['publishedAt'][:10] if article['publishedAt'] else None,
                    categoria="google_news"
                )
                noticias.append(n)
            return noticias
        except Exception as e:
            log.error(f"Error con NewsAPI para {nombre}: {e}")
            return []

    def busqueda_ad_hoc(self, query: str, idioma: str = "es-MX") -> list:
        """Búsqueda personalizada en Google News."""
        if self.newsapi:
            language = 'es' if 'es' in idioma else 'en'
            return self._scrape_con_newsapi(f"gnews_{query[:20]}", query, idioma)
        else:
            url = self.BASE.format(
                q=quote_plus(query),
                hl=idioma, gl="MX" if "MX" in idioma else "US",
                ceid=f"{'MX' if 'MX' in idioma else 'US'}:{idioma[:2]}"
            )
            return self.minador.scrape_feed(f"gnews_{query[:20]}", url, "google_news")

# =============================================================================
#  MÓDULO 8: MINADOR DE MERCADOS FINANCIEROS
# =============================================================================

class MinadorMercados:
    """Extrae precios de activos financieros via yfinance."""

    def __init__(self):
        self.activos = ACTIVOS_FINANCIEROS

    def obtener_precio(self, ticker_id: str) -> Optional[DatoMercado]:
        if not YFINANCE_OK:
            return None
        meta = self.activos.get(ticker_id)
        if not meta:
            return None
        try:
            t = yf.Ticker(meta["ticker"])
            hist = t.history(period="2d")
            if hist.empty:
                return None
            ultimo   = hist["Close"].iloc[-1]
            anterior = hist["Close"].iloc[-2] if len(hist) > 1 else ultimo
            cambio   = ((ultimo - anterior) / anterior * 100) if anterior else 0.0
            info     = t.info
            return DatoMercado(
                ticker=meta["ticker"],
                nombre=meta["nombre"],
                tipo=meta["tipo"],
                precio=round(float(ultimo), 4),
                cambio_pct=round(float(cambio), 3),
                cambio_abs=round(float(ultimo - anterior), 4),
                volumen=int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0,
                alto_dia=round(float(hist["High"].iloc[-1]), 4),
                bajo_dia=round(float(hist["Low"].iloc[-1]), 4),
                timestamp=datetime.now().isoformat(),
                moneda=info.get("currency", "USD"),
            )
        except Exception as e:
            log.warning(f"Mercado {ticker_id}: {e}")
            return None

    def obtener_todos(self, tipo: str = None) -> dict:
        """Obtiene todos los activos (o filtrados por tipo)."""
        resultado = {}
        activos_filtrados = {
            k: v for k, v in self.activos.items()
            if tipo is None or v["tipo"] == tipo
        }
        log.info(f"Consultando {len(activos_filtrados)} activos financieros...")
        for tid in activos_filtrados:
            dato = self.obtener_precio(tid)
            if dato:
                resultado[tid] = asdict(dato)
                log.info(f"  {dato.nombre}: {dato.precio} {dato.moneda} ({dato.cambio_pct:+.2f}%)")
            time.sleep(0.3)
        return resultado

    def snapshot_prioritario(self) -> dict:
        """Subset rápido: divisas, petróleo, plata, oro, IPC."""
        prioritarios = ["USD_MXN", "WTI", "SILVER", "GOLD", "SP500", "IPC_BMV", "COPPER"]
        resultado = {}
        for tid in prioritarios:
            d = self.obtener_precio(tid)
            if d:
                resultado[tid] = asdict(d)
        return resultado

# =============================================================================
#  MÓDULO 9: ANALIZADOR OSINT EXPANDIDO
# =============================================================================

# Candidatos Zacatecas 2027
CANDIDATOS_ZAC = {
    "david_monreal": {
        "nombre": "David Monreal Ávila", "partido": "Morena",
        "alianza": "Morena-PT-PVEM",
        "palabras_clave": ["David Monreal","Monreal Ávila","gobernador Monreal",
                           "Monreal Zacatecas","David Monreal gobernador"],
        "red_politica": ["Ricardo Monreal","Claudia Sheinbaum","Mario Delgado","PT","PVEM"],
    },
    "jose_haro": {
        "nombre": "José Haro Montes", "partido": "PAN",
        "alianza": "PAN-PRI-PRD",
        "palabras_clave": ["José Haro","Haro Montes","PAN Zacatecas","José Haro diputado"],
        "red_politica": ["Marko Cortés","PRI Zacatecas","PAN nacional"],
    },
    "claudia_anaya": {
        "nombre": "Claudia Anaya Mota", "partido": "PRI",
        "alianza": "PRI (posible Va por México)",
        "palabras_clave": ["Claudia Anaya","Anaya Mota","PRI Zacatecas","senadora Anaya"],
        "red_politica": ["Alejandro Moreno","PRI nacional","PAN alianza"],
    },
    "saul_monreal": {
        "nombre": "Saúl Monreal Ávila", "partido": "Morena",
        "alianza": "Morena (interno)",
        "palabras_clave": ["Saúl Monreal","Saul Monreal","Monreal Fresnillo"],
        "red_politica": ["David Monreal","Ricardo Monreal"],
    },
    "roberto_cabrera": {
        "nombre": "Roberto Cabrera Valencia", "partido": "MC",
        "alianza": "Movimiento Ciudadano",
        "palabras_clave": ["Roberto Cabrera","Movimiento Ciudadano Zacatecas","MC Zacatecas"],
        "red_politica": ["Dante Delgado","MC nacional"],
    },
    "jorge_miranda": {
        "nombre": "Jorge Miranda Castro", "partido": "PAN",
        "alianza": "PAN",
        "palabras_clave": ["Jorge Miranda","Miranda Castro","PAN Zacatecas"],
        "red_politica": ["Marko Cortés"],
    },
    "eva_velazquez": {
        "nombre": "Eva Velázquez Campa", "partido": "Ind",
        "alianza": "Independiente",
        "palabras_clave": ["Eva Velázquez","Velázquez Campa","candidata independiente Zacatecas"],
        "red_politica": [],
    },
}

KEYWORDS_ZACATECAS = [
    "Zacatecas","zacatecano","zacatecana","Fresnillo","Guadalupe Zac",
    "Jerez","Calera","Jalpa","Nochistlán","Tlaltenango","Sombrerete",
    "Loreto","Villanueva","Rio Grande Zac","Ojocaliente","gobernador Zacatecas",
    "gobernatura Zacatecas","elecciones Zacatecas","minería Zacatecas",
]

SEÑALES_GEOPOLITICAS_DICT = {
    "guerra":      ["guerra","conflicto armado","invasión","ataque militar","bombardeo",
                    "combate","ofensiva","frente de batalla","Ukraine","Ucrania","Gaza",
                    "Taiwán","misil","dron de combate","war","military strike"],
    "sanciones":   ["sanciones","embargo","restricciones comerciales","SWIFT","lista negra",
                    "OFAC","sanciones Rusia","sanciones Irán","sanción"],
    "petroleo_energia":["petróleo","WTI","Brent","crudo","OPEP","OPEC","gas natural","GNL",
                        "Pemex","CFE","energía","precio energía","litio","cobre","zinc","plata"],
    "comercio":    ["arancel","tariff","comercio exterior","exportaciones","importaciones",
                    "TMEC","T-MEC","USMCA","OMC","WTO","dumping","nearshoring","reshoring"],
    "inflacion_economia":["inflación","IPC","CPI","Fed","Federal Reserve","Banxico",
                          "tasa de interés","tipo de cambio","dólar","peso","devaluación",
                          "remesas","recesión","PIB","desempleo"],
    "cadena_suministro":["cadena de suministro","logística","puerto","flete","semiconductor",
                         "chip","escasez","inventario","manufactura global"],
}

SEÑALES_ELECTORALES_DICT = {
    "declaraciones":   ["declaró","afirmó","dijo","señaló","propuso","prometió","anunció"],
    "escandalo":       ["escándalo","corrupción","desvío","malversación","acusación","denuncia"],
    "encuestas":       ["encuesta","sondeo","preferencia electoral","intención de voto","tendencia"],
    "alianzas":        ["alianza","coalición","acuerdo político","respaldo","apoyo","frente"],
    "conflicto_interno":["pugna interna","fractura","división","disidencia","expulsión"],
    "campana":         ["campaña","acto de campaña","mitin","candidato","debate","precampaña"],
}

PARTIDOS_DICT = {
    "morena": ["Morena","4T","cuarta transformación"],
    "pan":    ["PAN","panista","blanquiazul","Acción Nacional"],
    "pri":    ["PRI","priista","tricolor","Revolucionario Institucional"],
    "prd":    ["PRD","perredista"],
    "mc":     ["MC","Movimiento Ciudadano","naranja","emecista"],
    "pvem":   ["PVEM","Verde","ecologista"],
    "pt":     ["PT","Trabajo","petista"],
}

POSITIVOS = {"gana","avanza","apoya","logra","éxito","positivo","crecimiento",
             "inversión","beneficio","acuerdo","alianza","victoria","mejora","desarrollo"}
NEGATIVOS = {"pierde","cae","crítica","escándalo","denuncia","derrota","conflicto",
             "crisis","violencia","corrupción","desvío","sanción","arresto","fracasa"}


class AnalizadorOSINT:
    """Clasificador multi-eje con detección de keywords globales."""

    def __init__(self):
        self.stats = defaultdict(int)

    def detectar_keywords(self, noticia: Noticia) -> tuple[list, list]:
        """Retorna (keywords_detectados, personajes_detectados)."""
        texto = noticia.raw_text
        kw_det, pers_det = [], []
        for grupo, terminos in KEYWORDS_GLOBALES.items():
            for t in terminos:
                if t.lower() in texto:
                    if grupo not in kw_det:
                        kw_det.append(grupo)
                    # Detectar personajes específicos
                    for pers in ["trump","putin","netanyahu","xi_jinping","zelensky",
                                  "sheinbaum","milei","erdogan","modi"]:
                        if pers in grupo and grupo not in pers_det:
                            pers_det.append(grupo)
                    break
        return kw_det, pers_det

    def detectar_alcance(self, noticia: Noticia) -> str:
        texto = noticia.raw_text
        if any(k.lower() in texto for k in KEYWORDS_ZACATECAS):
            return "local"
        if any(k.lower() in texto for k in ["méxico","mexico","mexicano","morena","pri","pan","mc"]):
            return "nacional"
        for ev, kws in SEÑALES_GEOPOLITICAS_DICT.items():
            if any(k.lower() in texto for k in kws):
                return "geopolitica"
        region_map = {
            "local":"local","institucional_zac":"local","nacional":"nacional",
            "institucional_mx":"nacional","latam":"internacional",
            "eeuu_uk":"internacional","europa":"internacional",
            "rusia":"internacional","asia":"internacional",
            "mo_africa":"internacional","mercados":"mercados",
            "think_tanks":"geopolitica","seguridad":"seguridad",
            "google_news":"nacional",
        }
        return region_map.get(noticia.region_fuente, "nacional")

    def detectar_señales_geo(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        return {ev: {"count": len([k for k in kws if k.lower() in texto]),
                     "matches": [k for k in kws if k.lower() in texto][:5]}
                for ev, kws in SEÑALES_GEOPOLITICAS_DICT.items()
                if any(k.lower() in texto for k in kws)}

    def detectar_señales_electorales(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        return {tipo: {"count": len([k for k in kws if k.lower() in texto]),
                       "matches": [k for k in kws if k.lower() in texto][:4]}
                for tipo, kws in SEÑALES_ELECTORALES_DICT.items()
                if any(k.lower() in texto for k in kws)}

    def detectar_candidatos(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        return {cid: {"nombre": datos["nombre"], "hits": [k for k in datos["palabras_clave"] if k.lower() in texto]}
                for cid, datos in CANDIDATOS_ZAC.items()
                if any(k.lower() in texto for k in datos["palabras_clave"])}

    def detectar_partidos(self, noticia: Noticia) -> list:
        texto = noticia.raw_text
        return list({p for p, kws in PARTIDOS_DICT.items() if any(k.lower() in texto for k in kws)})

    def relevancia_zac(self, noticia: Noticia) -> float:
        score = 0.0
        texto = noticia.raw_text
        if any(k.lower() in texto for k in KEYWORDS_ZACATECAS): score += 0.4
        if noticia.menciones_candidatos:                          score += 0.2
        if any(k in texto for k in ["plata","zinc","minería","remesas","fresnillo"]): score += 0.2
        if noticia.señales_electorales:                           score += 0.15
        if noticia.region_fuente in ("local","institucional_zac"): score += 0.05
        return round(min(score, 1.0), 3)

    def sentiment(self, noticia: Noticia) -> float:
        palabras = set(noticia.raw_text.split())
        pos = len(palabras & POSITIVOS)
        neg = len(palabras & NEGATIVOS)
        return round((pos - neg) / max(pos + neg, 1), 3)

    def analizar(self, noticia: Noticia) -> Noticia:
        noticia.categoria              = self.detectar_alcance(noticia)
        noticia.señales_geopoliticas   = self.detectar_señales_geo(noticia)
        noticia.señales_electorales    = self.detectar_señales_electorales(noticia)
        noticia.menciones_candidatos   = self.detectar_candidatos(noticia)
        noticia.partidos_detectados    = self.detectar_partidos(noticia)
        noticia.keywords_detectados, noticia.personajes_detectados = self.detectar_keywords(noticia)
        noticia.relevancia_zac         = self.relevancia_zac(noticia)
        noticia.sentiment_score        = self.sentiment(noticia)
        if noticia.señales_electorales:
            noticia.subcategoria = "electoral_" + list(noticia.señales_electorales.keys())[0]
        elif noticia.señales_geopoliticas:
            noticia.subcategoria = "geo_" + list(noticia.señales_geopoliticas.keys())[0]
        self.stats[noticia.categoria] += 1
        return noticia

    def analizar_lote(self, noticias: list) -> list:
        log.info(f"Analizando {len(noticias)} noticias...")
        r = [self.analizar(n) for n in noticias]
        log.info(f"✓ {dict(self.stats)}")
        return r

# =============================================================================
#  MÓDULO 10: PERFILES CANDIDATOS
# =============================================================================

class AnalizadorCandidatos:
    def __init__(self, noticias: list):
        self.noticias = noticias
        ahora = datetime.now()
        self.hace_7d  = ahora - timedelta(days=7)
        self.hace_30d = ahora - timedelta(days=30)

    def _fecha(self, n: Noticia) -> datetime:
        try:
            return datetime.fromisoformat(n.fecha)
        except Exception:
            return datetime.now()

    def construir_perfil(self, cid: str) -> PerfilCandidato:
        datos = CANDIDATOS_ZAC[cid]
        p = PerfilCandidato(id=cid, nombre=datos["nombre"],
                            partido=datos["partido"], alianza=datos["alianza"])
        recientes = []
        for n in self.noticias:
            if cid not in n.menciones_candidatos:
                continue
            p.menciones_totales += 1
            f = self._fecha(n)
            if f >= self.hace_7d:  p.menciones_7d += 1
            if f >= self.hace_30d: p.menciones_30d += 1
            p.sentiment_promedio += n.sentiment_score
            if n.sentiment_score > 0.1: p.señales_positivas += 1
            elif n.sentiment_score < -0.1: p.señales_negativas += 1
            for tipo in n.señales_electorales:
                if tipo == "escandalo":      p.eventos_escandalo += 1
                elif tipo == "alianzas":     p.eventos_alianza += 1
                elif tipo == "encuestas":    p.eventos_encuesta += 1
                elif tipo == "declaraciones":p.eventos_declaracion += 1
            if f >= self.hace_7d:
                recientes.append({"titulo":n.titulo,"fuente":n.fuente,"fecha":n.fecha,
                                   "sentiment":n.sentiment_score,"url":n.url})
        if p.menciones_totales > 0:
            p.sentiment_promedio = round(p.sentiment_promedio / p.menciones_totales, 3)
        p.score_visibilidad = round(min(p.menciones_totales / 20.0, 1.0), 3)
        p.score_momentum    = round(
            (p.menciones_7d * 2 + p.menciones_30d) / max(p.menciones_totales * 3, 1), 3
        )
        p.score_compuesto = round(max(0.0, min(1.0,
            p.score_visibilidad * 0.35 + p.score_momentum * 0.30 +
            min(p.eventos_alianza,5) / 5 * 0.20 +
            min(p.eventos_encuesta,5) / 5 * 0.15 -
            min(p.eventos_escandalo,5) / 5 * 0.25
        )), 3)
        p.red_politica_activa = datos.get("red_politica", [])
        p.keywords_propios    = datos.get("palabras_clave", [])
        p.noticias_recientes  = sorted(recientes, key=lambda x: x["fecha"], reverse=True)[:5]
        return p

    def construir_todos(self) -> dict:
        log.info("Construyendo perfiles de candidatos...")
        perfiles = {cid: self.construir_perfil(cid) for cid in CANDIDATOS_ZAC}
        for cid, p in perfiles.items():
            log.info(f"  {p.nombre}: menciones={p.menciones_totales} score={p.score_compuesto}")
        return perfiles

# =============================================================================
#  MÓDULO 11: HISTORIAL SQLite
# =============================================================================

class HistorialDB:
    """Base de datos SQLite local para serie temporal de señales y noticias."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS noticias (
        id TEXT PRIMARY KEY, titulo TEXT, resumen TEXT, url TEXT,
        fuente TEXT, region_fuente TEXT, fecha TEXT, fecha_scraped TEXT,
        categoria TEXT, subcategoria TEXT, relevancia_zac REAL,
        sentiment_score REAL, keywords TEXT, partidos TEXT,
        menciones_candidatos TEXT, señales_geo TEXT
    );
    CREATE TABLE IF NOT EXISTS radar_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        total_noticias INTEGER,
        señal_guerra INTEGER, señal_sanciones INTEGER,
        señal_petroleo INTEGER, señal_comercio INTEGER,
        señal_inflacion INTEGER,
        trend_morena INTEGER, trend_pan INTEGER,
        trend_pri INTEGER, trend_mc INTEGER,
        keywords_json TEXT,
        mercados_json TEXT,
        impacto_zac_json TEXT
    );
    CREATE TABLE IF NOT EXISTS mercados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, ticker TEXT, nombre TEXT,
        precio REAL, cambio_pct REAL, tipo TEXT
    );
    CREATE TABLE IF NOT EXISTS candidatos_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, candidato_id TEXT, nombre TEXT,
        menciones_7d INTEGER, menciones_30d INTEGER,
        sentiment_promedio REAL, score_compuesto REAL
    );
    CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha);
    CREATE INDEX IF NOT EXISTS idx_noticias_cat ON noticias(categoria);
    CREATE INDEX IF NOT EXISTS idx_mercados_tick ON mercados(ticker, timestamp);
    """

    def __init__(self, db_path: str = "zac_osint_historial.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()
        log.info(f"HistorialDB: {db_path}")

    def guardar_noticias(self, noticias: list) -> int:
        insertadas = 0
        for n in noticias:
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO noticias VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (n.id, n.titulo[:500], n.resumen[:800], n.url[:500],
                      n.fuente, n.region_fuente, n.fecha, n.fecha_scraped,
                      n.categoria, n.subcategoria, n.relevancia_zac, n.sentiment_score,
                      json.dumps(n.keywords_detectados, ensure_ascii=False),
                      json.dumps(n.partidos_detectados, ensure_ascii=False),
                      json.dumps(n.menciones_candidatos, ensure_ascii=False),
                      json.dumps(n.señales_geopoliticas, ensure_ascii=False)))
                insertadas += 1
            except Exception as e:
                log.debug(f"DB insert: {e}")
        self.conn.commit()
        return insertadas

    def guardar_snapshot(self, snap: RadarSnapshot):
        self.conn.execute("""
            INSERT INTO radar_snapshots
            (timestamp,total_noticias,señal_guerra,señal_sanciones,señal_petroleo,
             señal_comercio,señal_inflacion,trend_morena,trend_pan,trend_pri,trend_mc,
             keywords_json,mercados_json,impacto_zac_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (snap.timestamp, snap.total_noticias, snap.señal_guerra,
              snap.señal_sanciones, snap.señal_petroleo, snap.señal_comercio,
              snap.señal_inflacion, snap.trend_morena, snap.trend_pan,
              snap.trend_pri, snap.trend_mc,
              json.dumps(snap.keywords_frecuencia, ensure_ascii=False),
              json.dumps(snap.mercados, ensure_ascii=False),
              json.dumps(snap.impacto_zac, ensure_ascii=False)))
        self.conn.commit()

    def guardar_mercados(self, mercados: dict):
        ts = datetime.now().isoformat()
        for tid, d in mercados.items():
            self.conn.execute("""
                INSERT INTO mercados (timestamp,ticker,nombre,precio,cambio_pct,tipo)
                VALUES (?,?,?,?,?,?)
            """, (ts, d.get("ticker",""), d.get("nombre",""),
                  d.get("precio",0), d.get("cambio_pct",0), d.get("tipo","")))
        self.conn.commit()

    def guardar_candidatos(self, perfiles: dict):
        ts = datetime.now().isoformat()
        for cid, p in perfiles.items():
            self.conn.execute("""
                INSERT INTO candidatos_historico
                (timestamp,candidato_id,nombre,menciones_7d,menciones_30d,
                 sentiment_promedio,score_compuesto)
                VALUES (?,?,?,?,?,?,?)
            """, (ts, cid, p.nombre, p.menciones_7d, p.menciones_30d,
                  p.sentiment_promedio, p.score_compuesto))
        self.conn.commit()

    def consultar_noticias(self, dias: int = 7, categoria: str = None,
                            candidato: str = None, limite: int = 200) -> list:
        desde = (datetime.now() - timedelta(days=dias)).isoformat()
        q = "SELECT * FROM noticias WHERE fecha >= ?"
        params = [desde]
        if categoria:
            q += " AND categoria = ?"
            params.append(categoria)
        if candidato:
            q += " AND menciones_candidatos LIKE ?"
            params.append(f"%{candidato}%")
        q += f" ORDER BY fecha DESC LIMIT {limite}"
        cur = self.conn.execute(q, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def historial_mercados(self, ticker: str, dias: int = 30) -> list:
        desde = (datetime.now() - timedelta(days=dias)).isoformat()
        cur = self.conn.execute(
            "SELECT timestamp,precio,cambio_pct FROM mercados WHERE ticker=? AND timestamp>=? ORDER BY timestamp",
            (ticker, desde)
        )
        return [{"timestamp": r[0], "precio": r[1], "cambio_pct": r[2]} for r in cur.fetchall()]

    def historial_candidato(self, candidato_id: str, dias: int = 90) -> list:
        desde = (datetime.now() - timedelta(days=dias)).isoformat()
        cur = self.conn.execute(
            "SELECT timestamp,menciones_7d,score_compuesto,sentiment_promedio FROM candidatos_historico WHERE candidato_id=? AND timestamp>=? ORDER BY timestamp",
            (candidato_id, desde)
        )
        return [{"timestamp": r[0], "menciones_7d": r[1], "score": r[2], "sentiment": r[3]} for r in cur.fetchall()]

    def cerrar(self):
        self.conn.close()

# =============================================================================
#  MÓDULO 12: EXPORTADOR COMPLETO
# =============================================================================

class Exportador:
    """Exporta en JSON, JSONL, JSONLD, CSV y genera estadísticas."""

    def __init__(self, noticias: list, perfiles: dict,
                 mercados: dict, snap: RadarSnapshot, matriz: MatrizCorrelaciones):
        self.noticias  = noticias
        self.perfiles  = perfiles
        self.mercados  = mercados
        self.snap      = snap
        self.matriz    = matriz

    def exportar_todo(self, directorio: str = "output/") -> dict:
        Path(directorio).mkdir(parents=True, exist_ok=True)
        rutas = {}

        # 1. noticias.json
        rutas["noticias_json"] = self._escribir_json(
            [asdict(n) for n in self.noticias],
            Path(directorio) / "noticias.json"
        )

        # 2. noticias.jsonl
        ruta_jsonl = Path(directorio) / "noticias.jsonl"
        with open(ruta_jsonl, "w", encoding="utf-8") as f:
            for n in self.noticias:
                f.write(json.dumps(asdict(n), ensure_ascii=False) + "\n")
        rutas["noticias_jsonl"] = str(ruta_jsonl)

        # 3. candidatos.json
        rutas["candidatos_json"] = self._escribir_json(
            {cid: asdict(p) for cid, p in self.perfiles.items()},
            Path(directorio) / "candidatos.json"
        )

        # 4. mercados.json
        rutas["mercados_json"] = self._escribir_json(
            self.mercados, Path(directorio) / "mercados.json"
        )

        # 5. radar_snapshot.json
        rutas["radar_json"] = self._escribir_json(
            asdict(self.snap), Path(directorio) / "radar_snapshot.json"
        )

        # 6. matriz_correlaciones.json
        señales_activas = {
            "conflicto_bélico_activo":   self.snap.señal_guerra    / 100,
            "sanciones_rusia_europa":    self.snap.señal_sanciones / 100,
            "guerra_comercial_eeuu":     self.snap.señal_comercio  / 100,
            "inflacion_global_alta":     self.snap.señal_inflacion / 100,
        }
        impacto = self.matriz.calcular_impacto_compuesto(señales_activas)
        rutas["matriz_json"] = self._escribir_json(
            {"señales_activas": señales_activas, "impacto_zacatecas": impacto,
             "marcos_teoricos": {k: v.get("teoria","") for k, v in self.matriz.MATRIZ.items()},
             "pivotes_geograficos": self.matriz.PIVOTES_GEOGRAFICOS,
             "ciclos_dalio": self.matriz.CICLOS_DALIO},
            Path(directorio) / "matriz_correlaciones.json"
        )

        # 7. keywords_frecuencia.json
        kw_freq = Counter()
        for n in self.noticias:
            kw_freq.update(n.keywords_detectados)
        rutas["keywords_json"] = self._escribir_json(
            dict(kw_freq.most_common(50)),
            Path(directorio) / "keywords_frecuencia.json"
        )

        # 8. CSV para análisis estadístico
        ruta_csv = Path(directorio) / "noticias.csv"
        campos_csv = ["id","titulo","fuente","region_fuente","fecha","categoria",
                      "relevancia_zac","sentiment_score"]
        with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos_csv, extrasaction="ignore")
            w.writeheader()
            for n in self.noticias:
                w.writerow({k: getattr(n, k, "") for k in campos_csv})
        rutas["noticias_csv"] = str(ruta_csv)

        # 9. JSON-LD Schema.org para indexación SEO
        rutas["jsonld"] = self._escribir_json({
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Observatorio Electoral Zacatecas 2027 — ZAC-OSINT v2",
            "description": "Análisis OSINT de elecciones gubernatura Zacatecas 2027 y radar geopolítico global",
            "creator": {"@type": "Organization", "name": "Nicho Analyzer", "url": "https://ruskigarage-alt.github.io/nicho-analyzer"},
            "dateModified": self.snap.timestamp,
            "keywords": ["Zacatecas","elecciones 2027","gobernatura","OSINT","geopolítica","candidatos"],
            "spatialCoverage": {"@type": "Place", "name": "Zacatecas, México"},
            "temporalCoverage": "2024/2027",
            "hasPart": [
                {"@type": "Dataset", "name": "Noticias clasificadas",    "encodingFormat": "application/json"},
                {"@type": "Dataset", "name": "Perfiles candidatos",      "encodingFormat": "application/json"},
                {"@type": "Dataset", "name": "Mercados financieros",     "encodingFormat": "application/json"},
                {"@type": "Dataset", "name": "Matriz correlaciones geo", "encodingFormat": "application/json"},
            ]
        }, Path(directorio) / "dataset.jsonld")

        log.info(f"✓ Exportado a {directorio} — {len(self.noticias)} noticias, {len(self.perfiles)} candidatos")
        return rutas

    @staticmethod
    def _escribir_json(data, ruta: Path) -> str:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(ruta)

    def imprimir_reporte(self):
        s = self.snap
        print("\n" + "═"*70)
        print("  ZAC-OSINT v2.0 — REPORTE EJECUTIVO COMPLETO")
        print(f"  {s.timestamp[:19]}")
        print("═"*70)

        print(f"\n📰 NOTICIAS: {s.total_noticias}  |  Fuentes: 200+  |  Google News: activo")
        for cat, n in sorted(s.por_categoria.items(), key=lambda x: -x[1]):
            bar = "█" * min(n, 35)
            print(f"   {cat:<25} {bar} {n}")

        print(f"\n📊 FUENTES POR REGIÓN (top 10):")
        for reg, n in sorted(s.por_region_fuente.items(), key=lambda x: -x[1])[:10]:
            print(f"   {reg:<30} {n}")

        print("\n🌐 RADAR GEOPOLÍTICO (0-100):")
        señales = [("guerra",s.señal_guerra),("sanciones",s.señal_sanciones),
                   ("petroleo",s.señal_petroleo),("comercio",s.señal_comercio),
                   ("inflacion",s.señal_inflacion)]
        for sn, nv in sorted(señales, key=lambda x: -x[1]):
            bar = "█" * (nv//5)
            e = "🔴" if nv>=70 else "🟡" if nv>=40 else "🟢"
            print(f"   {e} {sn:<22} {bar} {nv}")

        print("\n🔑 KEYWORDS GLOBALES TOP 10:")
        for kw, freq in sorted(s.keywords_frecuencia.items(), key=lambda x:-x[1])[:10]:
            print(f"   {kw:<30} {freq}")

        if s.mercados:
            print("\n💹 MERCADOS (snapshot):")
            for tid, d in list(s.mercados.items())[:8]:
                signo = "↑" if d.get("cambio_pct",0)>=0 else "↓"
                print(f"   {signo} {d.get('nombre',''):<22} {d.get('precio',0):>10.3f}  ({d.get('cambio_pct',0):+.2f}%)")

        print("\n🗳️  TENDENCIAS ELECTORALES:")
        for partido, n in [("Morena",s.trend_morena),("PAN",s.trend_pan),
                           ("PRI",s.trend_pri),("MC",s.trend_mc)]:
            bar = "█" * min(n, 35)
            print(f"   {partido:<12} {bar} {n}")

        print("\n👤 RANKING CANDIDATOS (score compuesto):")
        for cid, p in sorted(self.perfiles.items(), key=lambda x:-x[1].score_compuesto):
            print(f"   {p.nombre:<30} menciones={p.menciones_totales:3d}  "
                  f"score={p.score_compuesto:.2f}  sent={p.sentiment_promedio:+.2f}")

        print("\n🔗 MATRIZ CORRELACIONES — IMPACTO ZAC (top 5):")
        señales_activas = {
            "conflicto_bélico_activo": s.señal_guerra/100,
            "guerra_comercial_eeuu":   s.señal_comercio/100,
            "inflacion_global_alta":   s.señal_inflacion/100,
        }
        impacto = self.matriz.calcular_impacto_compuesto(señales_activas)
        for sector, datos in list(impacto.items())[:5]:
            val = datos["impacto"]
            print(f"   {'↑' if val>0 else '↓'} {sector:<35} {val:+.3f} [{datos['nivel']}]")

        if s.alertas:
            print(f"\n⚠️  ALERTAS ({len(s.alertas)}):")
            for a in s.alertas:
                print(f"   {'🔴' if a.get('critico') else '🟡'} {a.get('mensaje','')}")

        print("═"*70 + "\n")

# =============================================================================
#  MÓDULO 13: PIPELINE ORQUESTADOR
# =============================================================================

def generar_snapshot(noticias: list, perfiles: dict, mercados: dict) -> RadarSnapshot:
    s = RadarSnapshot(timestamp=datetime.now().isoformat())
    s.total_noticias    = len(noticias)
    s.por_categoria     = dict(Counter(n.categoria for n in noticias))
    s.por_region_fuente = dict(Counter(n.region_fuente for n in noticias))

    kw_freq  = Counter()
    per_freq = Counter()
    for n in noticias:
        kw_freq.update(n.keywords_detectados)
        per_freq.update(n.personajes_detectados)
        s.señal_guerra    += n.señales_geopoliticas.get("guerra",{}).get("count",0)
        s.señal_sanciones += n.señales_geopoliticas.get("sanciones",{}).get("count",0)
        s.señal_petroleo  += n.señales_geopoliticas.get("petroleo_energia",{}).get("count",0)
        s.señal_comercio  += n.señales_geopoliticas.get("comercio",{}).get("count",0)
        s.señal_inflacion += n.señales_geopoliticas.get("inflacion_economia",{}).get("count",0)
        s.señal_suministro+= n.señales_geopoliticas.get("cadena_suministro",{}).get("count",0)
        for p in n.partidos_detectados:
            if p == "morena": s.trend_morena += 1
            elif p == "pan":  s.trend_pan    += 1
            elif p == "pri":  s.trend_pri    += 1
            elif p == "mc":   s.trend_mc     += 1

    s.keywords_frecuencia   = dict(kw_freq.most_common(30))
    s.personajes_frecuencia = dict(per_freq.most_common(20))
    s.mercados              = mercados
    s.ranking_candidatos    = sorted([(cid, p.score_compuesto) for cid,p in perfiles.items()],
                                      key=lambda x: -x[1])
    # Alertas
    umbrales = {"guerra":60,"sanciones":50,"petroleo_energia":55,"comercio":45,"inflacion_economia":50}
    señales_vals = {"guerra":s.señal_guerra,"sanciones":s.señal_sanciones,
                    "petroleo_energia":s.señal_petroleo,"comercio":s.señal_comercio,
                    "inflacion_economia":s.señal_inflacion}
    max_val = max(señales_vals.values(), default=1)
    for señal, umbral in umbrales.items():
        nivel = round(señales_vals.get(señal,0) / max(max_val,1) * 100)
        if nivel >= umbral:
            s.alertas.append({"señal":señal,"nivel":nivel,"critico":nivel>=75,
                               "mensaje":f"Señal '{señal}' en nivel {nivel}/100"})

    return s


def ejecutar_pipeline(config: dict = None) -> dict:
    """
    Pipeline completo v2.0.

    config:
        feeds_region    : str  — 'todos'|'local'|'nacional'|'eeuu'|'europa'… (default: 'todos')
        max_age_days    : int  — antigüedad máxima en días (default: 30)
        output_dir      : str  — directorio de salida (default: 'output/')
        incluir_gnews   : bool — incluir Google News (default: True)
        incluir_mercados: bool — incluir cotizaciones (default: True)
        guardar_historial: bool— guardar en SQLite (default: True)
        db_path         : str  — ruta base de datos (default: 'zac_osint_historial.db')
        verbose         : bool — imprimir reporte (default: True)
    """
    cfg = config or {}
    feeds_region     = cfg.get("feeds_region",     "todos")
    max_age          = cfg.get("max_age_days",      30)
    output_dir       = cfg.get("output_dir",        "output/")
    incl_gnews       = cfg.get("incluir_gnews",     True)
    incl_mercados    = cfg.get("incluir_mercados",  True)
    guardar_hist     = cfg.get("guardar_historial", True)
    db_path          = cfg.get("db_path",           "zac_osint_historial.db")
    verbose          = cfg.get("verbose",           True)

    cat = CatalogoFuentes
    log.info(f"CatalogoFuentes: {cat.contar()}")

    # 1. Selección de feeds
    if feeds_region == "todos":
        feeds = cat.todos()
    else:
        feeds = cat.por_region(feeds_region)
    log.info(f"Feeds seleccionados: {len(feeds)}")

    # 2. Minado RSS principal
    minador = MinadorRSS(max_age_days=max_age)
    noticias_raw = minador.scrape_lote(feeds, region=feeds_region)

    # 3. Google News
    if incl_gnews:
        log.info("Iniciando minado Google News...")
        gnews = MinadorGoogleNews()
        noticias_gnews = gnews.scrape_todas_consultas()
        noticias_raw.extend(noticias_gnews)
        log.info(f"Google News: +{len(noticias_gnews)} resultados")

    # 4. Análisis OSINT
    analizador = AnalizadorOSINT()
    noticias   = analizador.analizar_lote(noticias_raw)

    # 5. Perfiles candidatos
    ana_cand = AnalizadorCandidatos(noticias)
    perfiles = ana_cand.construir_todos()

    # 6. Mercados
    mercados = {}
    if incl_mercados:
        miner_m = MinadorMercados()
        mercados = miner_m.snapshot_prioritario()
        log.info(f"Mercados: {len(mercados)} activos consultados")

    # 7. Snapshot y alertas
    snap   = generar_snapshot(noticias, perfiles, mercados)
    matriz = MatrizCorrelaciones()
    señales_activas = {
        "conflicto_bélico_activo": min(snap.señal_guerra/100, 1.0),
        "sanciones_rusia_europa":  min(snap.señal_sanciones/100, 1.0),
        "guerra_comercial_eeuu":   min(snap.señal_comercio/100, 1.0),
        "inflacion_global_alta":   min(snap.señal_inflacion/100, 1.0),
        "ascenso_china":           0.7,   # señal estructural permanente
        "fractura_globalizacion":  0.6,
    }
    snap.impacto_zac = {k: v["impacto"] for k, v in
                         matriz.calcular_impacto_compuesto(señales_activas).items()}

    # 8. Historial SQLite
    if guardar_hist:
        db = HistorialDB(db_path)
        insertadas = db.guardar_noticias(noticias)
        db.guardar_snapshot(snap)
        if mercados: db.guardar_mercados(mercados)
        db.guardar_candidatos(perfiles)
        db.cerrar()
        log.info(f"Historial: {insertadas} nuevas noticias en DB")

    # 9. Exportar
    exportador = Exportador(noticias, perfiles, mercados, snap, matriz)
    rutas = exportador.exportar_todo(output_dir)

    if verbose:
        exportador.imprimir_reporte()

    return {"noticias": noticias, "perfiles": perfiles, "mercados": mercados,
            "snap": snap, "rutas": rutas}


# =============================================================================
#  CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ZAC-OSINT v2.0 — Motor OSINT Geopolítico + Electoral Zacatecas"
    )
    parser.add_argument("--run-all",          action="store_true", help="Pipeline completo")
    parser.add_argument("--solo-electoral",   action="store_true", help="Solo local+nacional+institucional")
    parser.add_argument("--solo-geopolitico", action="store_true", help="Solo internacional+think_tanks+mercados")
    parser.add_argument("--solo-mercados",    action="store_true", help="Solo cotizaciones financieras")
    parser.add_argument("--region",           metavar="REG",       help="Región específica: local|nacional|europa|rusia|asia|...")
    parser.add_argument("--sin-gnews",        action="store_true", help="Omitir Google News")
    parser.add_argument("--sin-mercados",     action="store_true", help="Omitir cotizaciones")
    parser.add_argument("--historial",        action="store_true", help="Consultar historial")
    parser.add_argument("--dias",             type=int, default=30, help="Antigüedad máxima en días")
    parser.add_argument("--exportar-json",    metavar="DIR",       help="Directorio de exportación")
    parser.add_argument("--db",               default="zac_osint_historial.db", help="Ruta SQLite")
    parser.add_argument("--daemon",           action="store_true", help="Modo daemon (requiere schedule)")
    parser.add_argument("--intervalo",        type=int, default=360, help="Intervalo daemon en minutos")
    parser.add_argument("--listar-fuentes",   action="store_true", help="Listar todas las fuentes")
    parser.add_argument("--buscar",           metavar="QUERY",     help="Búsqueda ad-hoc en Google News")
    args = parser.parse_args()

    if args.listar_fuentes:
        conteo = CatalogoFuentes.contar()
        print("\n📡 CATÁLOGO DE FUENTES ZAC-OSINT v2.0")
        print("─"*50)
        for categoria, n in conteo.items():
            if categoria != "TOTAL":
                print(f"  {categoria:<30} {n:>4} fuentes")
        print(f"  {'─'*36}")
        print(f"  {'TOTAL':<30} {conteo['TOTAL']:>4} fuentes")
        return

    if args.buscar:
        log.info(f"Búsqueda ad-hoc: '{args.buscar}'")
        gnews = MinadorGoogleNews()
        resultados = gnews.busqueda_ad_hoc(args.buscar)
        analizador = AnalizadorOSINT()
        for n in analizador.analizar_lote(resultados):
            print(f"  [{n.categoria}] {n.titulo[:100]} — {n.fuente}")
        return

    if args.historial:
        db = HistorialDB(args.db)
        noticias = db.consultar_noticias(dias=args.dias)
        print(f"\n📚 Historial últimos {args.dias} días: {len(noticias)} noticias")
        for n in noticias[:20]:
            print(f"  [{n['categoria']:<12}] [{n['fuente']:<25}] {n['titulo'][:80]}")
        db.cerrar()
        return

    # Configuración base
    cfg = {
        "max_age_days":   args.dias,
        "output_dir":     args.exportar_json or "output/",
        "db_path":        args.db,
        "incluir_gnews":  not args.sin_gnews,
        "incluir_mercados": not args.sin_mercados,
        "guardar_historial": True,
        "verbose": True,
    }

    if args.solo_mercados:
        m = MinadorMercados()
        data = m.obtener_todos()
        print("\n💹 MERCADOS FINANCIEROS")
        for tid, d in data.items():
            s = "↑" if d.get("cambio_pct",0)>=0 else "↓"
            print(f"  {s} {d.get('nombre',''):<25} {d.get('precio',0):>12.3f}  ({d.get('cambio_pct',0):+.2f}%)")
        return

    if args.solo_electoral:
        cfg["feeds_region"]      = "nacional"
        cfg["incluir_mercados"]  = False
    elif args.solo_geopolitico:
        cfg["feeds_region"]      = "todos"
        cfg["incluir_mercados"]  = True
    elif args.region:
        cfg["feeds_region"]      = args.region
    else:
        cfg["feeds_region"]      = "todos"

    if args.daemon:
        if not SCHEDULE_OK:
            log.error("pip install schedule  para usar --daemon")
            return
        log.info(f"Modo DAEMON: ejecutando cada {args.intervalo} minutos")
        def job():
            log.info(f"[DAEMON] Iniciando ciclo — {datetime.now().isoformat()}")
            ejecutar_pipeline(cfg)
        schedule.every(args.intervalo).minutes.do(job)
        job()
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        ejecutar_pipeline(cfg)


if __name__ == "__main__":
    main()
