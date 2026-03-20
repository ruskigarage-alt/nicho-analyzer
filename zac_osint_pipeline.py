#!/usr/bin/env python3
"""
=============================================================================
ZAC-OSINT v1.0 — Motor de Inteligencia Electoral y Geopolítica
Estado de Zacatecas | Elecciones Gobernatura 2027
=============================================================================
Autor     : Nicho Analyzer / Alfred
Descripción:
  Pipeline completo de minería de noticias, radar geopolítico y observatorio
  electoral para las elecciones de gobernatura 2027 en Zacatecas.

Módulos:
  1. MinadorRSS       — scraping de feeds RSS de fuentes locales/nacionales
  2. AnalizadorOSINT  — clasificación, detección de eventos, señales electorales
  3. PerfilCandidatos — scraping y scoring de candidatos
  4. RadarGeopolitico — correlaciones globales → impacto Zacatecas
  5. Exportador       — salida JSON/JSONL/JSONLD + estadísticas

Dependencias (instalar en venv):
  pip install feedparser requests beautifulsoup4 pandas numpy
  pip install python-dateutil textblob lxml

Uso:
  python3 zac_osint_pipeline.py --run-all
  python3 zac_osint_pipeline.py --solo-electoral
  python3 zac_osint_pipeline.py --solo-geopolitico
  python3 zac_osint_pipeline.py --candidatos
  python3 zac_osint_pipeline.py --exportar-json output/
=============================================================================
"""

import json
import re
import time
import logging
import hashlib
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── Dependencias opcionales (se importan con try/except) ─────────────────────
try:
    import feedparser
    FEEDPARSER_OK = True
except ImportError:
    FEEDPARSER_OK = False
    print("[AVISO] feedparser no instalado: pip install feedparser")

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False
    print("[AVISO] requests/bs4 no instalados: pip install requests beautifulsoup4")

try:
    import pandas as pd
    import numpy as np
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

# ─── CONFIGURACIÓN GLOBAL ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("ZAC-OSINT")

# ─── FUENTES RSS ─────────────────────────────────────────────────────────────

FEEDS_LOCALES = {
    "ntr_zacatecas":      "https://www.ntrzacatecas.com/feed/",
    "sol_zacatecas":      "https://www.elsoldezacatecas.com.mx/rss.xml",
    "ljz_zacatecas":      "https://ljz.mx/feed/",
    "imagen_zacatecas":   "https://imagenzacatecas.com/feed/",
    "zacatecas_en_imagen":"https://www.zacatecasenimagen.com/feed/",
    "codigo_zac":         "https://codigozacatecas.com/feed/",
}

FEEDS_NACIONALES = {
    "la_jornada":     "https://www.jornada.com.mx/rss/politica.xml",
    "expansion":      "https://expansion.mx/rss",
    "milenio":        "https://www.milenio.com/rss",
    "proceso":        "https://www.proceso.com.mx/rss/politica",
    "animal_politico":"https://animalpolitico.com/feed",
    "el_financiero":  "https://www.elfinanciero.com.mx/rss/ultima-hora.xml",
    "el_economista":  "https://www.eleconomista.com.mx/rss/rss.xml",
}

FEEDS_INTERNACIONALES = {
    "reuters_latam":   "https://feeds.reuters.com/reuters/latamNewsHeadlines",
    "bloomberg_mx":    "https://feeds.bloomberg.com/markets/news.rss",
    "al_jazeera_esp":  "https://www.aljazeera.com/xml/rss/all.xml",
    "scmp":            "https://www.scmp.com/rss/91/feed",
    "rt_espanol":      "https://actualidad.rt.com/rss",
    "france24_esp":    "https://www.france24.com/es/rss",
    "bbc_mundo":       "https://feeds.bbci.co.uk/mundo/rss.xml",
}

FEEDS_INSTITUCIONALES = {
    "ine":             "https://www.ine.mx/informacion-para-medios/boletin-prensa/feed/",
    "ieez":            "https://ieez.org.mx/noticias/feed/",  # IEEZ Zacatecas
    "banxico":         "https://www.banxico.org.mx/rss/comunicados.xml",
    "coneval":         "https://www.coneval.org.mx/Informes/Coordinacion/feed.aspx",
}

TODOS_LOS_FEEDS = {
    **FEEDS_LOCALES,
    **FEEDS_NACIONALES,
    **FEEDS_INTERNACIONALES,
    **FEEDS_INSTITUCIONALES,
}

# ─── CANDIDATOS 2027 ─────────────────────────────────────────────────────────

CANDIDATOS = {
    "david_monreal": {
        "nombre":   "David Monreal Ávila",
        "partido":  "Morena",
        "cargo_actual": "Gobernador (periodo vigente)",
        "alianza":  "Morena-PT-PVEM",
        "twitter":  "@David_Monreal_A",
        "palabras_clave": [
            "David Monreal", "Monreal Ávila", "gobernador Monreal",
            "Morena Zacatecas", "David Monreal gobernador"
        ],
        "red_politica": ["Ricardo Monreal", "AMLO", "Claudia Sheinbaum", "Mario Delgado"],
    },
    "jose_haro": {
        "nombre":   "José Haro Montes",
        "partido":  "PAN",
        "cargo_actual": "Diputado Federal (est.)",
        "alianza":  "PAN-PRI-PRD (Va por México)",
        "twitter":  None,
        "palabras_clave": [
            "José Haro", "Haro Montes", "PAN Zacatecas"
        ],
        "red_politica": ["Marko Cortés", "Alejandro Moreno", "PRI Zacatecas"],
    },
    "claudia_anaya": {
        "nombre":   "Claudia Anaya Mota",
        "partido":  "PRI",
        "cargo_actual": "Ex candidata a gobernadora / ex senadora",
        "alianza":  "PRI (posible alianza Va por México)",
        "twitter":  "@claudiaanayamx",
        "palabras_clave": [
            "Claudia Anaya", "Anaya Mota", "PRI Zacatecas",
            "senadora Anaya"
        ],
        "red_politica": ["Alejandro Moreno", "PRI nacional", "PAN"],
    },
    "saul_monreal": {
        "nombre":   "Saúl Monreal Ávila",
        "partido":  "Morena",
        "cargo_actual": "Ex alcalde Fresnillo / figura interna Morena",
        "alianza":  "Morena (precandidato interno)",
        "twitter":  None,
        "palabras_clave": [
            "Saúl Monreal", "Saul Monreal", "Morena Zacatecas",
            "Monreal Fresnillo"
        ],
        "red_politica": ["David Monreal", "Ricardo Monreal"],
    },
    "roberto_cabrera": {
        "nombre":   "Roberto Cabrera Valencia",
        "partido":  "Movimiento Ciudadano",
        "cargo_actual": "Candidato potencial MC",
        "alianza":  "MC",
        "twitter":  None,
        "palabras_clave": [
            "Roberto Cabrera", "Movimiento Ciudadano Zacatecas", "MC Zacatecas"
        ],
        "red_politica": ["Dante Delgado", "MC nacional"],
    },
    "jorge_miranda": {
        "nombre":   "Jorge Miranda Castro",
        "partido":  "PAN",
        "cargo_actual": "Figura local PAN",
        "alianza":  "PAN",
        "twitter":  None,
        "palabras_clave": [
            "Jorge Miranda", "Miranda Castro", "PAN Zacatecas"
        ],
        "red_politica": ["Marko Cortés"],
    },
    "eva_velazquez": {
        "nombre":   "Eva Velázquez Campa",
        "partido":  "Independiente / Ciudadano",
        "cargo_actual": "Activista civil",
        "alianza":  "No definida",
        "twitter":  None,
        "palabras_clave": [
            "Eva Velázquez", "Velázquez Campa", "candidata independiente Zacatecas"
        ],
        "red_politica": [],
    },
}

# ─── DICCIONARIOS DE CLASIFICACIÓN ───────────────────────────────────────────

KEYWORDS_ZACATECAS = [
    "Zacatecas", "zacatecano", "zacatecana", "Fresnillo", "Guadalupe Zac",
    "Jerez", "Calera", "Jalpa", "Nochistlán", "Tlaltenango", "Sombrerete",
    "Loreto", "Villanueva", "Rio Grande Zacatecas", "Ojocaliente",
    "gobernador Monreal", "gobernatura Zacatecas"
]

KEYWORDS_MEXICO = [
    "México", "Mexico", "mexicano", "mexicana", "AMLO", "Sheinbaum",
    "gobierno federal", "Congreso", "Senado", "Cámara de Diputados",
    "Morena", "PRI", "PAN", "PRD", "MC", "Movimiento Ciudadano",
    "presidencia", "secretaría", "INE", "IEEZ"
]

# Geopolitica → señales con impacto en Zacatecas (minería, energía, remesas)
EVENTOS_GEOPOLITICOS = {
    "guerra": [
        "guerra", "conflicto armado", "invasión", "ataque militar",
        "bombardeo", "combate", "ofensiva", "frente de batalla",
        "Ukraine", "Ucrania", "Gaza", "Taiwán", "Corea"
    ],
    "sanciones": [
        "sanciones", "sanción", "embargo", "restricciones comerciales",
        "bloqueo económico", "lista negra OFAC", "SWIFT",
        "sanciones Rusia", "sanciones Irán", "sanciones Venezuela"
    ],
    "petroleo_energia": [
        "petróleo", "petroleo", "WTI", "Brent", "crudo", "OPEP", "OPEC",
        "gas natural", "GNL", "refinería", "Pemex", "CFE", "energía eléctrica",
        "precio energía", "litio", "cobre", "zinc", "plata"  # minerales Zac
    ],
    "comercio": [
        "arancel", "tarifa", "comercio exterior", "exportaciones",
        "importaciones", "cadena de suministro", "supply chain",
        "TMEC", "T-MEC", "USMCA", "OMC", "WTO", "dumping",
        "reshoring", "nearshoring", "manufactura"
    ],
    "inflacion_economia": [
        "inflación", "inflacion", "IPC", "Fed", "Federal Reserve",
        "Banxico", "tasa de interés", "tipo de cambio", "dólar",
        "peso mexicano", "devaluación", "remesas", "recesión",
        "crecimiento PIB", "desempleo", "empleo"
    ],
    "cadena_suministro": [
        "cadena de suministro", "logística", "puerto", "flete",
        "semiconductor", "chip", "escasez", "inventario",
        "manufactura global", "reshoring", "friendshoring"
    ],
}

EVENTOS_ELECTORALES = {
    "declaraciones": [
        "declaró", "afirmó", "dijo", "señaló", "propuso",
        "prometió", "anunció", "presentó propuesta", "posicionamiento"
    ],
    "escandalo": [
        "escándalo", "escandalo", "corrupción", "corrupcion",
        "desvío", "desvio", "malversación", "acusación",
        "denuncia", "investigación", "Fiscalía", "detención"
    ],
    "encuestas": [
        "encuesta", "sondeo", "preferencia electoral", "intención de voto",
        "tendencia", "popularidad", "aprobación", "desaprobación"
    ],
    "alianzas": [
        "alianza", "coalición", "coalicion", "acuerdo político",
        "respaldo", "apoyo", "candidatura conjunta", "frente"
    ],
    "conflicto_interno": [
        "pugna interna", "fractura", "división", "disidencia",
        "expulsión", "renuncia al partido", "conflicto interno"
    ],
    "campana": [
        "campaña", "campana", "acto de campaña", "mitin",
        "candidato", "candidatura", "registro candidato", "INE registro",
        "precampaña", "debate", "plataforma electoral"
    ],
}

PARTIDOS = {
    "morena":  ["Morena", "MORENA", "4T", "cuarta transformación"],
    "pan":     ["PAN", "panista", "blanquiazul", "Acción Nacional"],
    "pri":     ["PRI", "priista", "tricolor", "Revolucionario Institucional"],
    "prd":     ["PRD", "perredista", "sol azteca"],
    "mc":      ["MC", "Movimiento Ciudadano", "naranja", "emecista"],
    "pvem":    ["PVEM", "Verde", "ecologista"],
    "pt":      ["PT", "Trabajo", "petista"],
    "morena_aliados": ["PT", "PVEM", "Morena"],
}

# ─── DATACLASSES ─────────────────────────────────────────────────────────────

@dataclass
class Noticia:
    id:           str = ""
    titulo:       str = ""
    resumen:      str = ""
    url:          str = ""
    fuente:       str = ""
    fecha:        str = ""
    categoria:    str = "no_clasificada"    # local|nacional|internacional|geopolitica|electoral
    subcategoria: str = ""
    relevancia_zac: float = 0.0
    menciones_candidatos: dict = field(default_factory=dict)
    señales_geopoliticas: dict = field(default_factory=dict)
    señales_electorales:  dict = field(default_factory=dict)
    partidos_detectados:  list = field(default_factory=list)
    sentiment_score:      float = 0.0      # -1 negativo → 1 positivo
    palabras_clave_match: list = field(default_factory=list)
    raw_text:     str = ""

@dataclass
class PerfilCandidato:
    id:           str = ""
    nombre:       str = ""
    partido:      str = ""
    alianza:      str = ""
    menciones_totales: int = 0
    menciones_7d:      int = 0
    menciones_30d:     int = 0
    sentiment_promedio: float = 0.0
    señales_positivas:  int = 0
    señales_negativas:  int = 0
    eventos_escandalo:  int = 0
    eventos_alianza:    int = 0
    eventos_encuesta:   int = 0
    eventos_declaracion: int = 0
    score_momentum:     float = 0.0   # tendencia reciente
    score_visibilidad:  float = 0.0
    score_compuesto:    float = 0.0
    noticias_recientes: list = field(default_factory=list)
    red_politica_activa: list = field(default_factory=list)

@dataclass
class EstadisticasRadar:
    timestamp:       str = ""
    total_noticias:  int = 0
    por_categoria:   dict = field(default_factory=dict)
    por_fuente:      dict = field(default_factory=dict)
    # Señales geopolíticas
    señal_guerra:    int = 0
    señal_sanciones: int = 0
    señal_petroleo:  int = 0
    señal_comercio:  int = 0
    señal_inflacion: int = 0
    señal_suministro: int = 0
    # Señales electorales
    trend_morena:    int = 0
    trend_pan:       int = 0
    trend_pri:       int = 0
    trend_mc:        int = 0
    trend_pvem:      int = 0
    # Ranking candidatos
    ranking_menciones: list = field(default_factory=list)
    ranking_momentum:  list = field(default_factory=list)
    # Alertas activas
    alertas:         list = field(default_factory=list)

# ─── MÓDULO 1: MINADOR RSS ────────────────────────────────────────────────────

class MinadorRSS:
    """Extrae noticias de feeds RSS de fuentes locales, nacionales e internacionales."""

    def __init__(self, timeout: int = 15, max_age_days: int = 30):
        self.timeout     = timeout
        self.max_age     = timedelta(days=max_age_days)
        self.noticias    = []
        self.hashes_vistos = set()
        self.stats       = defaultdict(int)

    def _hash_noticia(self, titulo: str, url: str) -> str:
        return hashlib.md5(f"{titulo}{url}".encode()).hexdigest()[:12]

    def _parsear_fecha(self, entry) -> str:
        """Extrae y normaliza fecha de la entrada RSS."""
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6]).isoformat()
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6]).isoformat()
        except Exception:
            pass
        return datetime.now().isoformat()

    def _es_reciente(self, fecha_str: str) -> bool:
        try:
            fecha = datetime.fromisoformat(fecha_str)
            return (datetime.now() - fecha) <= self.max_age
        except Exception:
            return True

    def scrape_feed(self, nombre: str, url: str) -> list[Noticia]:
        """Parsea un feed RSS y devuelve lista de Noticia."""
        if not FEEDPARSER_OK:
            log.warning("feedparser no disponible — usando demo data")
            return self._datos_demo(nombre)

        noticias = []
        try:
            log.info(f"  ↳ {nombre}: {url}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "ZAC-OSINT/1.0"})

            for entry in feed.entries[:50]:  # máx 50 por feed
                titulo   = getattr(entry, "title",   "") or ""
                resumen  = getattr(entry, "summary", "") or ""
                link     = getattr(entry, "link",    "") or ""
                fecha    = self._parsear_fecha(entry)

                if not titulo or not self._es_reciente(fecha):
                    continue

                nid = self._hash_noticia(titulo, link)
                if nid in self.hashes_vistos:
                    continue
                self.hashes_vistos.add(nid)

                # Limpiar HTML del resumen
                if resumen:
                    resumen = BeautifulSoup(resumen, "html.parser").get_text(" ", strip=True)[:500] if REQUESTS_OK else re.sub(r"<[^>]+>", " ", resumen)[:500]

                n = Noticia(
                    id=nid,
                    titulo=titulo.strip(),
                    resumen=resumen.strip(),
                    url=link,
                    fuente=nombre,
                    fecha=fecha,
                    raw_text=f"{titulo} {resumen}".lower()
                )
                noticias.append(n)
                self.stats[nombre] += 1

        except Exception as e:
            log.error(f"Error en {nombre}: {e}")

        return noticias

    def scrape_todos(self, feeds: dict = None) -> list[Noticia]:
        """Scrape todos los feeds configurados."""
        if feeds is None:
            feeds = TODOS_LOS_FEEDS

        log.info(f"Iniciando scraping de {len(feeds)} feeds...")
        todas = []
        for nombre, url in feeds.items():
            noticias = self.scrape_feed(nombre, url)
            todas.extend(noticias)
            time.sleep(0.5)  # Rate limiting cortés

        log.info(f"✓ Total extraído: {len(todas)} noticias únicas")
        self.noticias = todas
        return todas

    def _datos_demo(self, fuente: str) -> list[Noticia]:
        """Datos de demostración cuando no hay conexión."""
        demos = [
            ("David Monreal presenta plan de inversión para Fresnillo",
             "El gobernador David Monreal Ávila anunció una inversión de 500 mdp para infraestructura en Fresnillo, Zacatecas.",
             "https://demo.example.com/1"),
            ("PAN Zacatecas destaca candidatura de José Haro para gubernatura 2027",
             "El Partido Acción Nacional en Zacatecas formalizó el apoyo a José Haro como precandidato a gobernador.",
             "https://demo.example.com/2"),
            ("Aranceles de Trump afectan exportaciones de plata zacatecana",
             "La nueva ronda de aranceles impuestos por Estados Unidos afecta directamente la exportación de plata desde Zacatecas.",
             "https://demo.example.com/3"),
            ("Encuesta: Morena mantiene ventaja en intención de voto en Zacatecas",
             "Sondeo nacional muestra a Morena con 45% de preferencia en Zacatecas rumbo a 2027, PAN con 28%, MC con 15%.",
             "https://demo.example.com/4"),
            ("Claudia Anaya anuncia alianza con organizaciones civiles de Zacatecas",
             "La ex senadora del PRI Claudia Anaya Mota formalizó alianzas con grupos de la sociedad civil zacatecana.",
             "https://demo.example.com/5"),
            ("Precio del petróleo sube por conflicto en Medio Oriente",
             "El crudo WTI superó los 90 dólares ante escalada de tensiones en Medio Oriente, lo que afecta precios energéticos en México.",
             "https://demo.example.com/6"),
            ("Banxico mantiene tasa en 11% ante presiones inflacionarias",
             "El Banco de México decidió mantener la tasa de referencia en 11% para contener la inflación que ronda el 4.8%.",
             "https://demo.example.com/7"),
            ("Saúl Monreal busca posicionarse en Fresnillo de cara a 2027",
             "El ex alcalde de Fresnillo Saúl Monreal Ávila intensifica actividad política en la región ante las próximas elecciones.",
             "https://demo.example.com/8"),
            ("Movimiento Ciudadano confirma estructura en Zacatecas",
             "El partido naranja consolida su presencia en 10 municipios zacatecanos con miras a la elección de gobernatura.",
             "https://demo.example.com/9"),
            ("Guerra comercial entre EEUU y China impacta cadenas de suministro en México",
             "Los nuevos aranceles recíprocos entre Washington y Pekín generan incertidumbre en las cadenas de suministro que atraviesan México.",
             "https://demo.example.com/10"),
        ]
        noticias = []
        for i, (titulo, resumen, url) in enumerate(demos):
            n = Noticia(
                id=f"demo_{fuente}_{i}",
                titulo=titulo,
                resumen=resumen,
                url=url,
                fuente=fuente,
                fecha=datetime.now().isoformat(),
                raw_text=f"{titulo} {resumen}".lower()
            )
            noticias.append(n)
        return noticias[:3]  # 3 por fuente en demo

# ─── MÓDULO 2: ANALIZADOR OSINT ──────────────────────────────────────────────

class AnalizadorOSINT:
    """Clasificador y detector de señales sobre noticias extraídas."""

    def __init__(self):
        self.stats = defaultdict(int)

    # ── Clasificación geográfica ───────────────────────────────────────────────

    def detectar_alcance(self, noticia: Noticia) -> str:
        texto = noticia.raw_text

        # Prioridad: si menciona Zacatecas directamente
        if any(kw.lower() in texto for kw in KEYWORDS_ZACATECAS):
            return "local"

        # Mención de México pero no específicamente Zacatecas
        if any(kw.lower() in texto for kw in KEYWORDS_MEXICO):
            return "nacional"

        # Geopolítico — señales mundiales
        for evento, keywords in EVENTOS_GEOPOLITICOS.items():
            if any(kw.lower() in texto for kw in keywords):
                return "geopolitica"

        # Fuente local
        if noticia.fuente in FEEDS_LOCALES:
            return "local"
        if noticia.fuente in FEEDS_NACIONALES:
            return "nacional"
        if noticia.fuente in FEEDS_INTERNACIONALES:
            return "internacional"
        if noticia.fuente in FEEDS_INSTITUCIONALES:
            return "institucional"

        return "nacional"

    # ── Detección señales geopolíticas ────────────────────────────────────────

    def detectar_señales_geopoliticas(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        señales = {}
        for evento, keywords in EVENTOS_GEOPOLITICOS.items():
            hits = [kw for kw in keywords if kw.lower() in texto]
            if hits:
                señales[evento] = {"count": len(hits), "matches": hits[:5]}
        return señales

    # ── Detección señales electorales ─────────────────────────────────────────

    def detectar_señales_electorales(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        señales = {}
        for tipo, keywords in EVENTOS_ELECTORALES.items():
            hits = [kw for kw in keywords if kw.lower() in texto]
            if hits:
                señales[tipo] = {"count": len(hits), "matches": hits[:5]}
        return señales

    # ── Detección candidatos ──────────────────────────────────────────────────

    def detectar_candidatos(self, noticia: Noticia) -> dict:
        texto = noticia.raw_text
        menciones = {}
        for cid, datos in CANDIDATOS.items():
            hits = [kw for kw in datos["palabras_clave"] if kw.lower() in texto]
            if hits:
                menciones[cid] = {"nombre": datos["nombre"], "hits": hits}
        return menciones

    # ── Detección partidos ────────────────────────────────────────────────────

    def detectar_partidos(self, noticia: Noticia) -> list:
        texto = noticia.raw_text
        encontrados = []
        for partido, keywords in PARTIDOS.items():
            if any(kw.lower() in texto for kw in keywords):
                if partido not in encontrados:
                    encontrados.append(partido)
        return encontrados

    # ── Relevancia para Zacatecas ─────────────────────────────────────────────

    def calcular_relevancia_zac(self, noticia: Noticia) -> float:
        """Score 0-1 de relevancia para Zacatecas."""
        score = 0.0
        texto  = noticia.raw_text

        # Mención directa de Zacatecas (+0.4 base)
        if any(kw.lower() in texto for kw in KEYWORDS_ZACATECAS):
            score += 0.4

        # Mención de candidato local (+0.2 por candidato)
        for cid, datos in CANDIDATOS.items():
            if any(kw.lower() in texto for kw in datos["palabras_clave"]):
                score += 0.2
                break

        # Señal geopolítica con impacto directo en Zac
        # (minería plata/zinc, energía, remesas → clave para economía Zac)
        impacto_directo = ["plata", "zinc", "minería", "remesas", "fresnillo", "zacatecana"]
        if any(kw in texto for kw in impacto_directo):
            score += 0.2

        # Señales electorales (+0.15)
        if noticia.señales_electorales:
            score += 0.15

        # Fuente local (+0.05)
        if noticia.fuente in FEEDS_LOCALES:
            score += 0.05

        return min(score, 1.0)

    # ── Sentiment simplificado (sin TextBlob si no está instalado) ────────────

    POSITIVOS = {"gana", "avanza", "apoya", "logra", "éxito", "positivo",
                 "crecimiento", "inversión", "beneficio", "acuerdo", "alianza",
                 "victoria", "respaldo", "aumento", "mejora", "desarrollo"}
    NEGATIVOS = {"pierde", "cae", "crítica", "escándalo", "denuncia", "derrota",
                 "conflicto", "crisis", "violencia", "corrupción", "desvío",
                 "sanción", "arresto", "dimite", "renuncia", "baja", "fracasa"}

    def analizar_sentiment(self, noticia: Noticia) -> float:
        """Retorna score -1 (muy negativo) a 1 (muy positivo)."""
        palabras = set(noticia.raw_text.split())
        pos = len(palabras & self.POSITIVOS)
        neg = len(palabras & self.NEGATIVOS)
        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 3)

    # ── Clasificador completo ──────────────────────────────────────────────────

    def analizar(self, noticia: Noticia) -> Noticia:
        """Aplica todos los análisis a una noticia."""
        noticia.categoria            = self.detectar_alcance(noticia)
        noticia.señales_geopoliticas = self.detectar_señales_geopoliticas(noticia)
        noticia.señales_electorales  = self.detectar_señales_electorales(noticia)
        noticia.menciones_candidatos = self.detectar_candidatos(noticia)
        noticia.partidos_detectados  = self.detectar_partidos(noticia)
        noticia.relevancia_zac       = self.calcular_relevancia_zac(noticia)
        noticia.sentiment_score      = self.analizar_sentiment(noticia)

        # Subcategoría más específica
        if noticia.señales_electorales:
            noticia.subcategoria = "electoral_" + list(noticia.señales_electorales.keys())[0]
        elif noticia.señales_geopoliticas:
            noticia.subcategoria = "geo_" + list(noticia.señales_geopoliticas.keys())[0]

        self.stats[noticia.categoria] += 1
        return noticia

    def analizar_lote(self, noticias: list[Noticia]) -> list[Noticia]:
        log.info(f"Analizando {len(noticias)} noticias...")
        resultado = [self.analizar(n) for n in noticias]
        log.info(f"✓ Distribución: {dict(self.stats)}")
        return resultado

# ─── MÓDULO 3: PERFILES CANDIDATOS ───────────────────────────────────────────

class AnalizadorCandidatos:
    """Construye perfiles estadísticos de candidatos a partir de noticias analizadas."""

    def __init__(self, noticias: list[Noticia]):
        self.noticias = noticias
        ahora = datetime.now()
        self.hace_7d  = ahora - timedelta(days=7)
        self.hace_30d = ahora - timedelta(days=30)

    def _fecha_noticia(self, n: Noticia) -> datetime:
        try:
            return datetime.fromisoformat(n.fecha)
        except Exception:
            return datetime.now()

    def construir_perfil(self, cid: str) -> PerfilCandidato:
        datos = CANDIDATOS[cid]
        perfil = PerfilCandidato(
            id=cid,
            nombre=datos["nombre"],
            partido=datos["partido"],
            alianza=datos["alianza"],
        )

        menciones_recientes = []

        for n in self.noticias:
            if cid not in n.menciones_candidatos:
                continue

            perfil.menciones_totales += 1
            fecha = self._fecha_noticia(n)
            if fecha >= self.hace_7d:
                perfil.menciones_7d += 1
            if fecha >= self.hace_30d:
                perfil.menciones_30d += 1

            # Acumular sentiment
            perfil.sentiment_promedio += n.sentiment_score
            if n.sentiment_score > 0.1:
                perfil.señales_positivas += 1
            elif n.sentiment_score < -0.1:
                perfil.señales_negativas += 1

            # Conteo de tipos de eventos
            for tipo in n.señales_electorales:
                if tipo == "escandalo":     perfil.eventos_escandalo += 1
                elif tipo == "alianzas":    perfil.eventos_alianza += 1
                elif tipo == "encuestas":   perfil.eventos_encuesta += 1
                elif tipo == "declaraciones": perfil.eventos_declaracion += 1

            # Noticias recientes para mostrar
            if fecha >= self.hace_7d:
                menciones_recientes.append({
                    "titulo": n.titulo,
                    "fuente": n.fuente,
                    "fecha":  n.fecha,
                    "sentiment": n.sentiment_score,
                    "url": n.url,
                })

        # Normalizar sentiment
        if perfil.menciones_totales > 0:
            perfil.sentiment_promedio = round(
                perfil.sentiment_promedio / perfil.menciones_totales, 3
            )

        # Score de visibilidad (normalizado sobre máximo posible)
        perfil.score_visibilidad = min(perfil.menciones_totales / 20.0, 1.0)

        # Score momentum: peso en menciones recientes
        if perfil.menciones_totales > 0:
            perfil.score_momentum = round(
                (perfil.menciones_7d * 2 + perfil.menciones_30d) /
                max(perfil.menciones_totales * 3, 1), 3
            )

        # Score compuesto: visibilidad + momentum - escándalos + alianzas
        perfil.score_compuesto = round(
            (perfil.score_visibilidad * 0.35) +
            (perfil.score_momentum    * 0.30) +
            (min(perfil.eventos_alianza,   5) / 5 * 0.20) +
            (min(perfil.eventos_encuesta,  5) / 5 * 0.15) -
            (min(perfil.eventos_escandalo, 5) / 5 * 0.25), 3
        )
        perfil.score_compuesto = max(0.0, min(1.0, perfil.score_compuesto))

        # Red política activa: figuras mencionadas junto al candidato
        perfil.red_politica_activa = datos.get("red_politica", [])

        perfil.noticias_recientes = sorted(
            menciones_recientes, key=lambda x: x["fecha"], reverse=True
        )[:5]

        return perfil

    def construir_todos(self) -> dict[str, PerfilCandidato]:
        log.info("Construyendo perfiles de candidatos...")
        perfiles = {}
        for cid in CANDIDATOS:
            perfiles[cid] = self.construir_perfil(cid)
            log.info(f"  {CANDIDATOS[cid]['nombre']}: {perfiles[cid].menciones_totales} menciones")
        return perfiles

# ─── MÓDULO 4: RADAR GEOPOLÍTICO ─────────────────────────────────────────────

class RadarGeopolitico:
    """Agrega señales geopolíticas y calcula impacto en Zacatecas."""

    # Correlaciones: señal global → impacto sectores Zacatecas
    CORRELACIONES_ZAC = {
        "guerra": {
            "minerales_estrategicos": 0.8,  # Zac = 1er prod plata mundial
            "precio_plata":           0.7,
            "remesas":               -0.3,  # migración afectada
        },
        "sanciones": {
            "comercio_exterior":     -0.6,
            "tipo_cambio":           -0.5,
        },
        "petroleo_energia": {
            "costo_energia_industrial": 0.9,
            "costo_transporte":         0.7,
            "inflacion_local":          0.6,
        },
        "comercio": {
            "exportaciones_mineria":   0.7,
            "nearshoring_zac":         0.5,
            "empleo_manufactura":      0.4,
        },
        "inflacion_economia": {
            "poder_adquisitivo":      -0.8,
            "remesas_valor_real":     -0.5,
            "inversion_local":        -0.4,
        },
    }

    def __init__(self, noticias: list[Noticia]):
        self.noticias = noticias

    def calcular_intensidad(self) -> dict:
        """Calcula intensidad de cada señal geopolítica (0-100)."""
        totales = defaultdict(int)
        for n in self.noticias:
            for señal, datos in n.señales_geopoliticas.items():
                totales[señal] += datos.get("count", 0)

        # Normalizar a 0-100
        maximo = max(totales.values(), default=1)
        return {k: round(v / maximo * 100) for k, v in totales.items()}

    def calcular_impacto_zac(self) -> dict:
        """Traduce intensidades globales a impacto en sectores de Zacatecas."""
        intensidades = self.calcular_intensidad()
        impactos = defaultdict(float)

        for señal, intensidad in intensidades.items():
            correlaciones = self.CORRELACIONES_ZAC.get(señal, {})
            for sector, correlacion in correlaciones.items():
                impactos[sector] += (intensidad / 100) * correlacion

        # Normalizar impactos a -1..1
        return {k: round(max(-1.0, min(1.0, v)), 3)
                for k, v in impactos.items()}

    def generar_alertas(self, intensidades: dict) -> list:
        """Genera alertas cuando una señal supera umbral."""
        alertas = []
        UMBRALES = {
            "guerra":         60,
            "sanciones":      50,
            "petroleo_energia": 55,
            "comercio":       45,
            "inflacion_economia": 50,
        }
        for señal, umbral in UMBRALES.items():
            nivel = intensidades.get(señal, 0)
            if nivel >= umbral:
                alertas.append({
                    "señal":   señal,
                    "nivel":   nivel,
                    "critico": nivel >= 75,
                    "mensaje": f"⚠️ Señal '{señal}' en nivel {nivel}/100 — revisar impacto Zacatecas"
                })
        return sorted(alertas, key=lambda x: x["nivel"], reverse=True)

# ─── MÓDULO 5: ESTADÍSTICAS Y EXPORTADOR ─────────────────────────────────────

class Exportador:
    """Genera estadísticas y exporta en múltiples formatos."""

    def __init__(self, noticias: list[Noticia],
                 perfiles: dict[str, PerfilCandidato],
                 radar: RadarGeopolitico):
        self.noticias = noticias
        self.perfiles = perfiles
        self.radar    = radar

    def generar_estadisticas(self) -> EstadisticasRadar:
        stats = EstadisticasRadar(timestamp=datetime.now().isoformat())
        stats.total_noticias = len(self.noticias)

        # Distribución por categoría y fuente
        stats.por_categoria = dict(Counter(n.categoria for n in self.noticias))
        stats.por_fuente    = dict(Counter(n.fuente for n in self.noticias))

        # Señales geopolíticas
        for n in self.noticias:
            stats.señal_guerra    += n.señales_geopoliticas.get("guerra",    {}).get("count", 0)
            stats.señal_sanciones += n.señales_geopoliticas.get("sanciones", {}).get("count", 0)
            stats.señal_petroleo  += n.señales_geopoliticas.get("petroleo_energia", {}).get("count", 0)
            stats.señal_comercio  += n.señales_geopoliticas.get("comercio",  {}).get("count", 0)
            stats.señal_inflacion += n.señales_geopoliticas.get("inflacion_economia", {}).get("count", 0)
            stats.señal_suministro+= n.señales_geopoliticas.get("cadena_suministro", {}).get("count", 0)

        # Tendencias por partido
        for n in self.noticias:
            if "morena" in n.partidos_detectados:   stats.trend_morena += 1
            if "pan"    in n.partidos_detectados:   stats.trend_pan    += 1
            if "pri"    in n.partidos_detectados:   stats.trend_pri    += 1
            if "mc"     in n.partidos_detectados:   stats.trend_mc     += 1
            if "pvem"   in n.partidos_detectados:   stats.trend_pvem   += 1

        # Rankings
        stats.ranking_menciones = sorted(
            [(cid, p.menciones_totales) for cid, p in self.perfiles.items()],
            key=lambda x: x[1], reverse=True
        )
        stats.ranking_momentum = sorted(
            [(cid, p.score_momentum) for cid, p in self.perfiles.items()],
            key=lambda x: x[1], reverse=True
        )

        # Alertas
        intensidades = self.radar.calcular_intensidad()
        stats.alertas = self.radar.generar_alertas(intensidades)

        return stats

    def exportar_json(self, directorio: str = "output/") -> dict:
        """Exporta todos los datos a JSON."""
        Path(directorio).mkdir(parents=True, exist_ok=True)
        stats = self.generar_estadisticas()

        # 1. Noticias clasificadas
        noticias_dict = [asdict(n) for n in self.noticias]
        ruta_noticias = Path(directorio) / "noticias.json"
        with open(ruta_noticias, "w", encoding="utf-8") as f:
            json.dump(noticias_dict, f, ensure_ascii=False, indent=2)

        # 2. Perfiles candidatos
        perfiles_dict = {cid: asdict(p) for cid, p in self.perfiles.items()}
        ruta_perfiles = Path(directorio) / "candidatos.json"
        with open(ruta_perfiles, "w", encoding="utf-8") as f:
            json.dump(perfiles_dict, f, ensure_ascii=False, indent=2)

        # 3. Estadísticas del radar
        stats_dict = asdict(stats)
        ruta_stats = Path(directorio) / "radar_stats.json"
        with open(ruta_stats, "w", encoding="utf-8") as f:
            json.dump(stats_dict, f, ensure_ascii=False, indent=2)

        # 4. Señales geopolíticas
        geo_dict = {
            "intensidades":   self.radar.calcular_intensidad(),
            "impacto_zac":    self.radar.calcular_impacto_zac(),
            "alertas":        stats.alertas,
            "timestamp":      stats.timestamp,
        }
        ruta_geo = Path(directorio) / "geopolitico.json"
        with open(ruta_geo, "w", encoding="utf-8") as f:
            json.dump(geo_dict, f, ensure_ascii=False, indent=2)

        # 5. JSONL: stream de noticias (para pipeline de ML / embeddings)
        ruta_jsonl = Path(directorio) / "noticias.jsonl"
        with open(ruta_jsonl, "w", encoding="utf-8") as f:
            for n in self.noticias:
                f.write(json.dumps(asdict(n), ensure_ascii=False) + "\n")

        # 6. JSON-LD: schema.org para SEO / indexación
        schema = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Observatorio Electoral Zacatecas 2027",
            "description": "Análisis OSINT de elecciones de gobernatura Zacatecas 2027 y contexto geopolítico",
            "creator": {"@type": "Organization", "name": "Nicho Analyzer"},
            "dateModified": stats.timestamp,
            "keywords": ["Zacatecas", "elecciones 2027", "gobernatura", "OSINT", "geopolítica"],
            "hasPart": [
                {"@type": "Dataset", "name": "Noticias clasificadas", "encodingFormat": "application/json"},
                {"@type": "Dataset", "name": "Perfiles candidatos",   "encodingFormat": "application/json"},
            ]
        }
        ruta_jsonld = Path(directorio) / "dataset.jsonld"
        with open(ruta_jsonld, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        log.info(f"✓ Exportado a {directorio}/ — {len(noticias_dict)} noticias, {len(perfiles_dict)} candidatos")

        return {
            "noticias":       str(ruta_noticias),
            "candidatos":     str(ruta_perfiles),
            "radar_stats":    str(ruta_stats),
            "geopolitico":    str(ruta_geo),
            "noticias_jsonl": str(ruta_jsonl),
            "jsonld":         str(ruta_jsonld),
        }

    def imprimir_reporte(self):
        """Imprime resumen en consola."""
        stats = self.generar_estadisticas()
        intensidades = self.radar.calcular_intensidad()
        impacto_zac  = self.radar.calcular_impacto_zac()

        print("\n" + "═" * 65)
        print("  ZAC-OSINT — REPORTE DE RADAR ELECTORAL Y GEOPOLÍTICO")
        print(f"  {stats.timestamp[:19]}")
        print("═" * 65)

        print(f"\n📰 NOTICIAS PROCESADAS: {stats.total_noticias}")
        for cat, n in sorted(stats.por_categoria.items(), key=lambda x: -x[1]):
            bar = "█" * min(n, 30)
            print(f"   {cat:<20} {bar} {n}")

        print("\n🌐 RADAR GEOPOLÍTICO (intensidad 0-100):")
        for señal, nivel in sorted(intensidades.items(), key=lambda x: -x[1]):
            bar = "█" * (nivel // 5)
            emoji = "🔴" if nivel >= 70 else "🟡" if nivel >= 40 else "🟢"
            print(f"   {emoji} {señal:<22} {bar} {nivel}")

        print("\n🏔️ IMPACTO EN ZACATECAS (correlaciones):")
        for sector, impacto in sorted(impacto_zac.items(), key=lambda x: -abs(x[1])):
            signo = "↑" if impacto > 0 else "↓"
            print(f"   {signo} {sector:<30} {impacto:+.2f}")

        print("\n🗳️  TENDENCIAS ELECTORALES (menciones en noticias):")
        for partido, n in [("Morena", stats.trend_morena), ("PAN", stats.trend_pan),
                           ("PRI", stats.trend_pri), ("MC", stats.trend_mc)]:
            bar = "█" * min(n, 30)
            print(f"   {partido:<12} {bar} {n}")

        print("\n👤 RANKING CANDIDATOS:")
        for cid, menciones in stats.ranking_menciones[:7]:
            perfil = self.perfiles[cid]
            nombre_corto = CANDIDATOS[cid]["nombre"].split()[0] + " " + CANDIDATOS[cid]["nombre"].split()[1]
            print(f"   {nombre_corto:<25} menciones={menciones:3d}  "
                  f"score={perfil.score_compuesto:.2f}  "
                  f"sent={perfil.sentiment_promedio:+.2f}")

        if stats.alertas:
            print("\n⚠️  ALERTAS ACTIVAS:")
            for a in stats.alertas:
                print(f"   {'🔴' if a['critico'] else '🟡'} {a['mensaje']}")

        print("═" * 65 + "\n")

# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def ejecutar_pipeline(config: dict = None) -> dict:
    """
    Ejecuta el pipeline completo.

    config:
        feeds:       dict con feeds RSS (default: TODOS_LOS_FEEDS)
        max_age:     int días máximos de antigüedad (default: 30)
        output_dir:  str directorio de salida (default: 'output/')
        verbose:     bool (default: True)
    """
    if config is None:
        config = {}

    feeds      = config.get("feeds",      TODOS_LOS_FEEDS)
    max_age    = config.get("max_age",    30)
    output_dir = config.get("output_dir", "output/")
    verbose    = config.get("verbose",    True)

    log.info("=" * 60)
    log.info("ZAC-OSINT — Iniciando pipeline completo")
    log.info("=" * 60)

    # 1. Minado
    minador = MinadorRSS(max_age_days=max_age)
    noticias_raw = minador.scrape_todos(feeds)

    # 2. Análisis OSINT
    analizador = AnalizadorOSINT()
    noticias = analizador.analizar_lote(noticias_raw)

    # 3. Perfiles candidatos
    ana_cand = AnalizadorCandidatos(noticias)
    perfiles = ana_cand.construir_todos()

    # 4. Radar geopolítico
    radar = RadarGeopolitico(noticias)

    # 5. Exportar
    exportador = Exportador(noticias, perfiles, radar)
    rutas = exportador.exportar_json(output_dir)

    if verbose:
        exportador.imprimir_reporte()

    return {
        "noticias": noticias,
        "perfiles": perfiles,
        "radar":    radar,
        "rutas":    rutas,
        "stats":    exportador.generar_estadisticas(),
    }

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ZAC-OSINT: Motor de inteligencia electoral y geopolítica para Zacatecas 2027"
    )
    parser.add_argument("--run-all",         action="store_true", help="Ejecutar pipeline completo")
    parser.add_argument("--solo-electoral",  action="store_true", help="Solo feeds y análisis electoral")
    parser.add_argument("--solo-geopolitico",action="store_true", help="Solo feeds internacionales")
    parser.add_argument("--candidatos",      action="store_true", help="Solo perfiles de candidatos")
    parser.add_argument("--exportar-json",   metavar="DIR",       help="Directorio de exportación")
    parser.add_argument("--max-age",         type=int, default=30,help="Antigüedad máxima en días")
    parser.add_argument("--demo",            action="store_true", help="Modo demo con datos simulados")
    args = parser.parse_args()

    config = {"max_age": args.max_age}

    if args.exportar_json:
        config["output_dir"] = args.exportar_json

    if args.solo_electoral:
        config["feeds"] = {**FEEDS_LOCALES, **FEEDS_NACIONALES, **FEEDS_INSTITUCIONALES}

    elif args.solo_geopolitico:
        config["feeds"] = {**FEEDS_INTERNACIONALES, **FEEDS_NACIONALES}

    elif args.candidatos:
        config["feeds"] = {**FEEDS_LOCALES, **FEEDS_NACIONALES}

    # Siempre ejecutar
    resultado = ejecutar_pipeline(config)

    log.info("Pipeline completado. Archivos generados:")
    for nombre, ruta in resultado["rutas"].items():
        log.info(f"  {nombre}: {ruta}")


if __name__ == "__main__":
    main()
