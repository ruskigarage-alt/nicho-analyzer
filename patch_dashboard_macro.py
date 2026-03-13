#!/usr/bin/env python3
"""
PARCHE: agrega al generar_dashboard.py la sección MACRO MEXICO
Pega este bloque dentro del HTML, después de [ PRESION MACRO ]
y antes del bloque de noticias.

O ejecuta: python3 patch_dashboard_macro.py
para insertar automáticamente en generar_dashboard.py
"""

BLOQUE_MACRO = '''
<div class="section">
<span class="b">[ MACRO MEXICO — INDICADORES OFICIALES ]</span>
<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">

  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">balance fiscal</div>
    {FILA_DEFICIT}
    {FILA_CONFIANZA}
  </div>

  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">dinero y precios</div>
    {FILA_INFLACION}
    {FILA_TASA}
    {FILA_RESERVAS}
    {FILA_EMBI}
  </div>

</div>
</div>
'''

# ── Leer datos macro del jsonl del día ───────────────────────────
import os, json
from datetime import datetime, timezone

FECHA = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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

def fila(label, titulo_key, sufijo="", verde_si_positivo=True):
    d = macro.get(titulo_key, {})
    val = d.get("valor", "N/D")
    try:
        v = float(val)
        if verde_si_positivo:
            color = "g" if v >= 0 else "r"
        else:
            color = "r" if v >= 0 else "g"
        val_str = f"{v:+.2f}{sufijo}" if v != 0 else f"{v:.2f}{sufijo}"
    except Exception:
        color = "dim"
        val_str = str(val)
    interp = d.get("extra", {}).get("interpretacion", "")
    tag = f' <span style="font-size:10px;color:#484f58;">({interp})</span>' if interp else ""
    return (
        f'<div class="row">'
        f'<span class="dim">{label}</span>'
        f'<span><span class="{color}">{val_str}</span>{tag}</span>'
        f'</div>'
    )

FILA_DEFICIT    = fila("deficit/PIB",   "Deficit fiscal Mexico porcentaje PIB", "%", verde_si_positivo=False)
FILA_CONFIANZA  = fila("confianza",     "Indice confianza macro Mexico",        "pts", verde_si_positivo=True)
FILA_INFLACION  = fila("inflacion",     "Inflacion INPC anual Mexico",           "%", verde_si_positivo=False)
FILA_TASA       = fila("tasa Banxico",  "Tasa objetivo Banxico",                 "%", verde_si_positivo=True)
FILA_RESERVAS   = fila("reservas",      "Reservas internacionales Banxico",      " mmd", verde_si_positivo=True)
FILA_EMBI       = fila("EMBI aprox",    "Riesgo pais EMBI Mexico aproximado",   "pb", verde_si_positivo=False)

bloque_final = BLOQUE_MACRO.format(
    FILA_DEFICIT=FILA_DEFICIT,
    FILA_CONFIANZA=FILA_CONFIANZA,
    FILA_INFLACION=FILA_INFLACION,
    FILA_TASA=FILA_TASA,
    FILA_RESERVAS=FILA_RESERVAS,
    FILA_EMBI=FILA_EMBI,
)

# ── Insertar en generar_dashboard.py ────────────────────────────
TARGET_FILE = "generar_dashboard.py"
MARKER = "# ── Barras macro ───"

if os.path.exists(TARGET_FILE):
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        contenido = f.read()

    if "macro_html" not in contenido:
        insercion = f'''
# ── Bloque macro generado por patch_dashboard_macro.py ──────────
def bloque_macro():
    macro = {{}}
    jsonl = os.path.join("datos_crudos", f"macro_mx_{{FECHA}}.jsonl")
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                    macro[d["titulo"]] = d
                except Exception:
                    pass
    def fila(label, key, suf="", verde=True):
        d = macro.get(key, {{}})
        val = d.get("valor", "N/D")
        try:
            v = float(val)
            color = ("g" if v>=0 else "r") if verde else ("r" if v>=0 else "g")
            vs = f"{{v:+.2f}}{{suf}}"
        except Exception:
            color, vs = "dim", str(val)
        interp = d.get("extra", {{}}).get("interpretacion","")
        tag = f' <span style="font-size:10px;color:#484f58;">({{interp}})</span>' if interp else ""
        return f'<div class="row"><span class="dim">{{label}}</span><span><span class="{{color}}">{{vs}}</span>{{tag}}</span></div>'

    return f"""
<div class="section">
<span class="b">[ MACRO MEXICO — INDICADORES OFICIALES ]</span>
<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">balance fiscal</div>
    {{fila("deficit/PIB","Deficit fiscal Mexico porcentaje PIB","%",verde=False)}}
    {{fila("confianza","Indice confianza macro Mexico","pts",verde=True)}}
  </div>
  <div class="cotiz-block">
    <div style="color:#58a6ff;font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">dinero y precios</div>
    {{fila("inflacion","Inflacion INPC anual Mexico","%",verde=False)}}
    {{fila("tasa Banxico","Tasa objetivo Banxico","%",verde=True)}}
    {{fila("reservas","Reservas internacionales Banxico"," mmd",verde=True)}}
    {{fila("EMBI aprox","Riesgo pais EMBI Mexico aproximado","pb",verde=False)}}
  </div>
</div>
</div>"""

macro_html = bloque_macro()
'''
        # Insertar antes del bloque de noticias
        contenido = contenido.replace(
            "news_economia  = bloque_noticias",
            insercion + "\nnews_economia  = bloque_noticias"
        )
        # Insertar macro_html en el html final
        contenido = contenido.replace(
            "{barras_html}",
            "{barras_html}\"\"\"\n+ macro_html\n+ \"\"\""
        )
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"✓ Parche aplicado a {TARGET_FILE}")
    else:
        print(f"  Parche ya aplicado — omitiendo")
else:
    print(f"  {TARGET_FILE} no encontrado — copia el bloque manualmente")

print("\nBloque HTML listo:")
print(bloque_final[:400] + "...")
