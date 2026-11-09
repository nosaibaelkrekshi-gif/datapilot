"""tools.py — Les outils de l'agent : SQL (partie 1) et recherche documentaire (parties 2 et 3)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Mots-clés interdits : tout ce qui pourrait modifier la base ou sa structure
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


# ======================================================================
# Étape 6 — L'outil SQL sécurisé
# ======================================================================
class SQLValidationError(ValueError):
    """Requête refusée avant exécution."""


def validate_sql(sql: str) -> str:
    """Nettoie la requête et lève SQLValidationError si elle est dangereuse ou invalide."""
    cleaned = sql.strip().rstrip(";").strip()
    # Retirer les balises de code markdown ```sql ... ```
    cleaned = re.sub(r"^```(?:sql)?|```$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.rstrip(";").strip()

    # Refus 1 : requête vide
    if not cleaned:
        raise SQLValidationError("la requête est vide.")
    # Refus 2 : plusieurs ordres SQL (un « ; » au milieu)
    if ";" in cleaned:
        raise SQLValidationError("une seule requête SQL est autorisée à la fois.")
    # Refus 3 : doit commencer par SELECT ou WITH
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise SQLValidationError("seules les requêtes SELECT (ou WITH) sont autorisées.")
    # Refus 4 : mot-clé interdit
    match = FORBIDDEN.search(cleaned)
    if match:
        raise SQLValidationError(f"mot-clé interdit : {match.group(1).upper()}.")

    return cleaned


def format_results(columns: list[str], rows: list[tuple], truncated: bool = False) -> str:
    """Présente le résultat sous forme de tableau markdown lisible par le LLM."""
    if not rows:
        return "La requête n'a renvoyé aucun résultat (0 ligne)."

    def fmt(value):
        if value is None:
            return "NULL"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    lines = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows]

    text = f"{len(rows)} ligne(s) :\n" + "\n".join([header, separator, *lines])
    if truncated:
        text += f"\n(Résultat tronqué : seules les {len(rows)} premières lignes sont affichées.)"
    return text


class SQLTool:
    name = "query_database"
    description = "Exécute UNE requête SQL SELECT (SQLite) sur la base e-commerce."

    def __init__(self, db_path, max_rows: int = 50) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Base introuvable : {self.db_path}. Lancez d'abord : python data/create_db.py")
        self.max_rows = max_rows

    def _connect(self) -> sqlite3.Connection:
        """Connexion en LECTURE SEULE (barrière 1)."""
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def run(self, sql: str, params=()) -> str:
        """Exécute la requête. Ne lève jamais d'exception : renvoie toujours du texte."""
        # Barrière 2 : validation
        try:
            cleaned = validate_sql(sql)
        except SQLValidationError as exc:
            return f"ERREUR : requête refusée — {exc}"

        # Barrières 3 (paramètres) et 4 (limite de lignes)
        try:
            conn = self._connect()
            try:
                cursor = conn.execute(cleaned, params)
                columns = [d[0] for d in cursor.description] if cursor.description else []
                rows = cursor.fetchmany(self.max_rows + 1)
            finally:
                conn.close()
        except sqlite3.Error as exc:
            return f"ERREUR SQL : {exc}. Corrigez la requête et réessayez."

        truncated = len(rows) > self.max_rows
        return format_results(columns, rows[: self.max_rows], truncated=truncated)

    def get_schema(self) -> str:
        """Renvoie les instructions CREATE TABLE de la base."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()
        return "\n\n".join(r[0] for r in rows)



# ======================================================================
# Étape 7 — Découper la documentation
# ======================================================================
@dataclass
class Chunk:
    text: str      # le morceau de texte (préfixé par [Titre — Section])
    source: str    # nom du fichier d'origine
    section: str   # titre de la section


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Découpe un texte en morceaux d'au plus chunk_size caractères, sans couper les mots,
    avec un chevauchement d'environ `overlap` caractères entre deux morceaux."""
    if overlap >= chunk_size:
        raise ValueError("overlap doit être strictement inférieur à chunk_size")
    words = text.split()
    chunks, current, i = [], "", 0
    while i < len(words):
        word = words[i]
        candidate = f"{current} {word}" if current else word
        if not current or len(candidate) <= chunk_size:
            # Le mot rentre (ou le morceau est vide : on accepte même un mot très long)
            current = candidate
            i += 1
        else:
            # Le morceau est plein : on l'enregistre
            chunks.append(current)
            # On repart des `overlap` derniers caractères, sans le premier mot (peut-être coupé)
            tail = current[-overlap:] if overlap > 0 else ""
            current = " ".join(tail.split()[1:])
            # Si même avec le chevauchement le mot ne rentre pas, on repart de zéro
            if current and len(current) + 1 + len(word) > chunk_size:
                current = ""
    if current:
        chunks.append(current)   # le dernier morceau
    return chunks


def chunk_markdown(text: str, source: str, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    """Découpe un document markdown par section ##, puis par taille."""
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source
    chunks = []
    for index, part in enumerate(re.split(r"^##\s+", text, flags=re.MULTILINE)):
        if index == 0:
            # Introduction : on retire la ligne « # Titre »
            section = "Introduction"
            content = re.sub(r"^#\s+.+$", "", part, count=1, flags=re.MULTILINE)
        else:
            # Première ligne = titre de section, le reste = contenu
            section, _, content = part.partition("\n")
            section = section.strip()
        content = content.strip()
        if not content:
            continue
        for piece in chunk_text(content, chunk_size, overlap):
            chunks.append(Chunk(text=f"[{title} — {section}] {piece}",
                                source=source, section=section))
    return chunks


def load_corpus(docs_dir, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    """Charge et découpe tous les fichiers .md du dossier (triés par nom)."""
    files = sorted(Path(docs_dir).glob("*.md"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier .md trouvé dans {docs_dir}")
    chunks = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(text, path.name, chunk_size, overlap))
    return chunks




# ======================================================================
# Étape 8 — Embeddings, FAISS et recherche documentaire
# ======================================================================
class DocSearchTool:
    name = "search_docs"
    description = ("Recherche dans la documentation métier "
                   "(KPI, retours, segmentation, données, livraison, reporting).")

    def __init__(self, chunks: list[Chunk], embedder, top_k: int = 3) -> None:
        import faiss  # import local : l'outil SQL reste utilisable sans FAISS
        self.chunks = chunks
        self.embedder = embedder
        self.top_k = top_k
        vectors = self._embed([c.text for c in chunks])
        # Index FAISS : produit scalaire (= cosinus car les vecteurs sont normalisés)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Transforme une liste de textes en vecteurs normalisés (float32)."""
        vectors = self.embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vectors, dtype="float32")

    def search(self, query: str, k: int | None = None) -> list[tuple[float, Chunk]]:
        """Renvoie les k morceaux les plus proches de la question : [(score, chunk), ...]."""
        k = min(k or self.top_k, len(self.chunks))
        if k <= 0:
            return []
        query_vector = self._embed([query])           # une liste d'UNE question
        scores, ids = self.index.search(query_vector, k)
        return [(float(score), self.chunks[idx])
                for score, idx in zip(scores[0], ids[0]) if idx != -1]

    def run(self, query: str) -> str:
        """Renvoie les passages trouvés, avec leur source, sous forme de texte."""
        results = self.search(query)
        if not results:
            return "Aucun passage pertinent trouvé dans la documentation."
        passages = []
        for rank, (score, chunk) in enumerate(results, start=1):
            passages.append(
                f"[Passage {rank} — source : {chunk.source}, section « {chunk.section} », "
                f"score {score:.2f}]\n{chunk.text}")
        return "\n\n".join(passages)


def load_embedder(model_name: str):
    """Charge le modèle d'embeddings (téléchargé au premier appel)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)