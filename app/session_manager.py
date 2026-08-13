"""Gestion des sessions de conversation multi-tours pour l'assistant IT.
Permet de continuer le traitement après que l'utilisateur ait répondu aux questions."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.schemas import TicketSession, TicketInput, DecisionFinale

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
SESSION_TIMEOUT = timedelta(hours=24)  # Les sessions expirent après 24h


def _get_session_path(conversation_id: str) -> Path:
    """Retourne le chemin du fichier JSON pour une session."""
    # Sanitize pour éviter les path traversal attacks
    safe_id = conversation_id.replace("/", "_").replace("\\", "_")
    return SESSIONS_DIR / f"{safe_id}.json"


def save_session(session: TicketSession) -> None:
    """Sauvegarde une session en JSON."""
    path = _get_session_path(session.ticket_id)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def load_session(ticket_id: str) -> Optional[TicketSession]:
    """Charge une session depuis le disque."""
    path = _get_session_path(ticket_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        session = TicketSession(**data)
        # Vérifier l'expiration
        if datetime.now() - session.timestamp_creation > SESSION_TIMEOUT:
            path.unlink()  # Supprimer la session expirée
            return None
        return session
    except Exception:
        return None


def delete_session(ticket_id: str) -> None:
    """Supprime une session."""
    path = _get_session_path(ticket_id)
    if path.exists():
        path.unlink()


def create_session(ticket: TicketInput, classification: dict, diagnostic: dict) -> TicketSession:
    """Crée une nouvelle session de conversation."""
    session = TicketSession(
        ticket_id=ticket.ticket_id,
        categorie=classification.get("categorie", "autre_indetermine"),
        priorite=classification.get("priorite", "basse"),
        equipe=classification.get("equipe", "support_niveau_1"),
        etape_actuelle="classification",
        contexte_diagnostic=diagnostic,
        questions_restantes=diagnostic.get("questions_a_poser", []),
    )
    save_session(session)
    return session


def update_session_with_user_response(ticket_id: str, user_response: str) -> Optional[TicketSession]:
    """Met à jour une session avec la réponse de l'utilisateur à une question.
    Marque la question comme répondue et passe à la prochaine étape."""
    session = load_session(ticket_id)
    if not session or not session.questions_restantes:
        return None
    
    # Enregistrer la réponse (on la stocke avec la première question restante)
    question_key = session.questions_restantes[0] if session.questions_restantes else "general"
    session.reponses_utilisateur[question_key] = user_response
    session.questions_restantes.pop(0)  # Retirer la question traitée
    
    # Si toutes les questions ont été répondues, passer à la prochaine étape
    if not session.questions_restantes:
        session.etape_actuelle = "rag_agent"
    
    save_session(session)
    return session


def update_session_with_decision(ticket_id: str, decision: DecisionFinale) -> Optional[TicketSession]:
    """Met à jour une session avec la décision finale."""
    session = load_session(ticket_id)
    if not session:
        return None
    
    session.decision_finale = decision
    session.etape_actuelle = "resolution"
    save_session(session)
    return session
