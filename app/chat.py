
from app.schemas import DecisionFinale
from app.llm_client import call_llm

SYSTEM_PROMPT = (
    "You are the IT support assistant for a company. You receive a decision "
    "that has already been made by a ticket-processing system (category, "
    "priority, actions already taken, documentary sources). Your only role "
    "is to rephrase this decision into a clear, concise, and polite response "
    "in English, addressed directly to the user. Never invent information "
    "that is not present in the decision provided. Never propose an action "
    "that has not already been validated."
)


def _decision_vers_prompt(message_utilisateur: str, decision: DecisionFinale) -> str:
    lignes = [f"Original user message: {message_utilisateur}", ""]
    lignes.append(f"Detected category: {decision.categorie}")
    lignes.append(f"Priority: {decision.priorite}")
    lignes.append(f"Action decided by the system: {decision.action}")

    if decision.action == "demande_information":
        questions = decision.questions_a_poser or decision.informations_manquantes
        lignes.append("Questions to ask the user: " + " / ".join(questions))

    if decision.etapes_resolution:
        lignes.append("Information found in the knowledge base:")
        lignes.extend(f"- {e}" for e in decision.etapes_resolution)

    if decision.sources:
        lignes.append("Sources: " + ", ".join(decision.sources))

    if decision.validation_humaine_requise:
        lignes.append(
            "Human validation is required before any action: state this "
            "clearly to the user, without technical detail on why (just "
            "that a technician will take over)."
        )

    if decision.incertitude_notes:
        lignes.append(f"Uncertainty note: {decision.incertitude_notes}")

    lignes.append("")
    lignes.append("Write the response to send to the user (3-6 sentences maximum).")
    return "\n".join(lignes)


def _template_repli(decision: DecisionFinale) -> str:
    """Deterministic response used when Groq is unavailable — never an empty
    response, even in degraded mode."""
    if decision.action == "refus":
        return (
            "Your request could not be processed automatically for security "
            "reasons. A technician will review your ticket."
        )

    if decision.action == "demande_information":
        questions = decision.questions_a_poser or decision.informations_manquantes
        return (
            "To process your request, I need a bit more information: "
            + " ".join(questions)
        )

    if decision.action == "escalade":
        base = (
            f"Your ticket has been classified as category \u00ab {decision.categorie} \u00bb "
            f"with priority \u00ab {decision.priorite} \u00bb. "
        )
        if decision.validation_humaine_requise:
            base += "It has been forwarded to a technician for validation before any action."
        return base

    # resolution
    reponse = (
        f"Your request has been classified as category \u00ab {decision.categorie} \u00bb. "
    )
    if decision.etapes_resolution:
        reponse += "Here is what was found in our knowledge base:\n\n"
        reponse += "\n\n".join(decision.etapes_resolution)
    else:
        reponse += "It has been taken care of by the relevant team."
    return reponse


def reformuler_decision(message_utilisateur: str, decision: DecisionFinale) -> str:
    """Entry point of the module: reformulates the DecisionFinale into a
    conversational response. Never modifies the decision itself."""
    prompt = _decision_vers_prompt(message_utilisateur, decision)
    reponse = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.4, max_tokens=300)
    if reponse is None:
        return _template_repli(decision)
    return reponse.strip()
