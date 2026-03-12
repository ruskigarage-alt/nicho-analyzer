import os
from datetime import datetime

BASE_URL = "https://ruskigarage-alt.github.io/nicho-analyzer"
FECHA = datetime.now().strftime("%Y-%m-%d")

urls = []

# Páginas principales
urls.append({"loc": f"{BASE_URL}/", "priority": "1.0"})
urls.append({"loc": f"{BASE_URL}/contenido_estructurado/", "priority": "0.9"})
urls.append({"loc": f"{BASE_URL}/mi_feed/feed.xml", "priority": "0.9"})

# Archivos de contenido estructurado
for archivo in sorted(os.listdir("contenido_estructurado")):
    if archivo.endswith(('.md', '.jsonl', '.jsonld')):
        urls.append({
            "loc": f"{BASE_URL}/contenido_estructurado/{archivo}",
            "priority": "0.8"
        })

# Generar XML
xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

for url in urls:
    xml += '  <url>\n'
    xml += f'    <loc>{url["loc"]}</loc>\n'
    xml += f'    <lastmod>{FECHA}</lastmod>\n'
    xml += f'    <priority>{url["priority"]}</priority>\n'
    xml += '  </url>\n'

xml += '</urlset>'

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(xml)

print(f"✓ Sitemap generado con {len(urls)} URLs")
