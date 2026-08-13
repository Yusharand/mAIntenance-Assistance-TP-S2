"""
PERSONNE 3 (partie 3/3) — Boucle de l'agent (axe noté : 20%)
===============================================================

DÉMARCHE
--------
Sélection d'outils DÉTERMINISTE par règles (build_tool_plan), pas de
tool-calling LLM : plus lent à mettre en place côté prompt engineering et
moins prévisible pour une démo de 8h, alors qu'un plan explicite par
catégorie est trivial à auditer par le jury ("pourquoi l'agent a appelé cet
outil ?" -> réponse dans build_tool_plan, ligne par ligne).
Si l'équipe a le temps et une clé API LLM, cette fonction est le seul
endroit à remplacer par un appel de function-calling — le reste de la boucle
(validation, garde-fous, logging) reste identique.

GARANTIES DE SÉCURITÉ DE LA BOUCLE (section 5.2 et 6 du sujet)
-----------------------------------------------------------------
1. Contrôle du nombre d'actions : MAX_APPELS_OUTILS borne strictement le
   nombre d'appels, quel que soit le plan proposé.
2. Validation des paramètres AVANT appel (pas de try/except comme seule
   protection) : `_valider_parametres`.
3. Aucun outil sensible n'est exécuté sans passer par le statut
   "en_attente_validation_humaine" — l'agent NE DÉCIDE JAMAIS seul d'agir sur
   un compte, des droits, ou un incident de cybersécurité.
4. Toute tentative de prompt injection stoppe la boucle immédiatement, avant
   même de sélectionner un outil.
"""
from app.schemas import ToolCallLog
from app.tools import TOOL_REGISTRY, TOOL_SPECS
from app.guardrails import is_sensitive_action, detect_prompt_injection
from app.observability import log_tool_call

MAX_APPELS_OUTILS = 5


def _valider_parametres(nom_outil: str, parametres: dict) -> tuple[bool, str | None]:
    """Vérifie que tous les paramètres obligatoires sont présents et non vides
    AVANT d'appeler l'outil."""
    attendus = TOOL_SPECS.get(nom_outil, [])
    for p in attendus:
        if p not in parametres or parametres[p] in (None, ""):
            return False, f"paramètre manquant : {p}"
    return True, None


def build_tool_plan(categorie: str, ticket_texte: str, contexte: dict) -> list[tuple[str, dict]]:
    """Construit la liste ordonnée d'outils à considérer pour une catégorie
    donnée. `contexte` vient du diagnostic (Personne 1) : équipement,
    application_service, etc. Chaque ligne est justifiable individuellement
    -> à documenter dans le rapport technique.
    """
    utilisateur_id = contexte.get("utilisateur_id")
    equipement = contexte.get("equipement")
    application = contexte.get("application_service")
    impact = contexte.get("impact_activite")

    plan: list[tuple[str, dict]] = []

    if categorie == "comptes_authentification":
        if utilisateur_id:
            plan.append(("rechercher_utilisateur", {"utilisateur_id": utilisateur_id}))
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "moyenne",
            "description": "Réinitialisation de mot de passe / déblocage de compte",
        }))

    elif categorie == "reseau_connectivite":
        plan.append(("verifier_etat_service", {"service": "reseau_local"}))
        plan.append(("rechercher_incidents_actifs", {"categorie": categorie}))
        if impact:
            plan.append(("escalader_vers_technicien", {
                "ticket_id": contexte.get("ticket_id", "INCONNU"),
                "raison": "Impact réseau sur plusieurs utilisateurs",
            }))

    elif categorie == "materiel_informatique":
        if equipement:
            plan.append(("consulter_equipement", {"equipement_id": equipement}))
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "moyenne",
            "description": f"Panne matérielle : {ticket_texte[:120]}",
        }))

    elif categorie == "logiciels_applications":
        if application:
            plan.append(("verifier_etat_service", {"service": application}))
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "moyenne",
            "description": f"Incident logiciel : {ticket_texte[:120]}",
        }))

    elif categorie == "imprimantes_peripheriques":
        if equipement:
            plan.append(("consulter_equipement", {"equipement_id": equipement}))

    elif categorie == "droits_acces":
        if utilisateur_id:
            plan.append(("rechercher_utilisateur", {"utilisateur_id": utilisateur_id}))
        plan.append(("affecter_ticket", {
            "ticket_id": contexte.get("ticket_id", "INCONNU"), "equipe": "administration_systeme",
        }))

    elif categorie == "cybersecurite":
        plan.append(("rechercher_incidents_actifs", {"categorie": categorie}))
        plan.append(("escalader_vers_technicien", {
            "ticket_id": contexte.get("ticket_id", "INCONNU"),
            "raison": "Incident de cybersécurité — escalade systématique",
        }))

    else:  # autre_indetermine
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "basse",
            "description": f"Ticket non classable : {ticket_texte[:120]}",
        }))

    return plan


def run_agent(ticket_texte: str, categorie: str, contexte: dict) -> list[ToolCallLog]:
    """Exécute le plan d'outils pour ce ticket, avec garde-fous à chaque étape."""
    logs: list[ToolCallLog] = []

    injection, raison = detect_prompt_injection(ticket_texte)
    if injection:
        log = ToolCallLog(
            nom_outil="aucun",
            parametres={"raison": raison},
            resultat={"detail": "exécution bloquée avant toute sélection d'outil"},
            statut="refuse",
        )
        logs.append(log)
        log_tool_call(log)
        return logs

    plan = build_tool_plan(categorie, ticket_texte, contexte)

    for nom_outil, parametres in plan[:MAX_APPELS_OUTILS]:
        valide, raison_invalide = _valider_parametres(nom_outil, parametres)
        if not valide:
            log = ToolCallLog(nom_outil=nom_outil, parametres=parametres,
                               resultat={"erreur": raison_invalide}, statut="echec")
            logs.append(log)
            log_tool_call(log)
            continue

        if is_sensitive_action(nom_outil, categorie):
            log = ToolCallLog(
                nom_outil=nom_outil, parametres=parametres,
                resultat={"detail": "action sensible — en attente de validation humaine"},
                statut="refuse",
            )
            logs.append(log)
            log_tool_call(log)
            continue  # on ne va PAS plus loin dans le plan sans validation

        try:
            resultat = TOOL_REGISTRY[nom_outil](**parametres)
            log = ToolCallLog(nom_outil=nom_outil, parametres=parametres,
                               resultat=resultat, statut="succes")
        except Exception as e:
            log = ToolCallLog(nom_outil=nom_outil, parametres=parametres,
                               resultat={"erreur": str(e)}, statut="echec")

        logs.append(log)
        log_tool_call(log)

    return logs
