#!/usr/bin/env python3
"""
generar_perfiles_html.py
──────────────────────────────────────────────────
Lee los perfiles JSON de datos_electorales/perfiles/
y genera una página HTML estática por candidato.

Uso:
    python3 generar_perfiles_html.py

Corre DESPUÉS de minar_perfiles.py en actualizar.sh.
Las páginas generadas se publican en GitHub Pages.
"""

import json
import os
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")
PERFILES_DIR = "datos_electorales/perfiles"

PARTY_COLORS = {
    "pan":      {"color": "#4a9eff", "bg": "rgba(0,63,138,0.3)",  "border": "rgba(74,158,255,0.3)"},
    "pri":      {"color": "#ff6b6b", "bg": "rgba(204,0,0,0.2)",   "border": "rgba(255,107,107,0.3)"},
    "morena":   {"color": "#ff6b6b", "bg": "rgba(139,26,26,0.3)", "border": "rgba(255,68,68,0.3)"},
    "ptmorena": {"color": "#ff8c42", "bg": "rgba(139,26,26,0.2)", "border": "rgba(255,140,0,0.3)"},
    "pt":       {"color": "#ff8c00", "bg": "rgba(204,0,0,0.2)",   "border": "rgba(255,140,0,0.3)"},
    "default":  {"color": "#818cf8", "bg": "rgba(99,102,241,0.2)","border": "rgba(129,140,248,0.3)"},
}

CSS_BASE = """
:root {
  --bg: #08090c; --bg2: #0e1017; --bg3: #141620;
  --border: #1e2130; --border2: #2a2f45;
  --text: #6b7280; --text2: #9ca3af; --text3: #e5e7eb;
  --accent: #6366f1; --accent2: #818cf8;
  --font-mono: 'DM Mono', monospace;
  --font-ui: 'Syne', sans-serif;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text2); font-family:var(--font-ui); min-height:100vh; }
.container { max-width:900px; margin:0 auto; padding:32px 24px; }
.breadcrumb { font-family:var(--font-mono); font-size:0.65em; color:var(--text);
  letter-spacing:2px; text-transform:uppercase; margin-bottom:24px; }
.breadcrumb a { color:var(--accent2); text-decoration:none; }
.perfil-header { display:flex; gap:24px; align-items:flex-start; margin-bottom:32px;
  padding:24px; background:var(--bg2); border:1px solid var(--border); }
.perfil-partido-badge { font-family:var(--font-mono); font-size:0.65em; letter-spacing:2px;
  padding:4px 12px; border-radius:2px; display:inline-block; margin-bottom:12px; }
.perfil-nombre { font-size:2em; font-weight:800; color:var(--text3); line-height:1.1; margin-bottom:8px; }
.perfil-cargo { font-family:var(--font-mono); font-size:0.75em; color:var(--text); letter-spacing:2px;
  text-transform:uppercase; }
.wiki-link { font-family:var(--font-mono); font-size:0.65em; color:var(--accent2);
  text-decoration:none; margin-top:12px; display:inline-block; }
.wiki-link:hover { text-decoration:underline; }
.seccion { background:var(--bg2); border:1px solid var(--border); padding:24px; margin-bottom:16px; }
.seccion-titulo { font-family:var(--font-mono); font-size:0.65em; letter-spacing:3px;
  color:var(--text); text-transform:uppercase; margin-bottom:16px;
  padding-bottom:8px; border-bottom:1px solid var(--border); }
.bio-texto { font-size:0.9em; color:var(--text2); line-height:1.7; }
.dato-row { display:flex; gap:16px; padding:8px 0; border-bottom:1px solid var(--bg3); }
.dato-row:last-child { border-bottom:none; }
.dato-label { font-family:var(--font-mono); font-size:0.65em; color:var(--text);
  letter-spacing:1px; text-transform:uppercase; min-width:140px; padding-top:2px; }
.dato-valor { font-size:0.85em; color:var(--text3); flex:1; line-height:1.5; }
.cargo-item { padding:10px 0; border-bottom:1px solid var(--bg3); }
.cargo-item:last-child { border-bottom:none; }
.cargo-titulo { font-size:0.85em; color:var(--text3); font-weight:600; }
.cargo-periodo { font-family:var(--font-mono); font-size:0.65em; color:var(--accent2);
  margin-top:2px; }
.cargo-partido { font-family:var(--font-mono); font-size:0.6em; color:var(--text);
  margin-top:2px; }
.tag-list { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }
.tag { font-family:var(--font-mono); font-size:0.6em; padding:2px 8px;
  background:var(--bg3); border:1px solid var(--border2); color:var(--text); }
.vinculos-list { list-style:none; }
.vinculos-list li { padding:6px 0; border-bottom:1px solid var(--bg3);
  font-size:0.85em; color:var(--text2); }
.vinculos-list li:last-child { border-bottom:none; }
.vinculos-list li::before { content:'→ '; color:var(--accent2); font-family:var(--font-mono); }
.aviso { font-family:var(--font-mono); font-size:0.65em; color:var(--text);
  padding:10px; border:1px dashed var(--border2); margin-top:16px; }
footer { padding-top:24px; border-top:1px solid var(--border); margin-top:32px;
  display:flex; justify-content:space-between; font-family:var(--font-mono);
  font-size:0.65em; color:var(--text); }
footer a { color:var(--accent2); text-decoration:none; }
@media (max-width:600px) {
  .perfil-header { flex-direction:column; }
  .dato-row { flex-direction:column; gap:4px; }
  .dato-label { min-width:unset; }
}
"""

def generar_html_perfil(perfil):
    pid = perfil["id"]
    nombre = perfil["nombre"]
    partido = perfil["partido"]
    pc = perfil.get("partyClass", "default")
    colores = PARTY_COLORS.get(pc, PARTY_COLORS["default"])

    # Educación
    educacion = perfil.get("educacion", [])
    if isinstance(educacion, str):
        educacion = [educacion]
    edu_html = "<br>".join(educacion) if educacion else "No disponible"

    # Cargos
    cargos = perfil.get("cargos", [])
    cargos_detectados = perfil.get("cargos_detectados", [])
    cargos_html = ""
    if cargos:
        for c in cargos:
            cargos_html += f"""
            <div class="cargo-item">
              <div class="cargo-titulo">{c.get('cargo','—')}</div>
              <div class="cargo-periodo">{c.get('periodo','—')}</div>
              <div class="cargo-partido">{c.get('partido','—')}</div>
            </div>"""
    elif cargos_detectados:
        keywords_cargo = ["diputad", "senador", "presidente", "gobernador",
                         "secretari", "regidor", "síndico", "alcalde", "director"]
        cargos_filtrados = [
            c for c in cargos_detectados
            if any(k in c.lower() for k in keywords_cargo) and len(c) < 150
        ]
        for c in (cargos_filtrados or ["No disponible"])[:6]:
            cargos_html += f"""
            <div class="cargo-item">
              <div class="cargo-titulo">{c}</div>
            </div>"""
    else:
        cargos_html = '<div class="dato-valor">No disponible</div>'

    # Vínculos
    vinculos = perfil.get("vinculos", [])
    # Separar nombres pegados y filtrar el propio candidato
    def separar_nombres(texto):
        palabras = texto.split()
        nombres = []
        i = 0
        while i < len(palabras) - 1:
            if palabras[i][0].isupper():
                if i+2 < len(palabras) and palabras[i+1][0].isupper() and palabras[i+2][0].isupper():
                    nombres.append(' '.join(palabras[i:i+3]))
                    i += 3
                elif i+1 < len(palabras) and palabras[i+1][0].isupper():
                    nombres.append(' '.join(palabras[i:i+2]))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return nombres if nombres else [texto]

    vinculos_separados = []
    for v in vinculos:
        vinculos_separados.extend(separar_nombres(v))
    vinculos = [v for v in vinculos_separados if perfil["nombre"] not in v and len(v) > 4]
    vinculos_html = ""
    if vinculos:
        vinculos_html = "<ul class='vinculos-list'>"
        for v in vinculos:
            vinculos_html += f"<li>{v}</li>"
        vinculos_html += "</ul>"
    else:
        vinculos_html = '<div class="dato-valor" style="color:var(--text)">Sin vínculos registrados</div>'

    # Wiki link
    wiki_url = perfil.get("fuente_wiki", "")
    wiki_html = f'<a href="{wiki_url}" target="_blank" class="wiki-link">↗ Ver en Wikipedia</a>' if wiki_url else ""

    # Fuente nota
    fuente_nota = "Wikipedia" if wiki_url else "Datos base — sin artículo Wikipedia"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Perfil — {nombre} | Nicho Analyzer</title>
  <meta name="description" content="Perfil político de {nombre}. Trayectoria, cargos, estudios y militancia. Candidato a la gubernatura de Zacatecas 2027.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://ruskigarage-alt.github.io/nicho-analyzer/perfil_{pid}.html">
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>{CSS_BASE}</style>
</head>
<body>
<div class="container">

  <div class="breadcrumb">
    <a href="index.html">nicho-analyzer</a> /
    <a href="radar_electoral_zacatecas.html">radar electoral</a> /
    {pid}
  </div>

  <div class="perfil-header">
    <div style="flex:1">
      <div class="perfil-partido-badge" style="color:{colores['color']};background:{colores['bg']};border:1px solid {colores['border']}">
        {partido}
      </div>
      <div class="perfil-nombre">{nombre}</div>
      <div class="perfil-cargo">{perfil.get('cargo_actual','—')}</div>
      {wiki_html}
    </div>
  </div>

  <!-- BIO -->
  <div class="seccion">
    <div class="seccion-titulo">◈ Semblanza</div>
    <div class="bio-texto">{perfil.get('bio_corta','No disponible')}</div>
  </div>

  <!-- DATOS GENERALES -->
  <div class="seccion">
    <div class="seccion-titulo">◈ Datos generales</div>
    <div class="dato-row">
      <div class="dato-label">Nacimiento</div>
      <div class="dato-valor">{perfil.get('nacimiento','—')}</div>
    </div>
    <div class="dato-row">
      <div class="dato-label">Estudios</div>
      <div class="dato-valor">{edu_html}</div>
    </div>
    <div class="dato-row">
      <div class="dato-label">Partido actual</div>
      <div class="dato-valor">{perfil.get('partido_actual','—')}</div>
    </div>
    <div class="dato-row">
      <div class="dato-label">Militancia desde</div>
      <div class="dato-valor">{perfil.get('militancia_desde','—')}</div>
    </div>
  </div>

  <!-- TRAYECTORIA -->
  <div class="seccion">
    <div class="seccion-titulo">◈ Trayectoria política</div>
    {cargos_html}
  </div>

  <!-- VÍNCULOS -->
  <div class="seccion">
    <div class="seccion-titulo">◈ Vínculos políticos</div>
    {vinculos_html}
  </div>

  <div class="aviso">
    Datos obtenidos de fuentes públicas ({fuente_nota}). Última actualización: {FECHA}.
    Si detectas un error, puedes reportarlo al repositorio.
  </div>

  <footer>
    <div>
      <a href="radar_electoral_zacatecas.html">← RADAR ELECTORAL</a> &nbsp;|&nbsp;
      <a href="index.html">INICIO</a>
    </div>
    <div>NICHO ANALYZER — ZACATECAS, MÉXICO &nbsp;|&nbsp; CC BY 4.0</div>
  </footer>

</div>
</body>
</html>"""
    return html


def main():
    print(f"\n=== GENERANDO PÁGINAS DE PERFIL — {FECHA} ===")

    # Cargar perfiles
    archivos = [f for f in os.listdir(PERFILES_DIR)
                if f.endswith(".json") and f != "indice.json"]

    if not archivos:
        print("⚠ No hay perfiles JSON. Corre minar_perfiles.py primero.")
        return

    generados = 0
    for archivo in archivos:
        ruta = os.path.join(PERFILES_DIR, archivo)
        with open(ruta, encoding="utf-8") as f:
            perfil = json.load(f)

        html = generar_html_perfil(perfil)
        nombre_html = f"perfil_{perfil['id']}.html"

        with open(nombre_html, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  ✓ {nombre_html}")
        generados += 1

    print(f"\n✓ {generados} páginas generadas")
    print(f"  Agrega los enlaces en radar_electoral_zacatecas.html")
    print(f"  Ejemplo: <a href='perfil_saul_monreal.html'>Saúl Monreal</a>")


if __name__ == "__main__":
    main()
