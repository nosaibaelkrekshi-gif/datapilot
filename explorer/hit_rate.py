"""explorer/hit_rate.py — Mesure de la qualité de la recherche documentaire (hit rate @1 et @3).

Utilisation :
    python explorer/hit_rate.py            -> chunk_size = 500 (valeur de config)
    python explorer/hit_rate.py 300 800    -> compare plusieurs tailles
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from tools import DocSearchTool, load_corpus, load_embedder

JEU_EVAL = [
    ("Combien de jours pour retourner un article ?", "02_politique_retours.md"),
    ("Comment est défini le chiffre d'affaires ?", "01_glossaire_kpi.md"),
    ("Quels sont les critères pour devenir VIP ?", "03_segmentation_clients.md"),
    ("Quelles colonnes contient la table lignes_commande ?", "04_dictionnaire_donnees.md"),
    ("À partir de quel montant la livraison est-elle gratuite ?", "05_livraison.md"),
    ("Peut-on afficher l'email d'un client dans un rapport ?", "06_regles_reporting.md"),
    ("Qu'est-ce qu'un client actif ?", "01_glossaire_kpi.md"),
    ("Les produits de beauté peuvent-ils être retournés ?", "02_politique_retours.md"),
]


def evaluer(tool: DocSearchTool, detail: bool = True) -> tuple[float, float]:
    """Calcule le hit rate @1 et @3 sur JEU_EVAL."""
    hits_1 = hits_3 = 0
    for question, attendu in JEU_EVAL:
        sources = [chunk.source for _, chunk in tool.search(question, k=3)]
        ok_1 = bool(sources) and sources[0] == attendu
        ok_3 = attendu in sources
        hits_1 += ok_1
        hits_3 += ok_3
        if detail:
            print(f"{'OK ' if ok_3 else 'RATÉ'} | @1={'✓' if ok_1 else '✗'} | {question}")
            print(f"       attendu : {attendu} | trouvés : {sources}")
    n = len(JEU_EVAL)
    return hits_1 / n, hits_3 / n


if __name__ == "__main__":
    tailles = [int(x) for x in sys.argv[1:]] or [config.CHUNK_SIZE]
    print("Chargement du modèle d'embeddings (le 1er lancement le télécharge)...")
    embedder = load_embedder(config.EMBEDDING_MODEL)

    for taille in tailles:
        overlap = min(config.CHUNK_OVERLAP, taille // 4)
        chunks = load_corpus(config.DOCS_DIR, chunk_size=taille, overlap=overlap)
        tool = DocSearchTool(chunks, embedder, top_k=config.TOP_K)
        print(f"\n===== chunk_size = {taille} (overlap {overlap}) — {len(chunks)} morceaux =====")
        hr1, hr3 = evaluer(tool, detail=len(tailles) == 1)
        print(f"Hit rate @1 : {hr1:.0%}")
        print(f"Hit rate @3 : {hr3:.0%}")