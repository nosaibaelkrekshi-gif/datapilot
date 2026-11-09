"""ui.py — Interface Gradio de DataPilot (couche présentation uniquement)."""
from __future__ import annotations

import logging

import gradio as gr

TITLE = "📊 DataPilot — l'assistant data analyst de ShopNova"
DESCRIPTION = (
    "Posez vos questions **en français** sur les **ventes ShopNova de 2024 et 2025** "
    "(clients, commandes, produits, retours) et sur les **règles internes** "
    "(définitions des indicateurs, politique de retours, livraison, segmentation clients).\n\n"
    "DataPilot calcule les chiffres avec une **requête SQL** sur la base des ventes et cherche les règles "
    "dans la **documentation officielle**. Chaque réponse est accompagnée de blocs 🔧 repliables : "
    "cliquez dessus pour voir la requête exécutée et les passages consultés."
)
EXAMPLES = [
    "Combien de clients ont le statut VIP ?",                         # chiffrée (SQL)
    "Quel est le délai de retour pour un client VIP ?",               # règle (documentation)
    "Quel est le chiffre d'affaires net de 2025 ?",                   # mixte (définition + SQL)
    "Quel est le panier moyen 2025 selon la définition officielle ?", # mixte (définition + SQL)
    "À partir de quel montant la livraison est-elle gratuite ?",      # règle (documentation)
]
FOOTER = (
    "<small>⚠️ <b>Données de démonstration</b> (ShopNova, entreprise fictive). "
    "DataPilot utilise un modèle d'IA local (Ollama) : il peut se tromper. "
    "<b>Vérifiez les requêtes affichées avant toute décision.</b> "
    "Une réponse peut prendre 10 à 40 secondes. "
    "La base est en lecture seule : aucune donnée ne peut être modifiée.</small>"
)

# Libellés et icônes des outils (affichés dans les blocs repliables)
TOOL_ICONS = {"query_database": "🗄️ Requête SQL", "search_docs": "📚 Recherche documentaire"}
MAX_CONTENT = 1500   # longueur max du résultat affiché dans un bloc repliable


def message_text(content) -> str:
    """Renvoie le texte d'un message Gradio (chaîne, ou liste de morceaux en Gradio 6)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p)
    return str(content)


def steps_to_messages(steps) -> list[dict]:
    """Transforme les étapes de l'agent en messages repliables pour le Chatbot."""
    messages = []
    for step in steps:
        if step.kind == "tool":
            label = TOOL_ICONS.get(step.tool, step.tool)
            result = str(step.content)
            if len(result) > MAX_CONTENT:
                result = result[:MAX_CONTENT] + "\n… (résultat tronqué)"
            lang = "sql" if step.tool == "query_database" else "text"
            content = (f"**Entrée :**\n```{lang}\n{step.tool_input}\n```\n"
                       f"**Résultat :**\n\n{result}")
            messages.append({"role": "assistant", "content": content,
                             "metadata": {"title": f"🔧 {label}", "status": "done"}})
        elif step.kind == "error":
            messages.append({"role": "assistant", "content": str(step.content),
                             "metadata": {"title": "⚠️ Erreur corrigée par l'agent", "status": "done"}})
        # les étapes "final" sont ignorées : la réponse finale est ajoutée à part
    return messages


def create_ui(agent) -> gr.Blocks:
    """Construit l'interface. `agent` doit seulement posséder ask(question) et reset()."""

    def add_user_message(message: str, history: list):
        """1er événement (instantané) : affiche la question et vide la zone de saisie."""
        if not message or not message.strip():
            return "", history
        return "", history + [{"role": "user", "content": message.strip()}]

    def bot_response(history: list):
        """2e événement (lent) : appelle l'agent et ajoute ses étapes + sa réponse."""
        if not history or history[-1].get("role") != "user":
            return history
        question = message_text(history[-1]["content"])
        response = agent.ask(question)
        return (history + steps_to_messages(response.steps)
                + [{"role": "assistant", "content": response.answer}])

    def reset_conversation():
        """Vide la mémoire de l'agent, l'historique affiché et la saisie."""
        agent.reset()
        return [], ""

    with gr.Blocks(title="DataPilot") as demo:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(DESCRIPTION)
        chatbot = gr.Chatbot(label="Conversation avec DataPilot", height=520,
                             buttons=["copy"],
                             placeholder="👋 Bonjour ! Posez une question sur les ventes ShopNova "
                                         "ou cliquez sur un exemple ci-dessous 👇")
        with gr.Row():
            question = gr.Textbox(show_label=False, scale=8, placeholder="Votre question…")
            send_btn = gr.Button("Envoyer", variant="primary", scale=1)
            reset_btn = gr.Button("🔄 Réinitialiser", scale=1)
        gr.Examples(examples=EXAMPLES, inputs=question, label="💡 Exemples de questions")
        gr.Markdown(FOOTER)

        # Entrée (touche Entrée) ET clic sur « Envoyer » : deux événements enchaînés
        for trigger in (question.submit, send_btn.click):
            trigger(add_user_message, [question, chatbot], [question, chatbot], queue=False) \
                .then(bot_response, chatbot, chatbot, show_progress="full")

        reset_btn.click(reset_conversation, None, [chatbot, question], queue=False)
    return demo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from agent import build_agent

    agent, llm = build_agent()
    if not llm.is_available():
        print("⚠️  Ollama ne répond pas : lancez l'application Ollama ou 'ollama serve'.")
    create_ui(agent).launch(theme=gr.themes.Soft())