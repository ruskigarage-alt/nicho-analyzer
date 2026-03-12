from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import numpy as np
import matplotlib.pyplot as plt

modelo = SentenceTransformer('all-MiniLM-L6-v2')

nichos = {
    "politica_local": [
        "gobernanza municipal Zacatecas",
        "presupuesto participativo comunidades rurales",
        "movimientos sociales mineria Zacatecas",
        "cacicazgo politico regional Mexico",
        "elecciones locales y clientelismo",
        "transparencia gobierno municipal Mexico",
        "conflictos por agua en municipios rurales",
        "organizaciones civiles vs gobierno local",
        "migracion y politica local Zacatecas",
        "economia politica de presidentes municipales",
        "financiamiento de campanas locales Mexico",
        "partidos politicos en municipios pequenos",
        "corrupcion en obras publicas municipales",
        "participacion ciudadana en cabildos",
        "seguridad publica y politica municipal",
        "relacion gobierno estatal vs municipal",
        "liderazgos comunitarios indigenas Mexico",
        "gestion de recursos naturales comunidades",
        "politica educativa nivel municipal",
        "programas sociales federales y politica local",
        "medios locales y poder politico",
        "redes clientelares en zonas rurales",
        "autonomia municipal en Mexico",
        "conflictos electorales municipios marginados",
        "impacto minero en comunidades Zacatecas",
    ],
    "regulaciones_pyme": [
        "cumplimiento fiscal freelancers Mexico",
        "regulacion IMSS trabajadores independientes",
        "contratos informales consecuencias legales",
        "SAT economia digital Mexico",
        "facturacion CFDI pequenos negocios",
        "regimen simplificado de confianza Mexico",
        "obligaciones fiscales personas morales pequenas",
        "deduccion de gastos freelancers Mexico",
        "apertura de negocio tramites municipales",
        "regulacion comercio electronico Mexico",
        "proteccion de datos personales pymes",
        "contratos de prestacion de servicios Mexico",
        "propiedad intelectual emprendedores mexicanos",
        "regulacion importacion pequenos comerciantes",
        "normativa sanitaria negocios alimentos Mexico",
        "seguro social socios empresas familiares",
        "fusion y escision sociedades pequenas Mexico",
        "resolucion de disputas comerciales pymes",
        "financiamiento gobierno pymes Mexico",
        "regulacion plataformas digitales trabajadores",
        "obligaciones contables microempresas Mexico",
        "registro de marca pequenos negocios Mexico",
        "retencion de impuestos honorarios Mexico",
        "regimen de incorporacion fiscal transicion",
        "multas y sanciones SAT microempresas",
    ],
}

print("Calculando embeddings...\n")

for nombre, conceptos in nichos.items():
    embeddings = modelo.encode(conceptos)
    matriz = cosine_similarity(embeddings)

    np.fill_diagonal(matriz, 0)
    similitud = matriz.sum() / (len(conceptos) * (len(conceptos) - 1))
    score = 1 - similitud
    print("=" * 50)
    print("NICHO: {} | Score global: {:.4f}".format(nombre, score))
    print("=" * 50)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(embeddings)

    for i in range(5):
        miembros = [conceptos[j] for j in range(len(conceptos)) if clusters[j] == i]
        if len(miembros) > 1:
            emb_cluster = modelo.encode(miembros)
            mat_cluster = cosine_similarity(emb_cluster)
            np.fill_diagonal(mat_cluster, 0)
            sim_interna = mat_cluster.sum() / (len(miembros) * (len(miembros) - 1))
            hueco = 1 - sim_interna
            print("  Cluster {} (hueco={:.4f}):".format(i + 1, hueco))
            for m in miembros:
                print("    - {}".format(m))

    fig, ax = plt.subplots(figsize=(12, 10))
    np.fill_diagonal(matriz, 1)
    im = ax.imshow(matriz, cmap='RdYlGn', vmin=0, vmax=1)
    ax.set_xticks(range(len(conceptos)))
    ax.set_yticks(range(len(conceptos)))
    ax.set_xticklabels(conceptos, rotation=90, fontsize=7)
    ax.set_yticklabels(conceptos, fontsize=7)
    plt.colorbar(im, ax=ax, label='Similitud semantica')
    plt.title("Mapa de calor - {}".format(nombre))
    plt.tight_layout()
    plt.savefig("calor_{}.png".format(nombre))
    print("  Mapa guardado: calor_{}.png\n".format(nombre))

print("Listo.")
