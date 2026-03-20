# DataMiner - Script de Minería de Datos

Script Python para extraer datos de múltiples fuentes y guardarlos en formato JSON.

## Características

✅ **Web Scraping**: Extrae datos de sitios web  
✅ **API REST**: Obtiene datos de APIs JSON  
✅ **Archivos locales**: Importa CSV y JSON  
✅ **Datos manuales**: Agrega registros directamente  
✅ **Limpieza**: Elimina duplicados  
✅ **Exportación**: Guarda en JSON organizado  

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Opción 1: Script básico
```bash
python data_miner.py
```

### Opción 2: Uso avanzado en Python

```python
from data_miner import DataMiner

# Crear minero de datos
miner = DataMiner(output_dir='datos')

# Minar desde web
miner.minar_desde_url('https://ejemplo.com', 'p')

# Minar desde API
miner.minar_desde_api('https://api.ejemplo.com/datos')

# Minar archivo local
miner.minar_desde_archivo('archivo.csv')

# Agregar datos manualmente
miner.agregar_dato_manual({'nombre': 'John', 'edad': 30})

# Filtrar datos
datos_filtrados = miner.filtrar_datos('nombre', 'John')

# Limpiar duplicados
miner.limpiar_duplicados()

# Guardar
miner.guardar_json('mi_archivo.json')
```

## Métodos disponibles

| Método | Descripción |
|--------|------------|
| `minar_desde_url(url, selector)` | Extrae datos de una página web |
| `minar_desde_api(url, params)` | Obtiene datos más de una API |
| `minar_desde_archivo(ruta)` | Importa datos de CSV/JSON |
| `agregar_dato_manual(dato)` | Añade datos manualmente |
| `filtrar_datos(clave, valor)` | Filtra registros |
| `limpiar_duplicados()` | Elimina duplicados |
| `guardar_json(nombre)` | Exporta a JSON |
| `obtener_resumen()` | Genera resumen de datos |

## Ejemplos

### Ejemplo 1: Web Scraping
```python
miner = DataMiner()
miner.minar_desde_url('https://es.wikipedia.org/wiki/Python', 'p')
miner.guardar_json('wikipedia.json')
```

### Ejemplo 2: API Pública
```python
miner = DataMiner()
miner.minar_desde_api('https://jsonplaceholder.typicode.com/posts')
miner.guardar_json('posts.json')
```

### Ejemplo 3: Datos locales
```python
miner = DataMiner()
miner.minar_desde_archivo('datos.csv')
miner.limpiar_duplicados()
miner.guardar_json('datos_procesados.json')
```

## Estructura de salida JSON

```json
[
  {
    "nombre": "John",
    "edad": 30,
    "fuente": "manual",
    "fecha": "2026-03-17T10:30:45.123456"
  }
]
```

## Notas

- Los datos se guardan con timestamp automático si no es un nombre personalizado
- Todos los registros incluyen la fecha de minería
- Usa User-Agent para web scraping responsable
- Respeta los términos de servicio de sitios y APIs

## Requisitos

- Python 3.7+
- requests
- beautifulsoup4
