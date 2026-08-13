"""
PERSONNE 4 — Interface de démonstration + tableau de bord d'observabilité.
Lancer avec : streamlit run demo/streamlit_app.py
(Nécessite que l'API FastAPI tourne en parallèle sur localhost:8000,
 OU appeler directement process_ticket() sans passer par HTTP si vous
 voulez un seul process à lancer pour la démo.)
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from app.schemas import TicketInput
from app.orchestrator import process_ticket
from app.observability import read_all_logs

st.set_page_config(page_title="mAIntenance & Assistance", layout="wide")
st.title("🛠️ mAIntenance & Assistance")

tab_demo, tab_obs = st.tabs(["Démonstration", "Observabilité"])

with tab_demo:
    st.subheader("Soumettre un ticket")
    texte = st.text_area("Description du problème", height=120,
                          placeholder="Ex : Je n'arrive plus à me connecter à mon compte depuis ce matin, c'est urgent.")
    ticket_id = st.text_input("ID du ticket (démo)", value="TCK-DEMO-001")

    if st.button("Analyser le ticket") and texte.strip():
        ticket = TicketInput(ticket_id=ticket_id, texte=texte)
        with st.spinner("Traitement en cours..."):
            decision = process_ticket(ticket)

        st.json(decision.model_dump())

        if decision.validation_humaine_requise:
            st.warning("⚠️ Validation humaine requise avant toute action.")
            col1, col2 = st.columns(2)
            if col1.button("✅ Approuver l'action"):
                st.success("Action approuvée (à implémenter : déclencher l'outil réel).")
            if col2.button("❌ Rejeter"):
                st.error("Action rejetée.")

with tab_obs:
    st.subheader("Journal d'observabilité")
    logs = read_all_logs()
    if not logs:
        st.info("Aucun log pour l'instant. Soumettez un ticket dans l'onglet Démonstration.")
    else:
        df = pd.json_normalize(logs)
        st.dataframe(df, use_container_width=True)

        if "latence_s" in df.columns:
            st.subheader("Latence par étape")
            st.bar_chart(df.dropna(subset=["latence_s"]).groupby("step")["latence_s"].mean())
