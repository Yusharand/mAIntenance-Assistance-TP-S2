"""
PERSONNE 3 (partie 1/3) — Outils de l'agent (contribue à l'axe Agent, 20%)
============================================================================

DÉMARCHE
--------
Les 8 outils du sujet (section 3.4) sont simulés sur les fichiers JSON de
data/ (utilisateurs, équipements, services, incidents) plutôt que connectés à
un vrai système d'information — c'est explicitement autorisé par le sujet
("outils réels ou simulés").

Chaque outil :
  1. VALIDE ses paramètres avant toute exécution (type, présence, existence en
     base) -> exigence "validation des paramètres" section 5.2.
  2. Renvoie toujours un dict avec une clé "erreur" en cas de problème, jamais
     une exception qui remonterait telle quelle jusqu'à l'utilisateur.
  3. Est enregistré dans TOOL_REGISTRY avec sa liste de paramètres attendus
     (TOOL_SPECS) -> utilisé par agent.py pour valider AVANT l'appel, pas
     seulement en le laissant planter.

Les outils d'action (creer_ticket, mettre_a_jour_ticket, affecter_ticket,
escalader_vers_technicien) modifient un état -> ils sont dans OUTILS_SENSIBLES
et ne sont JAMAIS exécutés directement par l'agent sans validation humaine
préalable (section 6 du sujet).
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
TICKETS_STORE = DATA_DIR / "tickets_store.json"


def _load(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tickets_store() -> dict:
    if not TICKETS_STORE.exists():
        return {}
    return json.loads(TICKETS_STORE.read_text(encoding="utf-8"))


def _save_tickets_store(store: dict) -> None:
    TICKETS_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Outils de CONSULTATION (lecture seule — jamais besoin de validation humaine)
# ---------------------------------------------------------------------------

def rechercher_utilisateur(utilisateur_id: str) -> dict:
    if not utilisateur_id or not isinstance(utilisateur_id, str):
        return {"erreur": "parametre utilisateur_id invalide"}
    users = _load("users.json")
    return users.get(utilisateur_id, {"erreur": "utilisateur introuvable", "utilisateur_id": utilisateur_id})


def consulter_equipement(equipement_id: str) -> dict:
    if not equipement_id or not isinstance(equipement_id, str):
        return {"erreur": "parametre equipement_id invalide"}
    equipements = _load("equipments.json")
    return equipements.get(equipement_id, {"erreur": "équipement introuvable", "equipement_id": equipement_id})


def verifier_etat_service(service: str) -> dict:
    if not service or not isinstance(service, str):
        return {"erreur": "parametre service invalide"}
    services = _load("services.json")
    return services.get(service, {"erreur": "service inconnu", "service": service})


def rechercher_incidents_actifs(categorie: str = None) -> dict:
    incidents = _load("active_incidents.json").get("incidents", [])
    if categorie:
        incidents = [i for i in incidents if i.get("categorie") == categorie]
    return {"incidents": incidents, "total": len(incidents)}


# ---------------------------------------------------------------------------
# Outils d'ACTION (sensibles -> validation humaine obligatoire, cf. guardrails)
# ---------------------------------------------------------------------------

def creer_ticket(categorie: str, priorite: str, description: str) -> dict:
    if not categorie or not priorite or not description:
        return {"erreur": "champs categorie/priorite/description requis"}
    store = _load_tickets_store()
    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    store[ticket_id] = {
        "categorie": categorie, "priorite": priorite, "description": description,
        "statut": "cree", "cree_le": datetime.now().isoformat(),
    }
    _save_tickets_store(store)
    return {"ticket_id": ticket_id, "statut": "cree"}


def mettre_a_jour_ticket(ticket_id: str, updates: dict) -> dict:
    store = _load_tickets_store()
    if ticket_id not in store:
        return {"erreur": "ticket introuvable", "ticket_id": ticket_id}
    store[ticket_id].update(updates)
    _save_tickets_store(store)
    return {"ticket_id": ticket_id, "statut": "mis_a_jour"}


def affecter_ticket(ticket_id: str, equipe: str) -> dict:
    return mettre_a_jour_ticket(ticket_id, {"equipe_affectee": equipe})


def escalader_vers_technicien(ticket_id: str, raison: str) -> dict:
    return mettre_a_jour_ticket(ticket_id, {"statut": "escalade", "raison_escalade": raison})


# ---------------------------------------------------------------------------
# Registre : outil -> (fonction, paramètres attendus)
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "rechercher_utilisateur": rechercher_utilisateur,
    "consulter_equipement": consulter_equipement,
    "verifier_etat_service": verifier_etat_service,
    "rechercher_incidents_actifs": rechercher_incidents_actifs,
    "creer_ticket": creer_ticket,
    "mettre_a_jour_ticket": mettre_a_jour_ticket,
    "affecter_ticket": affecter_ticket,
    "escalader_vers_technicien": escalader_vers_technicien,
}

# Paramètres obligatoires par outil — utilisé par agent.py pour valider AVANT
# d'appeler (plutôt que de laisser un TypeError remonter).
TOOL_SPECS = {
    "rechercher_utilisateur": ["utilisateur_id"],
    "consulter_equipement": ["equipement_id"],
    "verifier_etat_service": ["service"],
    "rechercher_incidents_actifs": [],  # categorie optionnel
    "creer_ticket": ["categorie", "priorite", "description"],
    "mettre_a_jour_ticket": ["ticket_id", "updates"],
    "affecter_ticket": ["ticket_id", "equipe"],
    "escalader_vers_technicien": ["ticket_id", "raison"],
}

OUTILS_SENSIBLES = {
    "creer_ticket", "mettre_a_jour_ticket", "affecter_ticket", "escalader_vers_technicien",
}
