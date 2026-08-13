"""
PERSONNE 4 (partie 2/2) — Orchestrateur (le "chef d'orchestre" du pipeline)
==============================================================================
C'est le module le plus important pour l'INTÉGRATION. Il appelle dans l'ordre
les modules des 3 autres personnes et assemble la DecisionFinale (schéma imposé
section 5.3). Ne commence à le finaliser qu'une fois que chaque module a au moins
une version fonctionnelle (même basique) -> prévoir un point de sync vers 11h00
et un autre vers 13h30 (voir répartition horaire).
"""
from app.schemas import TicketInput, DecisionFinale
from app.classifier import classify_ticket, extract_diagnostic_info
from app.rag import answer_with_citations
from app.agent import run_agent
from app.guardrails import is_sensitive_action, detect_prompt_injection
from app.observability import Timer, log_step, log_decision_finale


def process_ticket(ticket: TicketInput) -> DecisionFinale:
    # 1. Sécurité en amont : on vérifie l'injection avant même de classifier
    injection_detectee, raison_injection = detect_prompt_injection(ticket.texte)
    if injection_detectee:
        decision = DecisionFinale(
            categorie="autre_indetermine",
            priorite="basse",
            equipe="securite",
            confiance=0.0,
            action="refus",
            validation_humaine_requise=True,
            incertitude_notes=f"Tentative de manipulation détectée : {raison_injection}.",
        )
        log_decision_finale(ticket.ticket_id, decision.model_dump())
        return decision

    # 2. Classification
    with Timer() as t:
        classification = classify_ticket(ticket)
    log_step("classification", {"texte": ticket.texte}, classification.model_dump(), t.elapsed)

    # 3. Diagnostic
    with Timer() as t:
        diagnostic = extract_diagnostic_info(ticket)
    log_step("diagnostic", {"texte": ticket.texte}, diagnostic.model_dump(), t.elapsed)

    # Scénario 3 : demande incomplète -> on s'arrête et on pose les questions
    if diagnostic.informations_manquantes:
        return DecisionFinale(
            categorie=classification.categorie,
            priorite=classification.priorite,
            equipe=classification.equipe,
            confiance=classification.confiance,
            informations_manquantes=diagnostic.informations_manquantes,
            action="demande_information",
            validation_humaine_requise=False,
            resume_probleme=ticket.texte,
        )

    # 4. RAG
    with Timer() as t:
        rag_result = answer_with_citations(ticket.texte)
    log_step("rag", {"query": ticket.texte}, rag_result.model_dump(), t.elapsed)

    # 5. Agent + outils
    contexte_agent = diagnostic.model_dump()
    contexte_agent["utilisateur_id"] = ticket.utilisateur_id
    contexte_agent["ticket_id"] = ticket.ticket_id
    with Timer() as t:
        tool_logs = run_agent(ticket.texte, classification.categorie, contexte_agent)
    log_step("agent", {"categorie": classification.categorie},
              {"appels": [l.model_dump() for l in tool_logs]}, t.elapsed)

    # 6. Décision finale
    validation_requise = (
        classification.categorie == "cybersecurite"
        or any(l.statut == "refuse" for l in tool_logs)
        or not rag_result.reponse_suffisamment_soutenue
    )
    action = "escalade" if validation_requise else "resolution"

    decision = DecisionFinale(
        categorie=classification.categorie,
        priorite=classification.priorite,
        equipe=classification.equipe,
        confiance=classification.confiance,
        informations_manquantes=[],
        action=action,
        sources=[s.document_id for s in rag_result.sources],
        validation_humaine_requise=validation_requise,
        resume_probleme=ticket.texte,
        diagnostic=diagnostic.symptomes,
        etapes_resolution=[rag_result.reponse_proposee] if rag_result.reponse_proposee else [],
        outils_utilises=[l.nom_outil for l in tool_logs],
        incertitude_notes=None if rag_result.reponse_suffisamment_soutenue else "Aucune source suffisamment pertinente trouvée.",
    )

    log_decision_finale(ticket.ticket_id, decision.model_dump())
    return decision
