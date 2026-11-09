"""explorer/test_memoire.py — Le LLM se souvient-il grâce à Conversation ?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from llm_client import LLMClient, Conversation

client = LLMClient(config.LLM_MODEL, config.OLLAMA_URL)

# 1) SANS mémoire : deux appels indépendants
client.chat([{"role": "user", "content": "Je m'appelle Lina."}])
sans = client.chat([{"role": "user", "content": "Comment je m'appelle ?"}])
print("SANS mémoire :", sans)
print("-" * 60)

# 2) AVEC mémoire : on renvoie l'historique à chaque appel
conv = Conversation(
    "Tu es un assistant. Réponds en français, en une phrase. "
    "Utilise les informations que l'utilisateur t'a données plus tôt dans la conversation.",
    max_turns=6,
)
conv.add_user("Je m'appelle Lina.")
conv.add_assistant(client.chat(conv.messages()))
conv.add_user("Comment je m'appelle ?")

print("Messages envoyés au LLM :")
for m in conv.messages():
    print(f"  [{m['role']}] {m['content']}")
print("-" * 60)

avec = client.chat(conv.messages())
print("AVEC mémoire :", avec)
print("Tokens estimés :", conv.estimated_tokens())