# mAIntenance & Assistance

Assistant intelligent de support informatique — Hackathon AI Engineering & ML, ISPM.

## Lancement

```bash
python -m venv venv && source venv/bin/activate   # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
python run.py
```

- API : http://localhost:8000/docs
- Démo + observabilité : http://localhost:8501
- Tests des 4 scénarios obligatoires : `python -m tests.scenarios`

## Architecture

```
Ticket (texte libre)
   │
   ▼
[classifier.py]   catégorie · priorité · équipe · confiance
   │
   ▼
[classifier.py]   extraction des infos + questions ciblées si incomplet
   │  (si infos manquantes -> arrêt, action = demande_information)
   ▼
[rag.py]          recherche documentaire (ChromaDB) + citation des sources
   │
   ▼
[agent.py]        sélection et appel d'outils (tools.py), garde-fous (guardrails.py)
   │
   ▼
[orchestrator.py] assemble la DecisionFinale (schéma imposé, schemas.py)
   │
   ▼
[observability.py] logge chaque étape -> logs/observability.jsonl -> dashboard Streamlit
```

Chaque module correspond directement à un axe de notation du sujet (voir répartition
des tâches ci-dessous), ce qui permet de développer les 4 modules en parallèle avec
une interface (les schémas Pydantic de `app/schemas.py`) définie et figée dès le départ.

## Approche choisie pour la classification / routage
TF-IDF (1-2 grammes) + Régression Logistique multi-classes (`scikit-learn`),
entraînée sur `app/training_data.py` (~55 exemples écrits à la main, à
enrichir avec l'historique réel de tickets dès qu'il est disponible). Choisi
plutôt qu'un LLM en few-shot pour rester 100% traçable (`predict_proba` donne
une vraie confiance calibrée, aucune probabilité n'est fixée à la main) et
gratuit/local. La priorité est déterminée par une règle explicite (sévérité de
base par catégorie + bonus mots-clés d'urgence/impact) plutôt qu'un second
modèle ML, faute de données étiquetées suffisantes pour ce sous-problème —
détail justifié dans `app/classifier.py`. Limite assumée : accuracy faible sur
un jeu de test aussi réduit (~33%), documentée dans `evaluate_classifier()`.

## Fonctionnement du RAG
Recherche par similarité TF-IDF + cosinus (pas d'embeddings neuronaux, pour
rester léger et sans dépendance lourde à installer pendant le hackathon).
Chunking par section Markdown (`## titre`) plutôt que par nombre fixe de
tokens, car la KB est déjà structurée logiquement. Seuil de confiance
`SEUIL_CONFIANCE_RAG` : sous ce seuil, `reponse_suffisamment_soutenue=False`
et la réponse est signalée incertaine plutôt qu'inventée. Synthèse de réponse
EXTRACTIVE par défaut (concatène les passages sourcés, zéro risque
d'hallucination) ; `generer_reponse_llm()` montre où brancher un vrai appel
LLM si l'équipe dispose d'une clé API. Precision@3 = 100% sur le jeu de test
de 6 requêtes (`evaluate_rag()`), à relire avec un regard critique vu la
petite taille du corpus de test.

## Outils accessibles à l'agent
Voir `app/tools.py` — 4 outils de consultation (lecture seule, jamais de
validation requise) + 4 outils d'action (`OUTILS_SENSIBLES`, nécessitent
toujours une validation humaine, voir `app/guardrails.py`). La sélection
d'outils par l'agent est déterministe et fondée sur des règles explicites par
catégorie (`app/agent.py::build_tool_plan`), auditables une par une, plutôt
que sur du tool-calling LLM — plus prévisible pour une démo de 8h.

## Stratégie d'évaluation
- split train/test stratifié, accuracy + F1 par catégorie (`app/classifier.py::evaluate_classifier`)
- precision@k sur un jeu de 6 requêtes de référence (`app/rag.py::evaluate_rag`)
- Résultats combinés générés dans `data/resultats_evaluation.json` via
  `python -m tests.run_evaluation`
-  pas de métrique quantitative (pas de "bonne réponse" unique pour une
  séquence d'outils) — évalué qualitativement via les 4 scénarios obligatoires
  (`tests/scenarios.py`) : vérifier manuellement que les bons outils sont
  proposés et que les actions sensibles sont bien bloquées en attente de
  validation humaine.

## Mécanismes de sécurité
- Détection de prompt injection (`guardrails.detect_prompt_injection`)
- Validation humaine obligatoire pour les actions sensibles et les tickets cybersécurité
- Masquage des données personnelles dans les logs (`guardrails.redact_personal_data`)
- Réponse RAG signalée comme incertaine si aucune source suffisamment pertinente

## Limites connues
*(à compléter avant la remise — sois honnête, c'est noté positivement par le jury)*


