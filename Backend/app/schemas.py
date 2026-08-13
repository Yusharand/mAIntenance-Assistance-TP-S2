"""
Schémas Pydantic — Personne 1 & Personne 4
Toute donnée qui transite entre les modules DOIT passer par un de ces schémas.
C'est ce qui garantit des "sorties structurées" (exigence 5.3 du sujet).
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class TicketInput(BaseModel):
    """Ticket brut soumis par un utilisateur."""
    ticket_id: str
    texte: str
    utilisateur_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ClassificationResult(BaseModel):
    """Sortie du module de classification — Personne 1."""
    categorie: Literal[
        "comptes_authentification", "reseau_connectivite", "materiel_informatique",
        "logiciels_applications", "imprimantes_peripheriques", "droits_acces",
        "cybersecurite", "autre_indetermine"
    ]
    priorite: Literal["basse", "moyenne", "haute", "critique"]
    equipe: str
    confiance: float = Field(ge=0.0, le=1.0)


class DiagnosticResult(BaseModel):
    """Sortie du module de diagnostic — Personne 1."""
    utilisateur_concerne: Optional[str] = None
    equipement: Optional[str] = None
    application_service: Optional[str] = None
    symptomes: Optional[str] = None
    moment_apparition: Optional[str] = None
    impact_activite: Optional[str] = None
    manipulations_effectuees: Optional[str] = None
    informations_manquantes: list[str] = []
    questions_a_poser: list[str] = []


class SourceCitee(BaseModel):
    """Une source utilisée par le RAG — Personne 2."""
    document_id: str
    extrait: str
    score_pertinence: float


class RAGResult(BaseModel):
    """Sortie du module RAG — Personne 2."""
    reponse_proposee: Optional[str] = None
    sources: list[SourceCitee] = []
    reponse_suffisamment_soutenue: bool = False


class ToolCallLog(BaseModel):
    """Trace d'un appel d'outil — Personne 3."""
    nom_outil: str
    parametres: dict
    resultat: Optional[dict] = None
    statut: Literal["succes", "echec", "refuse"]
    timestamp: datetime = Field(default_factory=datetime.now)


class DecisionFinale(BaseModel):
    """
    Sortie structurée finale — EXACTEMENT le schéma imposé section 5.3 du sujet.
    C'est CE schéma qui doit être montré au jury.
    """
    categorie: str
    priorite: str
    equipe: str
    confiance: float
    informations_manquantes: list[str] = []
    action: Literal["resolution", "demande_information", "escalade", "refus"]
    sources: list[str] = []
    validation_humaine_requise: bool

    # Champs additionnels utiles pour la démo / le rapport (au-delà du minimum imposé)
    resume_probleme: Optional[str] = None
    diagnostic: Optional[str] = None
    etapes_resolution: list[str] = []
    outils_utilises: list[str] = []
    incertitude_notes: Optional[str] = None
