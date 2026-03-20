#!/bin/bash
# Script para actualizar el OSINT de Zacatecas
# Uso: ./actualizar.sh [opciones]

# Cambiar al directorio del script
cd "$(dirname "$0")"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 no está instalado"
    exit 1
fi

# Instalar dependencias si no están
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

pip install -r requirements.txt

# Ejecutar el script de OSINT
echo "Ejecutando ZAC-OSINT v2..."
python3 zac_osint_v2.py --run-all

echo "Actualización completada."