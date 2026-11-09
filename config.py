"""config.py — Paramètres centralisés du projet DataPilot."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # dossier qui contient ce fichier

# --- Moteur LLM (Ollama) ----------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")          # modèle choisi (8 Go)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))        # secondes avant abandon d'un appel
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "8192"))       # taille de la fenêtre de contexte (tokens)

# --- Données ----------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "ecommerce.db"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", BASE_DIR / "data" / "docs"))

# --- Recherche documentaire (RAG) -------------------------------------
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))          # taille d'un morceau de texte (caractères)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))    # chevauchement entre deux morceaux
TOP_K = int(os.getenv("TOP_K", "3"))                      # nombre de morceaux renvoyés par la recherche

# --- Agent ------------------------------------------------------------
MAX_STEPS = int(os.getenv("MAX_STEPS", "5"))                  # nb max de tours outil/LLM par question
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))  # nb d'échanges gardés en mémoire
SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "50"))           # nb max de lignes renvoyées par une requête

# --- Journaux ---------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"