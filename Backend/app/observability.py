"""
PERSONNE 4 (partie 1/2) — Observabilité (axe noté : 20%)
===========================================================
À FAIRE :
- Logger CHAQUE étape du pipeline (classification, RAG, appels d'outils, décision
  finale) avec : timestamp, latence, entrée, sortie, erreurs éventuelles.
- Stocker dans un simple fichier JSONL (le plus rapide à implémenter) ou SQLite
  (un peu plus propre pour la démo/dashboard).
- Le dashboard (demo/streamlit_app.py) doit pouvoir relire ces logs et les afficher
  -> c'est ÇA le "journal ou tableau de bord d'observabilité" exigé en livrable 7.
- Bonus : estimer un coût par requête (ex: tokens_in * prix + tokens_out * prix)
  si vous utilisez une API LLM payante/à quota.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from app.schemas import ToolCallLog

LOG_FILE = Path(__file__).parent.parent / "logs" / "observability.jsonl"
LOG_FILE.parent.mkdir(exist_ok=True)


def _append_log(entry: dict) -> None:
    entry["timestamp"] = datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def log_step(step_name: str, entree: dict, sortie: dict, latence_s: float, erreur: str = None) -> None:
    """Log générique pour une étape du pipeline (classification, RAG, etc.)."""
    _append_log({
        "type": "step",
        "step": step_name,
        "entree": entree,
        "sortie": sortie,
        "latence_s": round(latence_s, 3),
        "erreur": erreur,
    })


def log_tool_call(tool_call: ToolCallLog) -> None:
    """Log spécifique pour un appel d'outil (appelé par agent.py)."""
    _append_log({
        "type": "tool_call",
        "nom_outil": tool_call.nom_outil,
        "parametres": tool_call.parametres,
        "resultat": tool_call.resultat,
        "statut": tool_call.statut,
    })


def log_decision_finale(ticket_id: str, decision: dict) -> None:
    _append_log({"type": "decision_finale", "ticket_id": ticket_id, "decision": decision})


class Timer:
    """Petit context manager pour mesurer la latence d'une étape.
    Usage: 
        with Timer() as t: ...
        log_step("classification", entree, sortie, t.elapsed)
    """
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start


def read_all_logs() -> list[dict]:
    """Utilisé par le dashboard Streamlit pour afficher l'historique."""
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
