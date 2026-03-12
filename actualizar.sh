#!/bin/bash

echo "=================================="
echo " NICHO ANALYZER — Actualización"
echo " $(date '+%Y-%m-%d %H:%M')"
echo "=================================="

# Activar entorno
source ~/entornos/nicho-analyzer/bin/activate

# Ir al proyecto
cd ~/nicho-analyzer

# Minar
echo ""
echo "[ 1/3 ] Minando fuentes..."
TMPDIR=~/tmp python3 minador.py

# Estructurar
echo ""
echo "[ 2/3 ] Estructurando contenido..."
python3 estructurador.py

# Publicar
echo ""
echo "[ 3/3 ] Publicando en GitHub..."
git add .
git commit -m "update $(date +%Y-%m-%d)"
git push

echo ""
echo "✓ Actualización completa — $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
