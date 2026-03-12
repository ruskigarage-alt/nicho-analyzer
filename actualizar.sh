#!/bin/bash

echo "=================================="
echo " NICHO ANALYZER — Actualización"
echo " $(date '+%Y-%m-%d %H:%M')"
echo "=================================="

source ~/entornos/nicho-analyzer/bin/activate
cd ~/nicho-analyzer

echo ""
echo "[ 1/5 ] Minando fuentes..."
TMPDIR=~/tmp python3 minador.py

echo ""
echo "[ 2/5 ] Filtrando por relevancia temática..."
python3 filtrador.py

echo ""
echo "[ 3/5 ] Estructurando contenido..."
python3 estructurador.py

echo ""
echo "[ 4/5 ] Tu resumen del día..."
python3 resumidor.py

echo ""
echo "[ 5/5 ] Publicando en GitHub..."
git add .
git commit -m "update $(date +%Y-%m-%d)"
git push

echo ""
echo "✓ Listo — $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
