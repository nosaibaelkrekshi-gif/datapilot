"""explorer/test_chunks.py — Point de contrôle 7 : découpage des documents."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import load_corpus

# 1) Découpage par défaut (500 caractères, chevauchement 100)
chunks = load_corpus("data/docs")
print("Nombre de morceaux (500/100) :", len(chunks))
for c in chunks[5:8]:
    print(c.source, "|", c.section, "|", c.text[:100])

# 2) Question de réflexion 1 : comparer plusieurs tailles
print("\n--- Comparaison des tailles ---")
for size in (200, 500, 1000):
    print(f"chunk_size={size} -> {len(load_corpus('data/docs', chunk_size=size, overlap=50))} morceaux")

# 3) Exemple de morceaux de 200 caractères : restent-ils compréhensibles ?
print("\n--- Exemples de morceaux de 200 caractères ---")
for c in load_corpus("data/docs", chunk_size=200, overlap=50)[10:13]:
    print("-", c.text)