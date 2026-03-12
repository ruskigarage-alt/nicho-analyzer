#!/bin/bash

echo "=================================="
echo " NICHO ANALYZER — Actualización"
echo " $(date '+%Y-%m-%d %H:%M')"
echo "=================================="

source ~/entornos/nicho-analyzer/bin/activate
cd ~/nicho-analyzer

echo ""
echo "[ 1/4 ] Minando fuentes..."
TMPDIR=~/tmp python3 minador.py

echo ""
echo "[ 2/4 ] Estructurando contenido..."
python3 estructurador.py

echo ""
echo "[ 3/4 ] Tu resumen del día..."
python3 resumidor.py

echo ""
echo "[ 4/4 ] Publicando en GitHub..."
git add .
git commit -m "update $(date +%Y-%m-%d)"
git push

echo ""
echo "✓ Listo — $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
