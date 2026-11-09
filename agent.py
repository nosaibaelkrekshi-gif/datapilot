"""agent.py — Routing et boucle de l'agent DataPilot."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from llm_client import Conversation, LLMError

logger = logging.getLogger("agent")
FINAL = "final_answer"


# ======================================================================
# Étape 9 — Lire la décision du LLM et router
# ======================================================================
@dataclass
class Decision:
    action: str
    input: object
    thought: str = ""
    params: list = field(default_factory=list)


class ParseError(ValueError):
    """Le texte du LLM ne contient pas de décision JSON exploitable."""


def parse_llm_output(raw: str) -> Decision:
    """Transforme le texte brut du LLM en Decision (lecture tolérante)."""
    # 1) Retirer les balises de code markdown ```json ... ```
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 2) Essayer de lire le JSON directement, sinon extraire du premier { au dernier }
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)   # gourmand : .* et non .*?
        if not match:
            raise ParseError("Aucun objet JSON trouvé dans la réponse du LLM.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ParseError(f"JSON illisible : {exc}") from exc

    # 3) Vérifier la structure
    if not isinstance(data, dict) or "action" not in data:
        raise ParseError("Le JSON ne contient pas de clé « action ».")

    params = data.get("params") or []
    if not isinstance(params, list):
        params = [params]

    return Decision(
        action=str(data["action"]).strip().lower(),
        input=data.get("input", data.get("action_input", "")),
        thought=str(data.get("thought", "")),
        params=params,
    )


@dataclass
class RouteResult:
    kind: str                  # "tool", "final" ou "error"
    content: str               # résultat de l'outil, réponse finale ou message d'erreur
    tool: str | None = None
    tool_input: object = None
    thought: str = ""


def route_query(llm_output: str, tools: dict) -> RouteResult:
    """Lit la décision du LLM et exécute l'outil demandé. Ne lève jamais d'exception."""
    # Cas 1 : JSON illisible
    try:
        decision = parse_llm_output(llm_output)
    except ParseError as exc:
        return RouteResult(
            kind="error",
            content=(f"Réponse illisible ({exc}). Réponds UNIQUEMENT avec un objet JSON : "
                     '{"thought": "...", "action": "...", "input": "..."}'))

    # Cas 2 : réponse finale
    if decision.action == FINAL:
        return RouteResult(kind="final", content=str(decision.input),
                           thought=decision.thought)

    # Cas 3 : outil inconnu
    if decision.action not in tools:
        valides = ", ".join(list(tools) + [FINAL])
        return RouteResult(
            kind="error",
            content=f"Outil inconnu « {decision.action} ». Outils valides : {valides}.",
            tool=decision.action, tool_input=decision.input, thought=decision.thought)

    # Cas 4 : outil connu -> on l'exécute
    tool = tools[decision.action]
    if decision.action == "query_database" and decision.params:
        content = tool.run(str(decision.input), decision.params)
    else:
        content = tool.run(str(decision.input))
    return RouteResult(kind="tool", content=content, tool=decision.action,
                       tool_input=decision.input, thought=decision.thought)




# ======================================================================
# Étape 10 — La boucle de l'agent
# ======================================================================
@dataclass
class AgentResponse:
    answer: str
    steps: list[RouteResult] = field(default_factory=list)


class Agent:
    def __init__(self, llm, tools: dict, system_prompt: str,
                 max_steps: int = 5, max_history_turns: int = 6) -> None:
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.conversation = Conversation(system_prompt, max_turns=max_history_turns)

    def ask(self, question: str) -> AgentResponse:
        """Boucle ReAct : le LLM décide -> on exécute -> on renvoie l'observation -> ..."""
        self.conversation.add_user(question)
        scratchpad = self.conversation.messages()   # brouillon : copie de la mémoire longue
        steps: list[RouteResult] = []
        answer = None
        try:
            for _ in range(self.max_steps):
                raw = self.llm.chat(scratchpad, json_mode=True)    # 1) le LLM décide
                result = route_query(raw, self.tools)              # 2) Python exécute
                steps.append(result)
                if result.kind == "final":                         # 3) réponse finale ?
                    answer = result.content
                    break
                # 4) sinon on enrichit le brouillon : ce que le LLM a dit + l'observation
                scratchpad.append({"role": "assistant", "content": raw})
                if result.kind == "error":
                    observation = f"ERREUR DE FORMAT :\n{result.content}"
                else:
                    observation = f"OBSERVATION ({result.tool}) :\n{result.content}"
                scratchpad.append({"role": "user", "content": observation})

            if answer is None:
                # Garde-fou : limite d'étapes atteinte -> on force une réponse finale
                scratchpad.append({"role": "user", "content": (
                    "Tu as atteint le nombre maximal d'étapes. Donne maintenant ta réponse "
                    "finale avec les informations dont tu disposes, au format JSON avec "
                    "l'action final_answer.")})
                raw = self.llm.chat(scratchpad, json_mode=True)
                result = route_query(raw, self.tools)
                steps.append(result)
                if result.kind == "final":
                    answer = result.content
                else:
                    answer = ("Désolé, je n'ai pas réussi à trouver une réponse fiable à votre "
                              "question. Pouvez-vous la reformuler ?")
        except LLMError as exc:
            logger.error("LLM en panne : %s", exc)          # le détail technique reste dans les journaux
            answer = ("Le moteur IA est indisponible pour le moment. "
                      "Lancez l'application Ollama (ou « ollama serve »), puis réessayez.")

        self.conversation.add_assistant(answer)   # seule la réponse finale va en mémoire longue
        return AgentResponse(answer=answer, steps=steps)

    def reset(self) -> None:
        """Vide la mémoire de la conversation."""
        self.conversation.reset()


def build_agent():
    """Assemble tous les morceaux : LLM, outils, system prompt, agent."""
    import config
    from llm_client import LLMClient
    from prompts import build_system_prompt
    from tools import DocSearchTool, SQLTool, load_corpus, load_embedder

    llm = LLMClient(
        model=config.LLM_MODEL,
        base_url=config.OLLAMA_URL,
        temperature=config.LLM_TEMPERATURE,
        timeout=config.LLM_TIMEOUT,
        num_ctx=config.LLM_NUM_CTX,
        log_file=config.LOG_DIR / "llm_exchanges.jsonl",
    )
    sql_tool = SQLTool(config.DB_PATH, max_rows=config.SQL_MAX_ROWS)
    doc_tool = DocSearchTool(
        load_corpus(config.DOCS_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP),
        load_embedder(config.EMBEDDING_MODEL),
        top_k=config.TOP_K,
    )
    tools = {sql_tool.name: sql_tool, doc_tool.name: doc_tool}
    system_prompt = build_system_prompt(sql_tool.get_schema())
    agent = Agent(llm, tools, system_prompt,
                  max_steps=config.MAX_STEPS, max_history_turns=config.MAX_HISTORY_TURNS)
    return agent, llm


if __name__ == "__main__":
    # Mode console
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s : %(message)s")
    print("Chargement de DataPilot (modèle d'embeddings + index)...")
    agent, llm = build_agent()
    if not llm.is_available():
        print("⚠️  Ollama ne répond pas. Lancez-le avec : ollama serve")
    print("DataPilot est prêt. Tapez votre question ('reset' = vider la mémoire, 'quit' = quitter).")

    while True:
        try:
            question = input("\nVous > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break
        if question.lower() == "reset":
            agent.reset()
            print("Mémoire vidée.")
            continue

        response = agent.ask(question)
        for i, step in enumerate(response.steps, start=1):
            entree = str(step.tool_input or step.content).replace("\n", " ")[:120]
            print(f"  Étape {i} [{step.kind}] {step.tool or ''} : {entree}")
        print(f"\nDataPilot > {response.answer}")

    print("Au revoir !")