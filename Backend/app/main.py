"""
PERSONNE 4 — Point d'entrée FastAPI.
Lancer avec : uvicorn app.main:app --reload --port 8000
Docs auto générées : http://localhost:8000/docs
"""
from fastapi import FastAPI
from app.schemas import TicketInput, DecisionFinale
from app.orchestrator import process_ticket
from app.observability import read_all_logs

app = FastAPI(
    title="mAIntenance & Assistance",
    description="Assistant intelligent de support informatique — ISPM Hackathon",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ticket", response_model=DecisionFinale)
def submit_ticket(ticket: TicketInput):
    """Endpoint principal : soumet un ticket, retourne la décision structurée."""
    return process_ticket(ticket)


@app.get("/observability/logs")
def get_logs():
    """Utilisé par le dashboard Streamlit pour afficher le journal."""
    return read_all_logs()
