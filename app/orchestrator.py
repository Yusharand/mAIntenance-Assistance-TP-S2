
from app.schemas import TicketInput, DecisionFinale
from app.classifier import classify_ticket, extract_diagnostic_info
from app.rag import answer_with_citations
from app.agent import run_agent
from app.guardrails import is_sensitive_action, detect_prompt_injection
from app.observability import Timer, log_step, log_decision_finale
from app.session_manager import (
    create_session, load_session, update_session_with_decision, update_session_with_user_response
)


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
            incertitude_notes=f"Manipulation attempt detected: {raison_injection}.",
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

    # Scénario 3 : demande incomplète -> on crée une session et on pose les questions
    if diagnostic.informations_manquantes:
        # Créer une session pour le suivi de la conversation
        session = create_session(
            ticket, 
            classification.model_dump(), 
            diagnostic.model_dump()
        )
        return DecisionFinale(
            categorie=classification.categorie,
            priorite=classification.priorite,
            equipe=classification.equipe,
            confiance=classification.confiance,
            informations_manquantes=diagnostic.informations_manquantes,
            action="demande_information",
            validation_humaine_requise=False,
            resume_probleme=ticket.texte,
            questions_a_poser=diagnostic.questions_a_poser,
        )

    # 4. RAG
    with Timer() as t:
        rag_result = answer_with_citations(ticket.texte, use_llm=True)
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
        incertitude_notes=None if rag_result.reponse_suffisamment_soutenue else "No sufficiently relevant source was found.",
    )

    log_decision_finale(ticket.ticket_id, decision.model_dump())
    return decision


def continue_ticket_processing(ticket_id: str, user_response: str) -> DecisionFinale:
    """Continue le traitement d'un ticket après que l'utilisateur ait répondu
    aux questions manquantes. Charge la session, met à jour avec la réponse,
    puis exécute le pipeline RAG + Agent."""
    # Charger la session existante
    session = load_session(ticket_id)
    if not session:
        # Pas de session trouvée -> retourner une erreur
        return DecisionFinale(
            categorie="autre_indetermine",
            priorite="basse",
            equipe="support_niveau_1",
            confiance=0.0,
            action="refus",
            validation_humaine_requise=True,
            incertitude_notes="Session not found or expired. Please start a new ticket.",
        )
    
    # Mettre à jour avec la réponse de l'utilisateur
    updated_session = update_session_with_user_response(ticket_id, user_response)
    if not updated_session:
        return DecisionFinale(
            categorie=session.categorie,
            priorite=session.priorite,
            equipe=session.equipe,
            confiance=0.9,
            action="resolution",
            validation_humaine_requise=False,
            incertitude_notes="No pending questions.",
        )
    
    # Si toutes les questions ont été répondues, continuer avec RAG + Agent
    if updated_session.etape_actuelle == "rag_agent":
        # Reconstituer le texte complèt avec les réponses de l'utilisateur
        contexte_diagnostic = updated_session.contexte_diagnostic or {}
        
        # Recréer un pseudo-ticket avec toutes les informations
        original_text = session.decision_finale.resume_probleme if session.decision_finale else ""
        responses_text = " | ".join(
            f"Q: {q} A: {updated_session.reponses_utilisateur.get(q, '')}"
            for q in session.questions_restantes
        )
        combined_text = f"{original_text}\n{responses_text}"
        
        # 4. RAG avec le texte complété
        with Timer() as t:
            rag_result = answer_with_citations(combined_text, use_llm=True)
        log_step("rag_continuation", {"query": combined_text}, rag_result.model_dump(), t.elapsed)
        
        # 5. Agent + outils
        contexte_agent = contexte_diagnostic.copy()
        contexte_agent["utilisateur_id"] = ""
        contexte_agent["ticket_id"] = ticket_id
        with Timer() as t:
            tool_logs = run_agent(combined_text, updated_session.categorie, contexte_agent)
        log_step("agent_continuation", {"categorie": updated_session.categorie},
                  {"appels": [l.model_dump() for l in tool_logs]}, t.elapsed)
        
        # 6. Décision finale
        validation_requise = (
            updated_session.categorie == "cybersecurite"
            or any(l.statut == "refuse" for l in tool_logs)
            or not rag_result.reponse_suffisamment_soutenue
        )
        action = "escalade" if validation_requise else "resolution"
        
        decision = DecisionFinale(
            categorie=updated_session.categorie,
            priorite=updated_session.priorite,
            equipe=updated_session.equipe,
            confiance=0.85,  # Légèrement réduit car basé sur des réponses incomplètes
            informations_manquantes=[],
            action=action,
            sources=[s.document_id for s in rag_result.sources],
            validation_humaine_requise=validation_requise,
            resume_probleme=combined_text,
            diagnostic=contexte_diagnostic.get("symptomes"),
            etapes_resolution=[rag_result.reponse_proposee] if rag_result.reponse_proposee else [],
            outils_utilises=[l.nom_outil for l in tool_logs],
            incertitude_notes=None if rag_result.reponse_suffisamment_soutenue else "No sufficiently relevant source was found.",
        )
        
        # Sauvegarder la décision finale dans la session
        update_session_with_decision(ticket_id, decision)
        log_decision_finale(ticket_id, decision.model_dump())
        return decision
    
    # Sinon, il reste des questions -> retourner l'état courant
    return DecisionFinale(
        categorie=updated_session.categorie,
        priorite=updated_session.priorite,
        equipe=updated_session.equipe,
        confiance=0.7,
        action="demande_information",
        validation_humaine_requise=False,
        resume_probleme="",
        questions_a_poser=updated_session.questions_restantes,
    )
