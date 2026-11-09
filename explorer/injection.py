"""explorer/injection.py — Démonstration du danger de l'injection SQL."""
import sqlite3

conn = sqlite3.connect("data/ecommerce.db")
saisie = "VIP' OR '1'='1"

# DANGEREUX : la saisie est collée dans le texte SQL (f-string)
print("Avec f-string   :", conn.execute(
    f"SELECT COUNT(*) FROM clients WHERE segment = '{saisie}'").fetchone())

# SÛR : la saisie est passée comme paramètre (?)
print("Avec paramètre ? :", conn.execute(
    "SELECT COUNT(*) FROM clients WHERE segment = ?", (saisie,)).fetchone())