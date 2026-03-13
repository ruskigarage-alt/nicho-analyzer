#!/bin/bash
echo "=================================="
echo " NICHO ANALYZER — Actualización"
echo " $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
source ~/entornos/nicho-analyzer/bin/activate
cd ~/nicho-analyzer
# ─────────────────────────────────────────
# PASO 1 — MINADO AUTOMÁTICO
# ─────────────────────────────────────────
echo ""
echo "[ 1/5 ] Minando fuentes..."
TMPDIR=~/tmp python3 minador.py
TMPDIR=~/tmp python3 minador_economico.py
TMPDIR=~/tmp python3 minador_global.py
TMPDIR=~/tmp python3 minador_electoral.py
echo ""
echo "[ 2/5 ] Filtrando por relevancia temática..."
python3 filtrador.py 2>/dev/null
echo ""
echo "[ 3/5 ] Estructurando contenido..."
python3 estructurador.py
python3 sitemap.py
python3 generar_indices.py
python3 generar_dataset.py
python3 generar_feed_json.py
python3 generar_feed_nichos.py
python3 minador_macro_mx.py
python3 minador_macro_mx.py
python3 generar_dashboard.py
python3 generar_scoreboard.py
# ─────────────────────────────────────────
# PASO 2 — TU RESUMEN
# ─────────────────────────────────────────
echo ""
echo "[ 4/5 ] Resumen del día..."
python3 resumidor.py
# ─────────────────────────────────────────
# PASO 3 — TU OPINIÓN (opcional)
# ─────────────────────────────────────────
echo ""
echo "================================================"
echo " ¿Quieres agregar análisis a alguna noticia?"
echo " Esto enriquece tu feed con tu contexto local."
echo "================================================"
read -p " (s/n): " respuesta
if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
    echo ""
    echo "Cuántas entradas quieres agregar?"
    read -p "(número, Enter para 1): " cantidad
    cantidad=${cantidad:-1}
    for i in $(seq 1 $cantidad); do
        echo ""
        echo "─── Entrada $i de $cantidad ───"
        python3 mi_feed.py
    done
fi
# ─────────────────────────────────────────
# PASO 4 — NOTICIAS LOCALES
# ─────────────────────────────────────────
echo ""
echo "================================================"
echo " ¿Tienes noticias locales para agregar?"
echo " (Zacatecas, SLP, Aguascalientes)"
echo "================================================"
read -p " (s/n): " respuesta_local
if [ "$respuesta_local" = "s" ] || [ "$respuesta_local" = "S" ]; then
    echo ""
    echo "Cuántas noticias locales tienes?"
    read -p "(número, Enter para 1): " cantidad_local
    cantidad_local=${cantidad_local:-1}
    for i in $(seq 1 $cantidad_local); do
        echo ""
        echo "─── Noticia local $i de $cantidad_local ───"
        python3 mi_feed.py
    done
fi
# ─────────────────────────────────────────
# PASO 5 — PUBLICAR TODO
# ─────────────────────────────────────────
echo ""
echo "[ 5/5 ] Publicando en GitHub..."
git add .
git commit -m "update $(date +%Y-%m-%d)"
git push
echo ""
echo "✓ Listo — $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
