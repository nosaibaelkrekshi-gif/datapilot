"""explorer/premier_appel.py — Premier appel HTTP à Ollama.

Utilisation :
    python explorer/premier_appel.py      -> expérience 0 (appel de base)
    python explorer/premier_appel.py 1    -> expérience 1 (system "réponds en anglais")
    python explorer/premier_appel.py 2    -> expérience 2 (mode JSON)
    python explorer/premier_appel.py 0    -> expérience 3 (à lancer avec Ollama arrêté)
"""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pour importer config
import config

# Numéro de l'expérience lu dans le terminal (0 par défaut)
EXPERIENCE = int(sys.argv[1]) if len(sys.argv) > 1 else 0

messages = []

# Expérience 1 : on ajoute une consigne "system"
if EXPERIENCE == 1:
    messages.append({"role": "system", "content": "Tu réponds uniquement en anglais."})

# Message de l'utilisateur
if EXPERIENCE == 2:
    messages.append({"role": "user", "content": "Donne le nom et la capitale de trois pays."})
else:
    messages.append({"role": "user", "content": "Explique en une phrase ce qu'est un panier moyen."})

# Corps de la requête envoyée à Ollama
payload = {
    "model": config.LLM_MODEL,
    "messages": messages,
    "stream": False,
    "options": {"temperature": config.LLM_TEMPERATURE},
}

# Expérience 2 : on force une réponse au format JSON
if EXPERIENCE == 2:
    payload["format"] = "json"

# Envoi de la requête et mesure du temps
debut = time.perf_counter()
reponse = requests.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=120)
duree = time.perf_counter() - debut

data = reponse.json()

# Affichage des résultats
print(f"Expérience     : {EXPERIENCE}")
print(f"Code HTTP      : {reponse.status_code}")
print(f"Réponse        : {data['message']['content']}")
print(f"Tokens lus     : {data.get('prompt_eval_count')}")
print(f"Tokens générés : {data.get('eval_count')}")
print(f"Durée          : {duree:.2f} s")
