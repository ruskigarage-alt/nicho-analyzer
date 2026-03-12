from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import matplotlib.pyplot as plt

# Modelo ligero, corre bien en tu CPU
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# Nichos candidatos con conceptos representativos
nichos = {
    "comercio_local": [
        "exportación desde Zacatecas",
        "productores locales y mercados regionales",
        "regulación aduanal para pequeños exportadores",
        "cadenas de suministro en México central",
        "economía informal y comercio fronterizo",
    ],
    "politica_local": [
        "gobernanza municipal en Zacatecas",
        "presupuesto participativo comunidades rurales",
        "movimientos sociales minería Zacatecas",
        "cacicazgo político regional México",
        "elecciones locales y clientelismo",
    ],
    "habilidades_tacitas": [
        "lo que no enseñan en la universidad",
        "negociación informal en mercados mexicanos",
        "confianza y redes personales en negocios",
        "intuición experta en toma de decisiones",
        "conocimiento no escrito de oficios tradicionales",
    ],
    "regulaciones_pyme": [
        "cumplimiento fiscal freelancers México",
        "regulación IMSS trabajadores independientes",
        "contratos informales y consecuencias legales",
        "SAT y economía digital México",
        "facturación CFDI para pequeños negocios",
    ],
}

# Calcular score de oportunidad por nicho
print("Calculando embeddings...\n")
resultados = {}

for nicho, conceptos in nichos.items():
    embeddings = modelo.encode(conceptos)
    matriz = cosine_similarity(embeddings)
    # Similaridad promedio excluyendo diagonal
    np.fill_diagonal(matriz, 0)
    similitud_promedio = matriz.sum() / (len(conceptos) * (len(conceptos) - 1))
    # Dispersión alta = oportunidad alta
    score_oportunidad = 1 - similitud_promedio
    resultados[nicho] = round(score_oportunidad, 4)
    print(f"{nicho}: score {score_oportunidad:.4f}")

# Visualización
plt.figure(figsize=(10, 5))
plt.barh(list(resultados.keys()), list(resultados.values()), color='steelblue')
plt.xlabel('Score de oportunidad (mayor = más hueco semántico)')
plt.title('Mapa de nichos — densidad semántica')
plt.tight_layout()
plt.savefig('mapa_nichos.png')
print("\nMapa guardado en mapa_nichos.png")
