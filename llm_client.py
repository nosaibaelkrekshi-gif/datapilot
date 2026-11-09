"""llm_client.py — Client LLM robuste en Python pur (bibliothèque requests)."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger("llm_client")


class LLMError(Exception):
    """Erreur définitive du client LLM (après épuisement des tentatives)."""


class LLMClient:
    # Codes HTTP "temporaires" : on peut réessayer
    RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

    def __init__(self, model, base_url="http://localhost:11434", temperature=0.1,
                 timeout=120, max_retries=3, backoff_factor=1.0, num_ctx=8192,
                 log_file=None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/api/chat"
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.num_ctx = num_ctx
        self.log_file = Path(log_file) if log_file else None
        self.session = requests.Session()  # réutilise la connexion entre les appels

    # ------------------------------------------------------------------
    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        """Envoie la conversation au LLM et renvoie le texte de sa réponse."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"

        start = time.perf_counter()
        data = self._post_with_retry(payload)
        duration = time.perf_counter() - start

        # Extraire le texte de la réponse
        try:
            answer = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Réponse inattendue d'Ollama : {data!r}") from exc

        self._log_exchange(messages, answer, duration, data)
        return answer

    # ------------------------------------------------------------------
    def _post_with_retry(self, payload: dict) -> dict:
        """POST avec réessais (backoff exponentiel) sur les erreurs temporaires."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(self.url, json=payload, timeout=self.timeout)

                # Erreur temporaire -> on lève HTTPError pour réessayer
                if response.status_code in self.RETRYABLE_STATUS:
                    raise requests.HTTPError(
                        f"Erreur temporaire HTTP {response.status_code}", response=response)

                # Erreur définitive (404, 400...) -> on s'arrête tout de suite
                if response.status_code >= 400:
                    raise LLMError(
                        f"Erreur HTTP {response.status_code} renvoyée par Ollama : "
                        f"{response.text[:200]}")

                try:
                    return response.json()
                except ValueError as exc:
                    raise LLMError("La réponse d'Ollama n'est pas du JSON valide.") from exc

            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_error = exc

            # Pause avant le prochain essai (pas de pause après le dernier)
            if attempt < self.max_retries:
                wait = self.backoff_factor * 2 ** (attempt - 1)
                logger.warning("Essai %d/%d échoué (%s). Nouvel essai dans %.2f s.",
                               attempt, self.max_retries, last_error, wait)
                time.sleep(wait)

        raise LLMError(
            f"Impossible de joindre le LLM après {self.max_retries} essais "
            f"({last_error}). Vérifiez qu'Ollama est lancé : ollama serve")

    # ------------------------------------------------------------------
    def _log_exchange(self, messages, answer, duration, raw):
        """Ajoute une ligne JSON par échange dans le fichier journal (JSONL)."""
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": self.model,
            "duration_s": round(duration, 3),
            "prompt_tokens": raw.get("prompt_eval_count"),
            "completion_tokens": raw.get("eval_count"),
            "messages": messages,
            "answer": answer,
        }
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """True si le serveur Ollama répond."""
        try:
            r = self.session.get(self.base_url + "/api/tags", timeout=3)
            return r.ok
        except requests.RequestException:
            return False




# ======================================================================
# Étape 4 — Mémoire conversationnelle
# ======================================================================
class Conversation:
    """Mémoire conversationnelle sans framework : system prompt + fenêtre glissante."""

    def __init__(self, system_prompt: str, max_turns: int = 6) -> None:
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.history: list[dict] = []   # messages user / assistant (sans le system)

    def add_user(self, content: str) -> None:
        """Ajoute une question de l'utilisateur à l'historique."""
        self.history.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        """Ajoute une réponse du modèle à l'historique."""
        self.history.append({"role": "assistant", "content": content})

    def messages(self) -> list[dict]:
        """System prompt + les 2 × max_turns derniers messages (1 tour = question + réponse)."""
        recent = self.history[-2 * self.max_turns:] if self.max_turns > 0 else []
        return [{"role": "system", "content": self.system_prompt}] + [dict(m) for m in recent]

    def estimated_tokens(self) -> int:
        """Estimation grossière : nombre de caractères / 4."""
        return sum(len(m["content"]) for m in self.messages()) // 4

    def reset(self) -> None:
        """Vide l'historique (le system prompt est conservé)."""
        self.history.clear()


