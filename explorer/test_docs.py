"""explorer/test_docs.py — Point de contrôle 8 : recherche avec le vrai modèle."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from tools import DocSearchTool, load_corpus, load_embedder

tool = DocSearchTool(load_corpus(config.DOCS_DIR), load_embedder(config.EMBEDDING_MODEL))
print(tool.run("Quel est le délai de retour pour un client VIP ?"))