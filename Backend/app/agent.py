
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
            "description": "Password reset / account unlock",
        }))

    elif categorie == "reseau_connectivite":
        plan.append(("verifier_etat_service", {"service": "reseau_local"}))
        plan.append(("rechercher_incidents_actifs", {"categorie": categorie}))
        if impact:
            plan.append(("escalader_vers_technicien", {
                "ticket_id": contexte.get("ticket_id", "INCONNU"),
                "raison": "Network impact affecting multiple users",
            }))

    elif categorie == "materiel_informatique":
        if equipement:
            plan.append(("consulter_equipement", {"equipement_id": equipement}))
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "moyenne",
            "description": f"Hardware failure: {ticket_texte[:120]}",
        }))

    elif categorie == "logiciels_applications":
        if application:
            plan.append(("verifier_etat_service", {"service": application}))
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "moyenne",
            "description": f"Software incident: {ticket_texte[:120]}",
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
            "raison": "Cybersecurity incident — systematic escalation",
        }))

    else:  # autre_indetermine
        plan.append(("creer_ticket", {
            "categorie": categorie, "priorite": "basse",
            "description": f"Unclassifiable ticket: {ticket_texte[:120]}",
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
