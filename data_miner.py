#!/usr/bin/env python3
"""
Script para minar datos de múltiples fuentes y guardarlos en JSON
"""

import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataMiner:
    def __init__(self, output_dir='output'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.data = []
    
    def minar_desde_url(self, url, selector=None):
        """
        Mina datos desde una URL usando web scraping
        
        Args:
            url: URL a minar
            selector: Selector CSS opcional para filtrar elementos
        """
        try:
            logger.info(f"Minando datos desde: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if selector:
                elementos = soup.select(selector)
            else:
                elementos = soup.find_all(['p', 'h1', 'h2', 'h3'])
            
            for elemento in elementos:
                self.data.append({
                    'fuente': 'web',
                    'url': url,
                    'contenido': elemento.get_text(strip=True),
                    'fecha': datetime.now().isoformat()
                })
            
            logger.info(f"✓ Se extrajeron {len(elementos)} elementos")
            
        except Exception as e:
            logger.error(f"Error minando URL: {e}")
    
    def minar_desde_api(self, url, params=None):
        """
        Mina datos desde una API REST
        
        Args:
            url: URL de la API
            params: Parámetros de la solicitud
        """
        try:
            logger.info(f"Minando datos desde API: {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            api_data = response.json()
            
            # Si es una lista, agregar cada elemento
            if isinstance(api_data, list):
                for item in api_data:
                    item['fuente'] = 'api'
                    item['fecha'] = datetime.now().isoformat()
                    self.data.append(item)
            else:
                api_data['fuente'] = 'api'
                api_data['fecha'] = datetime.now().isoformat()
                self.data.append(api_data)
            
            logger.info(f"✓ Se obtuvieron datos de la API")
            
        except Exception as e:
            logger.error(f"Error minando API: {e}")
    
    def minar_desde_archivo(self, ruta_archivo):
        """
        Mina datos desde un archivo CSV o JSON local
        
        Args:
            ruta_archivo: Ruta al archivo
        """
        try:
            logger.info(f"Minando datos desde archivo: {ruta_archivo}")
            ruta = Path(ruta_archivo)
            
            if ruta.suffix == '.json':
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        self.data.extend(datos)
                    else:
                        self.data.append(datos)
            
            elif ruta.suffix == '.csv':
                import csv
                with open(ruta, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row['fuente'] = 'archivo'
                        row['fecha'] = datetime.now().isoformat()
                        self.data.append(row)
            
            logger.info(f"✓ Se importaron datos del archivo")
            
        except Exception as e:
            logger.error(f"Error minando archivo: {e}")
    
    def agregar_dato_manual(self, dato):
        """Agregar un dato manualmente"""
        if isinstance(dato, dict):
            dato['fecha'] = datetime.now().isoformat()
            self.data.append(dato)
        else:
            self.data.append({'contenido': dato, 'fecha': datetime.now().isoformat()})
    
    def filtrar_datos(self, clave, valor):
        """Filtrar datos por clave y valor"""
        return [d for d in self.data if d.get(clave) == valor]
    
    def limpiar_duplicados(self):
        """Eliminar registros duplicados basados en contenido"""
        visto = set()
        datos_limpios = []
        
        for dato in self.data:
            # Crear una firma del dato
            firma = str(dato)
            if firma not in visto:
                visto.add(firma)
                datos_limpios.append(dato)
        
        self.data = datos_limpios
        logger.info(f"✓ Duplicados eliminados. Registros: {len(self.data)}")
    
    def guardar_json(self, nombre_archivo=None):
        """
        Guardar datos en formato JSON
        
        Args:
            nombre_archivo: Nombre del archivo (si no se proporciona, usa timestamp)
        """
        if not nombre_archivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"datos_{timestamp}.json"
        
        ruta_salida = self.output_dir / nombre_archivo
        
        try:
            with open(ruta_salida, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Datos guardados en: {ruta_salida}")
            logger.info(f"  Total de registros: {len(self.data)}")
            return ruta_salida
        
        except Exception as e:
            logger.error(f"Error guardando JSON: {e}")
            return None
    
    def obtener_resumen(self):
        """Obtener resumen de los datos minados"""
        return {
            'total_registros': len(self.data),
            'fuentes': list(set(d.get('fuente', 'desconocida') for d in self.data)),
            'fecha_minado': datetime.now().isoformat()
        }


# Ejemplo de uso
if __name__ == '__main__':
    miner = DataMiner(output_dir='output')
    
    # Ejemplo 1: Minar desde una URL (ejemplo con Wikipedia)
    # miner.minar_desde_url('https://es.wikipedia.org/wiki/Python', 'p')
    
    # Ejemplo 2: Minar desde una API pública
    # miner.minar_desde_api('https://jsonplaceholder.typicode.com/posts', {'_limit': 5})
    
    # Ejemplo 3: Agregar datos manualmente
    miner.agregar_dato_manual({'nombre': 'Dato 1', 'valor': 100})
    miner.agregar_dato_manual({'nombre': 'Dato 2', 'valor': 200})
    miner.agregar_dato_manual({'nombre': 'Dato 3', 'valor': 300})
    
    # Limpiar duplicados (opcional)
    miner.limpiar_duplicados()
    
    # Guardar datos
    miner.guardar_json('datos_ejemplo.json')
    
    # Mostrar resumen
    print("\n" + "="*50)
    print("RESUMEN DE MINERÍA")
    print("="*50)
    resumen = miner.obtener_resumen()
    for clave, valor in resumen.items():
        print(f"{clave}: {valor}")
