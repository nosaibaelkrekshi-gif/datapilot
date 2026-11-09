"""explorer/embeddings.py — Expérience : la similarité entre phrases."""
from sentence_transformers import SentenceTransformer

m = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
phrases = ["Combien de temps ai-je pour renvoyer un article ?",
           "Le client dispose de 30 jours pour retourner un article.",
           "La livraison standard coûte 4,90 euros."]
v = m.encode(phrases, normalize_embeddings=True)
print("Forme des vecteurs :", v.shape)
print("Matrice de similarité :")
print((v @ v.T).round(2))