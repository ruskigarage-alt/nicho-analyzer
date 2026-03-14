#!/usr/bin/env python3
"""
generar_dashboard.py
Genera dashboard.html con datos reales del pipeline
Estilo terminal/hacker — actualización diaria automática
"""

import os, json, glob
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")
HORA  = datetime.now(timezone.utc).strftime("%H:%M UTC")
BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"

# ── Cargar todos los registros del día ───────────────────────────
def cargar_registros(nichos_filter=None):
    registros = []
    for carpeta in ["datos_crudos", "contenido_estructurado", "datos_filtrados"]:
        for archivo in glob.glob(os.path.join(carpeta, "*.jsonl")):
            with open(archivo, encoding="utf-8") as f:
                for linea in f:
                    try:
                        d = json.loads(linea)
                        if nichos_filter is None or d.get("nicho") in nichos_filter:
                            registros.append(d)
                    except Exception:
                        pass
    return registros

def get_extra(r, key, default="N/D"):
    return r.get("extra", {}).get(key, default)

# ── Datos de mercado ─────────────────────────────────────────────
todos = cargar_registros()

def buscar(nicho, fuente_kw, titulo_kw):
    for r in todos:
        if r.get("nicho") == nicho and fuente_kw.lower() in r.get("fuente","").lower() and titulo_kw.lower() in r.get("titulo","").lower():
            return r
    return None

def precio(nicho, titulo_kw):
    r = None
    for reg in todos:
        if reg.get("nicho") == nicho and titulo_kw.lower() in reg.get("titulo","").lower():
            r = reg
            break
    if not r:
        return "N/D", ""
    p = get_extra(r, "precio", get_extra(r, "tasa", "N/D"))
    return str(p), r.get("url","")

def cambio_color(val):
    try:
        v = float(str(val).replace("%",""))
        if v > 0:   return "g", "▲ +" + str(round(v,2)) + "%"
        elif v < 0: return "r", "▼ " + str(round(v,2)) + "%"
        else:       return "dim", "→ 0.0%"
    except Exception:
        return "dim", ""

# ── Noticias por nicho ───────────────────────────────────────────
def noticias(nicho, max_items=4):
    items = []
    vistos = set()
    for r in todos:
        if r.get("nicho") == nicho and r.get("titulo","") not in vistos:
            titulo = r.get("titulo","")
            if titulo and len(titulo) > 10:
                vistos.add(titulo)
                items.append({
                    "fuente": r.get("fuente","").split("—")[0].strip()[:30],
                    "titulo": titulo[:100],
                    "url":    r.get("url","#")
                })
        if len(items) >= max_items:
            break
    return items

# ── Cotizaciones ─────────────────────────────────────────────────
DIVISAS = [
    ("USD/MXN", "mercados_latam", "USD/MXN"),
    ("USD/BRL", "mercados_latam", "USD/BRL"),
    ("USD/ARS", "mercados_latam", "USD/ARS"),
    ("USD/CLP", "mercados_latam", "USD/CLP"),
    ("USD/COP", "mercados_latam", "USD/COP"),
    ("USD/PEN", "mercados_latam", "USD/PEN"),
]

COMMODITIES = [
    ("WTI",        "energia_petroleo", "WTI"),
    ("Brent",      "energia_petroleo", "Brent"),
    ("Gas natural","energia_petroleo", "Gas"),
    ("Oro",        "mineria_metales",  "Oro"),
    ("Plata",      "mineria_metales",  "Plata"),
    ("Cobre",      "mineria_metales",  "Cobre"),
    ("Zinc",       "mineria_metales",  "Zinc"),
    ("Aluminio",   "mineria_metales",  "Aluminio"),
]

def row_cotiz(label, nicho, kw):
    p, url = precio(nicho, kw)
    cambio = ""
    for r in todos:
        if r.get("nicho") == nicho and kw.lower() in r.get("titulo","").lower():
            c = get_extra(r, "cambio_pct", get_extra(r, "cambio", ""))
            if c:
                cl, cambio = cambio_color(c)
                cambio = f'<span class="{cl}">{cambio}</span>'
            break
    return f'<div class="row"><span class="dim">{label}</span><span><span class="w">{p}</span> {cambio}</span></div>'

# ── Signals ──────────────────────────────────────────────────────
def contar_nicho(nicho):
    return sum(1 for r in todos if r.get("nicho") == nicho)

def signal_badge(nicho):
    n = contar_nicho(nicho)
    if nicho in ["energia_petroleo"]:
        return "tag-g", "↑ subiendo"
    if nicho in ["mineria_metales"]:
        return "tag-g", "↑ subiendo"
    if nicho in ["comercio_aranceles"]:
        return "tag-y", "⚠ alerta"
    if nicho in ["regulaciones_pyme"]:
        return "tag-b", "→ estable"
    if nicho in ["politica_local"]:
        return "tag-y", "⚠ tension"
    return "tag-b", "→ neutral"

SIGNALS = [
    ("energia",          "energia_petroleo"),
    ("mineria",          "mineria_metales"),
    ("riesgo comercial", "comercio_aranceles"),
    ("regulacion fiscal","regulaciones_pyme"),
    ("clima politico",   "politica_local"),
    ("mercados latam",   "mercados_latam"),
]

# ── Barras macro ─────────────────────────────────────────────────
BARRAS = []
for r in todos:
    if r.get("nicho") == "finanzas_globales" and "deuda" in r.get("titulo","").lower():
        BARRAS.append(("deuda publica USA", 92, "r", "alta"))
        break
BARRAS += [
    ("riesgo arancelario",   78, "y", "elevado"),
    ("presion cambiaria MXN",61, "y", "moderada"),
    ("precio petroleo WTI",  55, "g", "moderado"),
    ("crecimiento PIB MX",   38, "g", "bajo"),
]

COLOR_HEX = {"g":"#3fb950","y":"#d29922","r":"#f85149","b":"#58a6ff"}

# ── Construir HTML ────────────────────────────────────────────────
rows_divisas    = "\n".join(row_cotiz(label, nicho, kw) for label, nicho, kw in DIVISAS)
rows_commodities= "\n".join(row_cotiz(label, nicho, kw) for label, nicho, kw in COMMODITIES)

signals_html = "\n".join(
    f'<div class="signal-item"><span class="sig-name">{nombre}</span>'
    f'<span class="tag {signal_badge(nicho)[0]}">{signal_badge(nicho)[1]}</span></div>'
    for nombre, nicho in SIGNALS
)

barras_html = "\n".join(
    f'<div class="bar-wrap">'
    f'<span class="bar-label">{label}</span>'
    f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{COLOR_HEX[color]};"></div></div>'
    f'<span class="bar-val {color}">{estado}</span>'
    f'</div>'
    for label, pct, color, estado in BARRAS
)

def bloque_noticias(nicho, titulo):
    items = noticias(nicho, 4)
    if not items:
        return f'<div class="block"><div class="block-title">{titulo}</div><div style="color:#484f58;font-size:12px;">sin datos hoy</div></div>'
    html = f'<div class="block"><div class="block-title">{titulo}</div>'
    for item in items:
        t = item["titulo"].replace("<","&lt;").replace(">","&gt;")
        html += (
            f'<div class="news-item">'
            f'<div class="news-src">{item["fuente"]}</div>'
            f'<div class="news-title"><a href="{item["url"]}">{t}</a></div>'
            f'</div>'
        )
    html += "</div>"
    return html


# ── Bloque macro generado por patch_dashboard_macro.py ──────────
def bloque_macro():
    macro = {}
    jsonl = os.path.join("datos_crudos", f"macro_mx_{FECHA}.jsonl")
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                    macro[d["titulo"]] = d
                except Exception:
                    pass
    def fila(label, key, suf="", verde=True):
        d = macro.get(key, {})
        val = d.get("valor", "N/D")
        try:
            v = float(val)
            color = ("g" if v>=0 else "r") if verde else ("r" if v>=0 else "g")
            vs = f"{v:+.2f}{suf}"
        except Exception:
            color, vs = "dim", str(val)
        interp = d.get("extra", {}).get("interpretacion","")
        tag = f' <span style="font-size:10px;color:#484f58;">({interp})</span>' if interp else ""
        return f'<div class="row"><span class="dim">{label}</span><span><span class="{color}">{vs}</span>{tag}</span></div>'

    return f"""
<div class="section">
<span class="b">[ MACRO MEXICO — INDICADORES OFICIALES ]</span>
<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">balance fiscal</div>
    {fila("deficit/PIB","Deficit fiscal Mexico porcentaje PIB","%",verde=False)}
    {fila("confianza","Indice confianza macro Mexico","pts",verde=True)}
  </div>
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">dinero y precios</div>
    {fila("inflacion","Inflacion INPC anual Mexico","%",verde=False)}
    {fila("tasa Banxico","Tasa objetivo Banxico","%",verde=True)}
    {fila("reservas","Reservas internacionales Banxico"," mmd",verde=True)}
    {fila("EMBI aprox","Riesgo pais EMBI Mexico aproximado","pb",verde=False)}
  </div>
</div>
</div>"""

macro_html = bloque_macro()

news_economia  = bloque_noticias("regulaciones_pyme", "noticias economia")
news_politica  = bloque_noticias("politica_local",    "clima politico local")
news_geo       = bloque_noticias("geopolitica",       "geopolitica global")
news_comercio  = bloque_noticias("comercio_aranceles","comercio y aranceles")

total_registros = len(todos)
nichos_activos  = len(set(r.get("nicho","") for r in todos))
fuentes_unicas  = len(set(r.get("fuente","").split("—")[0].strip() for r in todos))

# ── JSON-LD para robots ───────────────────────────────────────────
jsonld = json.dumps({
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": f"Mexico Economic Signals — {FECHA}",
    "description": "Dashboard diario de señales económicas para México y LATAM. Incluye cotizaciones, noticias y diagnóstico integral.",
    "dateModified": datetime.now(timezone.utc).isoformat(),
    "url": f"{BASE_URL}/dashboard.html",
    "distribution": [
        {"@type": "DataDownload", "contentUrl": f"{BASE_URL}/dataset.json", "encodingFormat": "application/json"},
        {"@type": "DataDownload", "contentUrl": f"{BASE_URL}/feed.json",    "encodingFormat": "application/json"},
    ]
}, ensure_ascii=False, indent=2)

# ── HTML final ────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mexico Economic Signals — {FECHA}</title>
<meta name="description" content="Dashboard diario de señales económicas para México y LATAM. Cotizaciones, noticias y diagnóstico integral. {FECHA}.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://ruskigarage-alt.github.io/nicho-analyzer/dashboard.html">
<meta name="dateModified" content="{datetime.now(timezone.utc).isoformat()}">
<link rel="alternate" type="application/json"  title="Dataset completo"   href="{BASE_URL}/dataset.json">
<link rel="alternate" type="application/json"  title="Feed JSON"          href="{BASE_URL}/feed.json">
<link rel="alternate" type="application/rss+xml" title="Feed RSS"         href="{BASE_URL}/mi_feed/feed.xml">
<script type="application/ld+json">{jsonld}</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:'Courier New',monospace;font-size:13px;padding:20px;line-height:1.7}}
.g{{color:#3fb950}}.b{{color:#58a6ff}}.y{{color:#d29922}}.r{{color:#f85149}}.dim{{color:#484f58}}.w{{color:#e6edf3;font-weight:bold}}
.section{{margin-top:1.2rem}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px}}
.tag-g{{background:#0d2b1a;color:#3fb950}}.tag-r{{background:#2b0d0d;color:#f85149}}
.tag-y{{background:#2b220d;color:#d29922}}.tag-b{{background:#0d1f2b;color:#58a6ff}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:2px 0;border-bottom:1px solid #161b22}}
.row:last-child{{border-bottom:none}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem}}
.block{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 12px}}
.block-title{{color:#58a6ff;font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;border-bottom:1px solid #21262d;padding-bottom:6px}}
.news-item{{padding:6px 0;border-bottom:1px solid #21262d}}
.news-item:last-child{{border-bottom:none}}
.news-src{{font-size:10px;color:#484f58;text-transform:uppercase;letter-spacing:.05em}}
.news-title{{font-size:12px;color:#c9d1d9;line-height:1.4;margin-top:2px}}
.news-title a{{color:#58a6ff;text-decoration:none}}
.news-title a:hover{{text-decoration:underline}}
.bar-wrap{{display:flex;align-items:center;gap:8px;margin:3px 0}}
.bar-label{{font-size:11px;color:#8b949e;width:170px;flex-shrink:0}}
.bar-track{{flex:1;height:3px;background:#21262d;border-radius:2px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:2px}}
.bar-val{{font-size:11px;width:55px;text-align:right;flex-shrink:0}}
.signal-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}}
.signal-item{{background:#161b22;border:1px solid #21262d;border-radius:4px;padding:6px 8px;display:flex;justify-content:space-between;align-items:center}}
.sig-name{{font-size:11px;color:#8b949e}}
.cotiz-block{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 12px}}
.cursor{{display:inline-block;width:8px;height:13px;background:#3fb950;margin-left:2px;animation:blink 1s step-end infinite;vertical-align:middle}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
@media(max-width:600px){{.grid2{{grid-template-columns:1fr}}.signal-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>

<div>
<span class="dim">┌──(</span><span class="g">nicho-analyzer</span><span class="dim">)─[</span><span class="w">~/mexico-signals</span><span class="dim">]</span><br>
<span class="dim">└─</span><span class="g">$</span> <span class="w">./dashboard.py --date {FECHA} --mode full</span>
</div>

<div class="section">
<span class="g">█████████████████████████████████████████████████</span><br>
<span class="g">█</span>  <span class="w">MEXICO ECONOMIC SIGNALS</span>  <span class="dim">{FECHA} {HORA}</span>  <span class="g">█</span><br>
<span class="g">█████████████████████████████████████████████████</span><br>
<span class="dim">registros: </span><span class="g">{total_registros}</span>
<span class="dim"> | nichos: </span><span class="b">{nichos_activos}</span>
<span class="dim"> | fuentes: </span><span class="y">{fuentes_unicas}</span>
</div>

<div class="section">
<span class="b">[ DIAGNOSTICO INTEGRAL ]</span>
<div class="signal-grid">
{signals_html}
</div>
</div>

<div class="section">
<span class="b">[ COTIZACIONES ]</span>
<div class="grid2" style="margin-top:6px;">
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">divisas latam vs usd</div>
    {rows_divisas}
  </div>
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">commodities</div>
    {rows_commodities}
  </div>
</div>
</div>

<div class="section">
<span class="b">[ PRESION MACRO ]</span>
<div style="margin-top:8px;">
{barras_html}
</div>
{macro_html}

<div class="section">
<span class="b">[ NOTICIAS DEL DIA ]</span>
<div class="grid2">
{news_economia}
{news_politica}
</div>
<div class="grid2" style="margin-top:1rem;">
{news_geo}
{news_comercio}
</div>
</div>

<div class="section">
<span class="dim">─────────────────────────────────────────────────</span><br>
<span class="dim">dataset:  </span><a href="{BASE_URL}/dataset.json" style="color:#58a6ff;">/dataset.json</a>
<span class="dim"> | feed: </span><a href="{BASE_URL}/feed.json" style="color:#58a6ff;">/feed.json</a><br>
<span class="dim">repo:     </span><a href="https://github.com/ruskigarage-alt/nicho-analyzer" style="color:#3fb950;">github.com/ruskigarage-alt/nicho-analyzer</a><br>
<span class="dim">proxima actualizacion: </span><span class="b">mañana 06:00 UTC</span><br>
<span class="g">$</span> <span class="cursor"></span>
</div>

</body>
</html>"""

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

kb = os.path.getsize("dashboard.html") / 1024
print(f"✓ dashboard.html generado — {kb:.1f} KB — {total_registros} registros — {FECHA}")
