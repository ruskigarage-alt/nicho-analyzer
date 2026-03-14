#!/usr/bin/env python3
"""
generar_scoreboard.py
Dashboard electoral profesional — Zacatecas 2027
Estilo: terminal oscuro consistente con el dashboard principal
"""

import json
import os
import glob
from datetime import datetime, timezone
from collections import defaultdict

FECHA     = datetime.now(timezone.utc).strftime("%Y-%m-%d")
HORA      = datetime.now(timezone.utc).strftime("%H:%M UTC")
BASE_URL  = "https://ruskigarage-alt.github.io/nicho-analyzer"

# ─────────────────────────────────────────
# CARGAR DATOS
# ─────────────────────────────────────────
def cargar_electoral():
    path = f"datos_crudos/electoral_{FECHA}.json"
    if not os.path.exists(path):
        # Buscar el más reciente
        archivos = sorted(glob.glob("datos_crudos/electoral_*.json"), reverse=True)
        if not archivos:
            return None
        path = archivos[0]
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def cargar_historial():
    path = "datos_electorales/historial_momentum.json"
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

datos      = cargar_electoral()
historial  = cargar_historial()

if not datos:
    print("✗ No hay datos electorales. Corre primero minador_electoral.py")
    exit(1)

ASPIRANTES  = datos["aspirantes"]
ENTRADAS    = datos["entradas"]
MOMENTUM    = datos.get("momentum", {})

# ─────────────────────────────────────────
# CONSTRUIR RANKING
# ─────────────────────────────────────────
def calcular_ranking():
    """
    Combina preferencia base + momentum del día.
    """
    ranking = []
    for asp in ASPIRANTES:
        aid = asp["id"]
        m   = MOMENTUM.get(aid, {})
        menciones = m.get("menciones", 0)
        momentum  = m.get("momentum",  0)
        positivo  = m.get("positivo",  0)
        negativo  = m.get("negativo",  0)
        temas     = m.get("temas",     [])

        # Score compuesto: base + ajuste por momentum
        ajuste = min(max(momentum * 0.3, -5), 5)
        score  = round(asp["pct_base"] + ajuste, 1)

        # Tendencia vs historial
        tendencia = "→"
        fechas = sorted(historial.keys(), reverse=True)
        if len(fechas) >= 2:
            anterior = historial.get(fechas[1], {}).get(aid, {}).get("momentum", 0)
            actual   = momentum
            if actual > anterior + 1:
                tendencia = "▲"
            elif actual < anterior - 1:
                tendencia = "▼"

        ranking.append({
            **asp,
            "score":     score,
            "menciones": menciones,
            "momentum":  momentum,
            "positivo":  positivo,
            "negativo":  negativo,
            "temas":     temas,
            "tendencia": tendencia,
            "ajuste":    ajuste,
        })

    return sorted(ranking, key=lambda x: x["score"], reverse=True)

ranking = calcular_ranking()

# ─────────────────────────────────────────
# NOTICIAS POR ASPIRANTE
# ─────────────────────────────────────────
def noticias_aspirante(asp_id, max_items=3):
    items = []
    for e in ENTRADAS:
        if asp_id in e.get("aspirantes_mencionados", []):
            items.append(e)
        if len(items) >= max_items:
            break
    return items

# ─────────────────────────────────────────
# NOTICIAS ELECTORALES GENERALES
# ─────────────────────────────────────────
def noticias_generales(max_items=6):
    items = []
    vistos = set()
    for e in ENTRADAS:
        t = e.get("titulo", "")
        if t not in vistos and len(t) > 10:
            vistos.add(t)
            items.append(e)
        if len(items) >= max_items:
            break
    return items

# ─────────────────────────────────────────
# RELACIONES NACIONALES ↔ LOCALES
# ─────────────────────────────────────────
def detectar_conexiones():
    """Entradas que conectan tema nacional con Zacatecas."""
    conexiones = []
    kw_nacional = ["Morena nacional", "AMLO", "Claudia Sheinbaum", "PAN nacional",
                   "PRI nacional", "elecciones 2027 México", "TEPJF", "INE resolución",
                   "aranceles México", "economía nacional", "seguridad federal"]
    for e in ENTRADAS:
        texto = f"{e.get('titulo','')} {e.get('resumen','')}"
        tiene_nacional = any(k.lower() in texto.lower() for k in kw_nacional)
        tiene_local    = e.get("es_electoral") or e.get("es_contextual")
        if tiene_nacional and tiene_local:
            conexiones.append(e)
        if len(conexiones) >= 4:
            break
    return conexiones

conexiones = detectar_conexiones()

# ─────────────────────────────────────────
# GENERAR MINIGRÁFICO ASCII DE TENDENCIA
# ─────────────────────────────────────────
def mini_barra(valor, max_val=50, ancho=20):
    pct = min(valor / max_val, 1.0)
    fill = int(pct * ancho)
    empty = ancho - fill
    return "█" * fill + "░" * empty

# ─────────────────────────────────────────
# CONSTRUIR SCOREBOARD HTML
# ─────────────────────────────────────────
COLOR_PARTIDO = {
    "Morena":     "#C91A1A",
    "PT/Morena":  "#E05C00",
    "PT":         "#CC3300",
    "PAN":        "#005DAA",
    "PRI":        "#009E44",
}

def badge_partido(partido):
    color = COLOR_PARTIDO.get(partido, "#555")
    return f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}44;">{partido}</span>'

def badge_tendencia(t):
    if t == "▲":
        return '<span class="tend-up">▲ subiendo</span>'
    if t == "▼":
        return '<span class="tend-down">▼ bajando</span>'
    return '<span class="tend-flat">→ estable</span>'

def badge_tema(tema):
    colores = {
        "encuesta":      ("#58a6ff","#0d1f2b"),
        "candidatura":   ("#3fb950","#0d2b1a"),
        "alianza":       ("#d29922","#2b220d"),
        "seguridad":     ("#f85149","#2b0d0d"),
        "gasto_publico": ("#a371f7","#1a0d2b"),
        "corrupcion":    ("#f85149","#2b0d0d"),
        "nepotismo":     ("#f85149","#2b0d0d"),
        "general":       ("#8b949e","#161b22"),
    }
    c, bg = colores.get(tema, ("#8b949e","#161b22"))
    return f'<span class="tema-badge" style="background:{bg};color:{c};">{tema}</span>'

# Cards de aspirantes
cards_html = ""
for i, asp in enumerate(ranking):
    pos_label = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
    barra     = mini_barra(asp["score"], 50, 18)
    noticias  = noticias_aspirante(asp["id"], 2)
    temas_html = " ".join(badge_tema(t) for t in asp["temas"][:3]) if asp["temas"] else badge_tema("general")

    noticias_html = ""
    for n in noticias:
        t = n.get("titulo","")[:90].replace("<","&lt;").replace(">","&gt;")
        fuente_label = n.get("fuente","").replace("_"," ")
        tema_badge   = badge_tema(n.get("tema","general"))
        noticias_html += f"""
        <div class="noticia-item">
          <div class="noticia-meta">{fuente_label} {tema_badge}</div>
          <a href="{n.get('link','#')}" class="noticia-titulo">{t}</a>
        </div>"""

    if not noticias_html:
        noticias_html = '<div class="noticia-vacia">sin menciones hoy</div>'

    momentum_color = "g" if asp["momentum"] >= 0 else "r"
    momentum_signo = f"+{asp['momentum']}" if asp["momentum"] >= 0 else str(asp["momentum"])

    cards_html += f"""
    <div class="asp-card">
      <div class="asp-header">
        <div class="asp-pos">{pos_label}</div>
        <div class="asp-info">
          <div class="asp-nombre"><a href="perfil_{asp['id']}.html" style="color:#e6edf3;text-decoration:none;border-bottom:1px solid #30363d">{asp['nombre']}</a></div>
          <div class="asp-meta">{badge_partido(asp['partido'])} {badge_tendencia(asp['tendencia'])}</div>
        </div>
        <div class="asp-score-block">
          <div class="asp-score">{asp['score']}%</div>
          <div class="asp-momentum {momentum_color}">momentum {momentum_signo}</div>
        </div>
      </div>
      <div class="asp-barra-wrap">
        <span class="dim" style="font-size:10px;width:60px;display:inline-block">encuesta</span>
        <span class="barra-ascii" style="color:{asp['color']};">{barra}</span>
        <span class="barra-val">{asp['score']}%</span>
      </div>
      <div class="asp-barra-wrap">
        <span class="dim" style="font-size:10px;width:60px;display:inline-block">presencia</span>
        <span class="barra-ascii" style="color:#58a6ff;">{mini_barra(asp['menciones'], 12, 18)}</span>
        <span class="barra-val">{asp['menciones']} menciones</span>
      </div>
      <div class="asp-temas">{temas_html}</div>
      <div class="asp-noticias">
        {noticias_html}
      </div>
      <div class="asp-stats">
        <span class="dim">menciones hoy: </span><span class="w">{asp['menciones']}</span>
        <span class="dim"> | positivas: </span><span class="g">{asp['positivo']}</span>
        <span class="dim"> | negativas: </span><span class="r">{asp['negativo']}</span>
      </div>
    </div>"""

# Noticias generales
nots_gen = noticias_generales(6)
nots_gen_html = ""
for n in nots_gen:
    t  = n.get("titulo","")[:100].replace("<","&lt;").replace(">","&gt;")
    fu = n.get("fuente","").replace("_"," ")
    tb = badge_tema(n.get("tema","general"))
    nots_gen_html += f"""
    <div class="noticia-item">
      <div class="noticia-meta">{fu} {tb}</div>
      <a href="{n.get('link','#')}" class="noticia-titulo">{t}</a>
    </div>"""

# Conexiones nacionales
conexiones_html = ""
for c in conexiones:
    t  = c.get("titulo","")[:100].replace("<","&lt;").replace(">","&gt;")
    fu = c.get("fuente","").replace("_"," ")
    tb = badge_tema(c.get("tema","general"))
    conexiones_html += f"""
    <div class="noticia-item">
      <div class="noticia-meta">{fu} {tb}</div>
      <a href="{c.get('link','#')}" class="noticia-titulo">{t}</a>
    </div>"""

if not conexiones_html:
    conexiones_html = '<div class="noticia-vacia">sin conexiones detectadas hoy</div>'

# Movimiento de partidos
partidos_data = defaultdict(lambda: {"aspirantes": [], "menciones": 0, "momentum": 0})
for asp in ranking:
    p = asp["partido"].split("/")[0]  # Tomar el primero si es PT/Morena
    partidos_data[p]["aspirantes"].append(asp["nombre"].split()[0])
    partidos_data[p]["menciones"] += asp["menciones"]
    partidos_data[p]["momentum"]  += asp["momentum"]

partidos_html = ""
for partido, pd in sorted(partidos_data.items(), key=lambda x: x[1]["momentum"], reverse=True):
    color = COLOR_PARTIDO.get(partido, "#555")
    mom   = pd["momentum"]
    mom_s = f"+{mom}" if mom >= 0 else str(mom)
    mom_c = "g" if mom >= 0 else "r"
    partidos_html += f"""
    <div class="partido-row">
      <span class="partido-nombre" style="color:{color};">{partido}</span>
      <span class="dim">{', '.join(pd['aspirantes'][:2])}</span>
      <span class="partido-stats">
        <span class="dim">menciones: </span><span class="w">{pd['menciones']}</span>
        <span class="dim"> momentum: </span><span class="{mom_c}">{mom_s}</span>
      </span>
    </div>"""

# JSON-LD para robots
jsonld = json.dumps({
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": f"Scoreboard Electoral Zacatecas 2027 — {FECHA}",
    "description": "Seguimiento diario de aspirantes a gobernador y alcaldes en Zacatecas. Menciones, momentum y análisis de cobertura mediática.",
    "dateModified": datetime.now(timezone.utc).isoformat(),
    "url": f"{BASE_URL}/scoreboard.html",
    "about": {"@type": "Event", "name": "Elecciones Zacatecas 2027"},
    "keywords": "Zacatecas, elecciones, gobernador, 2027, Morena, PAN, PRI, candidatos",
}, ensure_ascii=False, indent=2)

total_entradas = len(ENTRADAS)
fuentes_unicas = len(set(e.get("fuente","") for e in ENTRADAS))

html = f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scoreboard Electoral Zacatecas 2027 — {FECHA}</title>
<meta name="description" content="Seguimiento diario de candidatos a gobernador Zacatecas 2027. Menciones, momentum mediático y análisis de cobertura. Actualizado {FECHA}.">
<meta name="robots" content="index, follow">
<meta name="keywords" content="Zacatecas elecciones 2027, candidatos gobernador Zacatecas, Morena Zacatecas, PAN Zacatecas">
<meta name="dateModified" content="{datetime.now(timezone.utc).isoformat()}">
<link rel="alternate" type="application/rss+xml" href="{BASE_URL}/mi_feed/feed.xml">
<script type="application/ld+json">{jsonld}</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:'Courier New',monospace;font-size:13px;padding:16px;line-height:1.7;max-width:960px;margin:0 auto}}
a{{color:#58a6ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
.g{{color:#3fb950}}.b{{color:#58a6ff}}.y{{color:#d29922}}.r{{color:#f85149}}.dim{{color:#484f58}}.w{{color:#e6edf3;font-weight:bold}}
.section{{margin-top:1.4rem}}
.section-title{{color:#58a6ff;font-size:11px;text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px;border-bottom:1px solid #21262d;padding-bottom:6px}}
/* CARDS */
.cards-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}}
.asp-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px;transition:border-color .2s}}
.asp-card:hover{{border-color:#30363d}}
.asp-header{{display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}}
.asp-pos{{font-size:20px;line-height:1;flex-shrink:0;width:28px}}
.asp-info{{flex:1}}
.asp-nombre{{color:#e6edf3;font-weight:bold;font-size:13px}}
.asp-meta{{margin-top:3px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.asp-score-block{{text-align:right;flex-shrink:0}}
.asp-score{{color:#e6edf3;font-size:22px;font-weight:bold;line-height:1}}
.asp-momentum{{font-size:11px;margin-top:2px}}
.asp-barra-wrap{{display:flex;align-items:center;gap:8px;margin:6px 0}}
.barra-ascii{{font-size:11px;letter-spacing:1px}}
.barra-val{{font-size:11px;color:#8b949e}}
.asp-temas{{margin:6px 0;display:flex;gap:4px;flex-wrap:wrap}}
.asp-noticias{{margin-top:8px;border-top:1px solid #21262d;padding-top:8px}}
.asp-stats{{margin-top:8px;font-size:11px;border-top:1px solid #21262d;padding-top:6px}}
/* BADGES */
.badge{{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:bold;letter-spacing:.03em}}
.tema-badge{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px}}
.tend-up{{color:#3fb950;font-size:11px}}.tend-down{{color:#f85149;font-size:11px}}.tend-flat{{color:#484f58;font-size:11px}}
/* NOTICIAS */
.noticia-item{{padding:6px 0;border-bottom:1px solid #21262d}}
.noticia-item:last-child{{border-bottom:none}}
.noticia-meta{{font-size:10px;color:#484f58;text-transform:uppercase;display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.noticia-titulo{{font-size:12px;color:#c9d1d9;line-height:1.4;display:block;margin-top:2px}}
.noticia-titulo:hover{{color:#58a6ff}}
.noticia-vacia{{font-size:11px;color:#484f58;font-style:italic;padding:6px 0}}
/* PARTIDOS */
.partido-row{{display:flex;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid #21262d;flex-wrap:wrap}}
.partido-nombre{{font-weight:bold;font-size:13px;width:90px;flex-shrink:0}}
.partido-stats{{margin-left:auto;font-size:11px}}
/* BLOQUES */
.bloque{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:12px;margin-top:8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px}}
/* HEADER */
.header-bar{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:12px 16px;margin-bottom:16px}}
.cursor{{display:inline-block;width:8px;height:13px;background:#3fb950;animation:blink 1s step-end infinite;vertical-align:middle}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
.stat-chips{{display:flex;gap:16px;margin-top:8px;flex-wrap:wrap}}
.chip{{font-size:11px}}.chip .val{{color:#e6edf3;font-weight:bold}}
@media(max-width:640px){{.cards-grid{{grid-template-columns:1fr}}.grid2{{grid-template-columns:1fr}}.partido-row{{flex-direction:column;align-items:flex-start}}}}
</style>
</head>
<body>

<div class="header-bar">
  <div>
    <span class="dim">┌──(</span><span class="g">nicho-analyzer</span><span class="dim">)─[</span><span class="w">~/electoral/zacatecas</span><span class="dim">]</span><br>
    <span class="dim">└─</span><span class="g">$</span> <span class="w">./scoreboard.py --estado zacatecas --año 2027</span><span class="cursor"></span>
  </div>
  <div style="margin-top:10px;">
    <span style="color:#e6edf3;font-size:16px;font-weight:bold;">SCOREBOARD ELECTORAL — ZACATECAS 2027</span><br>
    <span class="dim">{FECHA} {HORA} | elecciones: junio 2027 | gobernador + 58 alcaldías</span>
  </div>
  <div class="stat-chips">
    <div class="chip">entradas minadas: <span class="val">{total_entradas}</span></div>
    <div class="chip">fuentes: <span class="val">{fuentes_unicas}</span></div>
    <div class="chip">aspirantes rastreados: <span class="val">{len(ASPIRANTES)}</span></div>
    <div class="chip">partidos: <span class="val">{len(partidos_data)}</span></div>
  </div>
</div>

<div class="section">
  <div class="section-title">[ ranking de aspirantes — gobernador ]</div>
  <div style="font-size:11px;color:#484f58;margin-bottom:8px;">score = preferencia base + ajuste por momentum mediático del día</div>
  <div class="cards-grid">
    {cards_html}
  </div>
</div>

<div class="section">
  <div class="section-title">[ movimiento de partidos — local → nacional ]</div>
  <div class="bloque">
    {partidos_html}
  </div>
</div>

<div class="section grid2">
  <div>
    <div class="section-title">[ noticias electorales del día ]</div>
    <div class="bloque">
      {nots_gen_html if nots_gen_html else '<div class="noticia-vacia">sin entradas hoy</div>'}
    </div>
  </div>
  <div>
    <div class="section-title">[ conexiones nacional ↔ zacatecas ]</div>
    <div class="bloque">
      {conexiones_html}
    </div>
  </div>
</div>

<div class="section">
  <span class="dim">─────────────────────────────────────────────────────────</span><br>
  <span class="dim">dashboard principal: </span><a href="{BASE_URL}/dashboard.html">/dashboard.html</a>
  <span class="dim"> | repo: </span><a href="https://github.com/ruskigarage-alt/nicho-analyzer">github</a><br>
  <span class="dim">próxima actualización: </span><span class="b">mañana 06:00 UTC</span>
</div>

</body>
</html>"""

os.makedirs(".", exist_ok=True)
with open("scoreboard.html", "w", encoding="utf-8") as f:
    f.write(html)

kb = os.path.getsize("scoreboard.html") / 1024
print(f"✓ scoreboard.html generado — {kb:.1f} KB — {len(ASPIRANTES)} aspirantes — {FECHA}")
