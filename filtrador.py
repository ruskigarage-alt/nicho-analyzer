from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# ─────────────────────────────────────────
# DEFINICIÓN DE NICHOS — qué debe contener cada uno
# Mientras más específicas las frases, mejor el filtro
# ─────────────────────────────────────────
DEFINICIONES_NICHO = {
    "regulaciones_pyme": [
        "SAT impuestos fiscalidad México",
        "regulación pequeñas empresas México",
        "cumplimiento fiscal freelancers",
        "CFDI facturación electrónica",
        "crédito financiamiento pymes México",
        "comercio exterior regulación México",
        "T-MEC reglas comercio",
        "inflación economía México",
        "banca fintech regulación México",
    ],
    "politica_local": [
        "gobierno municipal México",
        "política Zacatecas",
        "elecciones locales México",
        "movimientos sociales comunidades",
        "minería conflictos comunidades México",
    ],
    "politica_local_bajio": [
        "Zacatecas gobierno municipal estado",
        "Aguascalientes política local gobierno",
        "San Luis Potosí política gobernador",
        "minería comunidades centro norte México",
        "seguridad pública Zacatecas CJNG crimen",
        "elecciones municipales Zacatecas SLP Aguascalientes",
        "presupuesto obras públicas municipios",
        "movimientos sociales campesinos región",
        "migración Zacatecas San Luis remesas",
        "economía local agrícola minera bajío",
        "David Monreal gobernador Zacatecas",
        "corrupción transparencia municipios",
    ],
    "politica_local_bajio": [
        "Zacatecas gobierno municipal estado",
        "Aguascalientes política local gobierno",
        "San Luis Potosí política gobernador",
        "minería comunidades centro norte México",
        "seguridad pública Zacatecas CJNG crimen",
        "elecciones municipales Zacatecas SLP Aguascalientes",
        "presupuesto obras públicas municipios",
        "movimientos sociales campesinos región",
        "migración Zacatecas San Luis remesas",
        "economía local agrícola minera bajío",
        "David Monreal gobernador Zacatecas",
        "corrupción transparencia municipios",
    ],
    "geopolitica": [
        "petroleo crudo precios mercados energia",
        "minerales raros tierras raras cadena suministro",
        "aranceles comercio guerra comercial",
        "alianzas militares estrategicas OTAN",
        "movimiento buques estrecho canal maritimo Ormuz Suez",
        "reserva federal tasas interes Powell inflacion",
        "sanciones economicas geopolitica",
        "China Estados Unidos tension comercial",
        "Rusia Europa gas energia guerra",
        "impacto Mexico latinoamerica economia global",
        "oil prices energy markets war",
        "Federal Reserve interest rates inflation",
        "trade tariffs sanctions geopolitics",
        "strait hormuz shipping oil tanker",
        "China US trade war supply chain",
        "Iran war Israel military strike",
        "rare earth minerals strategic resources",
        "NATO alliance military strategy",
        "Russia Ukraine war energy Europe",
        "Bloomberg markets financial economy",
    ],
}

UMBRAL = 0.46  # similitud mínima para aceptar una entrada

def filtrar_entradas(entradas, nicho):
    if nicho not in DEFINICIONES_NICHO:
        return entradas, []

    definicion = DEFINICIONES_NICHO[nicho]
    emb_definicion = modelo.encode(definicion)

    aceptadas = []
    rechazadas = []

    for entrada in entradas:
        texto = f"{entrada['titulo']}. {entrada.get('resumen', '')}"
        emb_entrada = modelo.encode([texto])
        similitudes = cosine_similarity(emb_entrada, emb_definicion)[0]
        score_max = float(similitudes.max())
        entrada["relevancia_score"] = round(score_max, 4)

        if score_max >= UMBRAL:
            aceptadas.append(entrada)
        else:
            rechazadas.append(entrada)

    return aceptadas, rechazadas


# Cargar datos crudos
archivo = f"datos_crudos/minado_{FECHA}.json"
with open(archivo, "r", encoding="utf-8") as f:
    datos = json.load(f)

# Agrupar por nicho
por_nicho = {}
for fuente in datos:
    nicho = fuente["nicho"]
    if nicho not in por_nicho:
        por_nicho[nicho] = []
    if fuente["tipo"] == "rss":
        for entrada in fuente["entradas"]:
            entrada["fuente_nombre"] = fuente["fuente"]
            por_nicho[nicho].append(entrada)

# Filtrar y reportar
print(f"\nFILTRADO TEMÁTICO — {FECHA}")
print("=" * 50)

resultado_filtrado = {}

for nicho, entradas in por_nicho.items():
    aceptadas, rechazadas = filtrar_entradas(entradas, nicho)
    resultado_filtrado[nicho] = aceptadas

    print(f"\n▶ {nicho}")
    print(f"  Total:     {len(entradas)}")
    print(f"  Aceptadas: {len(aceptadas)}")
    print(f"  Rechazadas: {len(rechazadas)}")

    if rechazadas:
        print(f"\n  Entradas descartadas:")
        for r in rechazadas:
            print(f"    ✗ [{r['relevancia_score']}] {r['titulo'][:60]}...")

    if aceptadas:
        print(f"\n  Entradas aceptadas:")
        for a in aceptadas:
            print(f"    ✓ [{a['relevancia_score']}] {a['titulo'][:60]}...")

# Guardar datos filtrados
os.makedirs("datos_filtrados", exist_ok=True)
archivo_salida = f"datos_filtrados/filtrado_{FECHA}.json"
with open(archivo_salida, "w", encoding="utf-8") as f:
    json.dump(resultado_filtrado, f, ensure_ascii=False, indent=2)

print(f"\n✓ Datos filtrados guardados en: {archivo_salida}")
