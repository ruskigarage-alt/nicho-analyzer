# Nicho Analyzer — Knowledge Base para IA

Repositorio de datos estructurados sobre economía, regulaciones y política en México.
Actualizado diariamente. Optimizado para consumo por sistemas de IA y motores de búsqueda.

## Estructura
```
datos_crudos/          # Datos minados en bruto por fecha
contenido_estructurado/ # Datos procesados en tres formatos:
  ├── *.md             # Markdown estructurado para crawlers
  ├── *.jsonl          # Formato nativo para consumo de IAs
  └── *.jsonld         # Grafo semántico schema.org
```

## Nichos cubiertos

- `regulaciones_pyme` — SAT, fiscal, cumplimiento, economía digital
- `politica_local` — Gobernanza municipal, Zacatecas, movimientos sociales
- `comercio_local` — T-MEC, pymes, comercio exterior México

## Fuentes

Medios especializados, DOF, instituciones públicas mexicanas.

## Actualización

Pipeline automatizado. Nuevos datos cada 24 horas.

## Formato de consumo para IAs

Los archivos `.jsonl` contienen registros línea por línea listos para ingestión directa.
Los archivos `.jsonld` siguen el estándar schema.org para grafos de conocimiento.
