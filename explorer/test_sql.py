"""explorer/test_sql.py — Point de contrôle 6 : l'outil SQL en action."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import SQLTool

t = SQLTool("data/ecommerce.db")
print(t.run("SELECT segment, COUNT(*) AS nb FROM clients GROUP BY segment"))
print()
print(t.run("DELETE FROM clients"))
print()
print(t.run("SELECT montant FROM commandes"))