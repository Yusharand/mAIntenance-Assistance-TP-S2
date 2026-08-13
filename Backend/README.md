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

## Approche choisie pour la classification / routage (P1)
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

## Fonctionnement du RAG (P2)
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

## Outils accessibles à l'agent (P3)
Voir `app/tools.py` — 4 outils de consultation (lecture seule, jamais de
validation requise) + 4 outils d'action (`OUTILS_SENSIBLES`, nécessitent
toujours une validation humaine, voir `app/guardrails.py`). La sélection
d'outils par l'agent est déterministe et fondée sur des règles explicites par
catégorie (`app/agent.py::build_tool_plan`), auditables une par une, plutôt
que sur du tool-calling LLM — plus prévisible pour une démo de 8h.

## Stratégie d'évaluation
- P1 : split train/test stratifié, accuracy + F1 par catégorie (`app/classifier.py::evaluate_classifier`)
- P2 : precision@k sur un jeu de 6 requêtes de référence (`app/rag.py::evaluate_rag`)
- Résultats combinés générés dans `data/resultats_evaluation.json` via
  `python -m tests.run_evaluation`
- P3 : pas de métrique quantitative (pas de "bonne réponse" unique pour une
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

---

## Répartition des tâches (équipe de 4, 8h30 → 16h30)

| Rôle | Personne | Fichiers dont il/elle est responsable |
|---|---|---|
| Classification & Diagnostic | **P1** | `app/classifier.py` |
| RAG / recherche documentaire | **P2** | `app/rag.py`, ingestion `data/knowledge_base/` |
| Agent, outils, sécurité | **P3** | `app/agent.py`, `app/tools.py`, `app/guardrails.py` |
| Orchestration, observabilité, démo | **P4** | `app/orchestrator.py`, `app/observability.py`, `app/main.py`, `demo/streamlit_app.py` |

### Planning horaire

**8h30 – 9h00 — Cadrage (tous ensemble)**
Lecture du sujet, validation de la répartition ci-dessus, choix définitif du LLM
(Groq ou Gemini gratuit), création du repo Git partagé, chacun clone le squelette fourni.
Les schémas `app/schemas.py` sont validés et NE CHANGENT PLUS après 9h00 — c'est le
contrat entre les 4 modules.

**9h00 – 11h00 — Sprint 1 (travail en parallèle)**
- P1 : première version de `classify_ticket()` (règles ou few-shot) + `extract_diagnostic_info()`
- P2 : ingestion de 5-10 documents de test dans la KB, pipeline chunking + embeddings + recherche
- P3 : implémentation des 8 outils (`tools.py`) sur les données factices fournies + `detect_prompt_injection()`
- P4 : squelette FastAPI fonctionnel (déjà fourni), squelette du dashboard Streamlit, mise en place du logging JSONL

**11h00 – 11h15 — Point de synchronisation #1**
Chacun montre sa fonction qui tourne isolément (même avec des résultats imparfaits).
P4 vérifie que tous les retours respectent bien les schémas Pydantic.

**11h15 – 13h00 — Sprint 2**
- P1 : amélioration de la classification, ajout du calcul de confiance, début du jeu de test étiqueté
- P2 : génération de réponses sourcées, gestion du seuil "réponse non soutenue"
- P3 : boucle `run_agent()` avec sélection d'outils, branchement des garde-fous sur les actions sensibles
- P4 : branchement complet de `orchestrator.py`, premier bout-en-bout sur un ticket simple

**13h00 – 13h30 — Pause déjeuner** (décalée si besoin selon l'avancement)

**13h30 – 15h00 — Intégration complète + les 4 scénarios**
Tout le monde sur `tests/scenarios.py` : faire passer les 4 scénarios obligatoires
un par un. C'est le moment où les vrais bugs d'intégration apparaissent — ne pas
commencer de nouvelle fonctionnalité durant ce créneau.

**15h00 – 16h00 — Finalisation**
- P1 & P2 : résultats d'évaluation (métriques classification + précision RAG), à mettre dans le rapport
- P3 : vérification finale des garde-fous, relecture sécurité
- P4 : dashboard d'observabilité présentable, README complété, rapport technique (structure du sujet section 9)

**16h00 – 16h30 — Répétition de la démo + checklist finale**
Un membre présente, un autre surveille le chrono, vérification de la checklist de
remise (section 11 du sujet) : code, fichier de lancement, interface, rapport,
jeux de tests, résultats, journal d'observabilité, README, 4 scénarios, sources
citées, schéma respecté, validation humaine visible.

### Règle d'or pendant les sprints
Chaque personne travaille contre les **schémas Pydantic**, pas contre l'implémentation
des autres. Tant que `classify_ticket()` retourne un `ClassificationResult` valide,
peu importe si c'est fait avec 3 règles regex ou un LLM — P4 peut déjà l'intégrer
dans l'orchestrateur. Ça permet aux 4 modules d'avancer vraiment en parallèle.
