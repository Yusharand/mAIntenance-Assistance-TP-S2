
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import TicketInput, DecisionFinale, ChatRequest, ChatResponse
from app.orchestrator import process_ticket
from app.observability import read_all_logs
from app.chat import reformuler_decision

app = FastAPI(
    title="mAIntenance & Assistance",
    description="Assistant intelligent de support informatique — ISPM Hackathon",
    version="0.1.0",
)

# CORS : permet au frontend NestJS (ou tout autre frontend) d'appeler l'API
# depuis le navigateur. Origines configurables via FRONTEND_ORIGIN dans .env
# (liste séparée par des virgules) — par défaut les ports NestJS/Angular usuels.
_origins_env = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000,http://localhost:4200, https://front-m-a-intenance-assistance.vercel.app/")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ticket", response_model=DecisionFinale)
def submit_ticket(ticket: TicketInput):
    """Endpoint principal : soumet un ticket, retourne la décision structurée."""
    return process_ticket(ticket)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Endpoint conversationnel destiné au frontend NestJS.

    Le pipeline déterministe (classifier -> diagnostic -> RAG -> agent) traite
    le message exactement comme un ticket classique ; ce endpoint ajoute
    uniquement une reformulation en langage naturel de la DecisionFinale
    obtenue (voir app/chat.py). Le LLM ne prend aucune décision."""
    ticket = TicketInput(
        ticket_id=f"CHAT-{uuid.uuid4().hex[:8].upper()}",
        texte=request.message,
        utilisateur_id=request.utilisateur_id,
    )
    decision = process_ticket(ticket)
    reponse = reformuler_decision(request.message, decision)
    return ChatResponse(
        reponse=reponse,
        decision=decision,
        conversation_id=request.conversation_id,
    )


@app.get("/observability/logs")
def get_logs():
    """Journal d'observabilité — consultable par un dashboard externe."""
    return read_all_logs()
