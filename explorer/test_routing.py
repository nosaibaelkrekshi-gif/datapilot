"""explorer/test_routing.py — Point de contrôle 9 : le routing avec les vrais outils."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import route_query
from tools import SQLTool

outils = {"query_database": SQLTool("data/ecommerce.db")}

# 1) Outil connu
print(route_query('{"action": "query_database", "input": "SELECT COUNT(*) AS n FROM produits"}', outils))
print()

# 2) Outil inconnu, avec du texte autour du JSON
print(route_query('Voici ma réponse : {"action": "envoyer_email", "input": "x"}', outils).content)
print()

# 3) Question de réflexion 1 : regex gourmande (.*) vs non gourmande (.*?)
texte = '{"action": "x", "input": {"a": 1}}'
print("Gourmande     .*  :", re.search(r"\{.*\}", texte).group(0))
print("Non gourmande .*? :", re.search(r"\{.*?\}", texte).group(0))