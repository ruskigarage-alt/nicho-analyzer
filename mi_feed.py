import json
import os
from datetime import datetime

os.makedirs("mi_feed", exist_ok=True)
FEED_FILE = "mi_feed/entradas.json"

# Cargar entradas existentes
if os.path.exists(FEED_FILE):
    with open(FEED_FILE, "r", encoding="utf-8") as f:
        entradas = json.load(f)
else:
    entradas = []

# ─────────────────────────────────────────
# CAPTURA INTERACTIVA
# ─────────────────────────────────────────
print("\n=== MI FEED PERSONAL ===")
print("Agrega una nueva entrada. Ctrl+C para cancelar.\n")

print("Nichos disponibles:")
print("  1. politica_local_bajio")
print("  2. regulaciones_pyme")
print("  3. geopolitica")
print("  4. habilidades_tacitas")

opcion = input("\nNicho (1-4): ").strip()
nichos = {
    "1": "politica_local_bajio",
    "2": "regulaciones_pyme",
    "3": "geopolitica",
    "4": "habilidades_tacitas"
}
nicho = nichos.get(opcion, "general")

titulo = input("Título: ").strip()
fuente = input("Fuente (ej: NTR Zacatecas, Imagen Zacatecas): ").strip()
url_original = input("URL original (opcional, Enter para omitir): ").strip()

print("\nPega el texto (termina con una línea que solo diga FIN):")
lineas = []
while True:
    linea = input()
    if linea.strip() == "FIN":
        break
    lineas.append(linea)
texto = "\n".join(lineas)

print("\nTu análisis/contexto (termina con FIN):")
print("(Lo que tú agregas — conexiones, impacto local, lo no escrito)")
analisis = []
while True:
    linea = input()
    if linea.strip() == "FIN":
        break
    analisis.append(linea)
contexto_local = "\n".join(analisis)

# Crear entrada
entrada = {
    "id": len(entradas) + 1,
    "titulo": titulo,
    "fuente": fuente,
    "url_original": url_original,
    "nicho": nicho,
    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "texto": texto,
    "contexto_local": contexto_local,
    "autor": "ruskigarage-alt"
}

entradas.append(entrada)

# Guardar JSON
with open(FEED_FILE, "w", encoding="utf-8") as f:
    json.dump(entradas, f, ensure_ascii=False, indent=2)

# Generar RSS válido
rss = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Nicho Analyzer — Feed Personal</title>
    <link>https://github.com/ruskigarage-alt/nicho-analyzer</link>
    <description>Análisis local de política, economía y geopolítica desde Zacatecas, México</description>
    <language>es-mx</language>
    <lastBuildDate>{fecha}</lastBuildDate>
'''.format(fecha=datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"))

for e in reversed(entradas[-20:]):  # últimas 20 entradas
    rss += '''    <item>
      <title><![CDATA[{titulo}]]></title>
      <description><![CDATA[{texto}

CONTEXTO LOCAL: {contexto}]]></description>
      <pubDate>{fecha}</pubDate>
      <dc:creator>{autor}</dc:creator>
      <category>{nicho}</category>
      {link}
    </item>
'''.format(
        titulo=e["titulo"],
        texto=e["texto"][:500],
        contexto=e["contexto_local"][:300],
        fecha=e["fecha"],
        autor=e["autor"],
        nicho=e["nicho"],
        link=f'<link>{e["url_original"]}</link>' if e["url_original"] else ""
    )

rss += '''  </channel>
</rss>'''

with open("mi_feed/feed.xml", "w", encoding="utf-8") as f:
    f.write(rss)

print(f"\n✓ Entrada guardada: #{entrada['id']} — {titulo}")
print(f"✓ Feed actualizado: mi_feed/feed.xml")
print(f"✓ Total entradas en tu feed: {len(entradas)}")
print(f"\nPublica con: git add . && git commit -m 'feed: {titulo[:40]}' && git push")
