"""explorer/analyse_logs.py — Étape 11 : analyser le journal des appels au LLM.

Utilisation :
    python explorer/analyse_logs.py                 -> statistiques générales
    python explorer/analyse_logs.py "VIP"           -> + trace des appels dont la question contient "VIP"
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

LOG = config.LOG_DIR / "llm_exchanges.jsonl"
logs = pd.read_json(LOG, lines=True, encoding="utf-8")

# 1) Statistiques générales
print(f"Journal : {LOG}")
print(f"Nombre d'appels au LLM : {len(logs)}\n")
print(logs[["duration_s", "prompt_tokens", "completion_tokens"]].describe().round(2))

print("\n--- Chiffres clés pour le carnet ---")
print(f"Durée moyenne d'un appel      : {logs['duration_s'].mean():.2f} s")
print(f"Durée médiane d'un appel      : {logs['duration_s'].median():.2f} s")
print(f"Tokens lus en moyenne / appel : {logs['prompt_tokens'].mean():.0f}")
print(f"Tokens générés en moyenne     : {logs['completion_tokens'].mean():.0f}")
print(f"Question en 3 étapes ≈ {3 * logs['duration_s'].mean():.0f} s d'attente")

# 2) Dernière réponse brute du LLM
print("\n--- Dernière réponse brute du LLM ---")
print(logs.iloc[-1]["answer"])


# 3) Trace détaillée des appels pour une question (pour analyser une erreur)
def question_posee(messages):
    """Renvoie la vraie question de l'utilisateur (pas une OBSERVATION ni un message d'erreur)."""
    for m in reversed(messages):
        if m["role"] == "user" and not m["content"].startswith(("OBSERVATION", "ERREUR", "Tu as atteint")):
            return m["content"]
    return ""


if len(sys.argv) > 1:
    mot = sys.argv[1].lower()
    logs["question"] = logs["messages"].apply(question_posee)
    selection = logs[logs["question"].str.lower().str.contains(mot, regex=False)]
    print(f"\n=== Trace des appels dont la question contient « {sys.argv[1]} » ({len(selection)} appels) ===")
    for _, row in selection.iterrows():
        dernier = row["messages"][-1]["content"].replace("\n", " ")[:150]
        print(f"\n[{row['timestamp']}] question : {row['question']}")
        print(f"  tokens lus : {row['prompt_tokens']} | durée : {row['duration_s']} s")
        print(f"  dernier message reçu : {dernier}")
        print(f"  décision du LLM      : {row['answer'][:250]}")