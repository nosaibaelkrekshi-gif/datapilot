"""explorer/test_prompt.py — Point de contrôle 5 : le prompt oriente-t-il vers la bonne action ?"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from llm_client import LLMClient
from prompts import build_system_prompt

# 1) Récupérer automatiquement le schéma de la base
conn = sqlite3.connect(config.DB_PATH)
schema = "\n\n".join(r[0] for r in conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"))
conn.close()

# 2) Construire le system prompt
prompt = build_system_prompt(schema)
llm = LLMClient(config.LLM_MODEL, config.OLLAMA_URL)

# 3) Tester trois questions (action attendue entre parenthèses)
questions = [
    ("Combien de commandes ont été livrées en 2025 ?", "query_database"),
    ("Quelle est la politique de retour pour les clients VIP ?", "search_docs"),
    ("Bonjour, qui es-tu ?", "final_answer"),
]

for question, attendu in questions:
    reponse = llm.chat([{"role": "system", "content": prompt},
                        {"role": "user", "content": question}], json_mode=True)
    try:
        action = json.loads(reponse).get("action")
    except json.JSONDecodeError:
        action = "JSON INVALIDE"
    statut = "OK" if action == attendu else "A AMELIORER"
    print(f"\nQuestion : {question}")
    print(f"Réponse  : {reponse}")
    print(f"Action   : {action} (attendu : {attendu}) -> {statut}")

print(f"\nTaille du prompt : {len(prompt)} caractères, environ {len(prompt) // 4} tokens")