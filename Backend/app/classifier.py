"""
PERSONNE 1 — Classification & Diagnostic (axe noté : 20%)
=========================================================

DÉMARCHE / MÉTHODOLOGIE
------------------------
1. Classification de catégorie :
   TF-IDF (1-2 grammes de mots) + Régression Logistique multi-classes, entraînée
   sur `training_data.TRAINING_DATA`.
   Pourquoi ce choix plutôt qu'un LLM en few-shot ou des règles pures ?
     - Data-driven et traçable : aucune probabilité n'est fixée à la main, tout
       sort de l'apprentissage sur les exemples fournis (principe : pas de poids
       numérique sans source justifiable).
     - Gratuit, aucun appel API, latence quasi nulle -> bon compromis pour un
       hackathon de 8h où la fiabilité de la démo compte plus que la sophistication.
     - `predict_proba` donne une confiance réellement calibrée sur le modèle
       (contrairement à un score de règle inventé).
   Limite assumée et à documenter dans le rapport : le jeu d'entraînement est
   petit (~55 exemples) et écrit à la main -> à réentraîner sur l'historique réel
   de tickets (data/tickets_history.json) dès qu'il est disponible pour un vrai
   test de généralisation (voir evaluate_classifier()).

2. Priorité :
   Score composite = sévérité de base de la catégorie (cybersécurité et réseau
   plus critiques par nature) + bonus si mots-clés d'urgence/impact détectés.
   Volontairement PAS un modèle ML séparé : on n'a pas de données étiquetées en
   priorité assez nombreuses pour ce sous-problème -> on utilise une règle
   explicite et justifiée plutôt qu'un modèle mal entraîné sur trop peu de
   données (cf. limite documentée plus haut, même logique que pour l'IPEF :
   ne pas produire un chiffre non traçable).

3. Diagnostic (extraction d'informations) :
   Extraction par règles (mots-clés / expressions régulières) des champs demandés
   section 3.2 du sujet. Une vraie solution NER/LLM serait plus robuste mais les
   règles suffisent pour la démo et restent 100% explicables au jury.

ÉVALUATION
----------
`evaluate_classifier()` fait un split train/test stratifié et calcule accuracy
et F1 par catégorie -> résultats à copier dans le rapport technique et dans
data/resultats_evaluation.json (livrable 6).
"""
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

from app.schemas import ClassificationResult, DiagnosticResult, TicketInput
from app.training_data import TRAINING_DATA, CATEGORIE_VERS_EQUIPE

CATEGORIES = list(CATEGORIE_VERS_EQUIPE.keys())


# ---------------------------------------------------------------------------
# 1. CLASSIFICATION DE CATÉGORIE (TF-IDF + Régression Logistique)
# ---------------------------------------------------------------------------

def _build_pipeline() -> Pipeline:
    """Construit le pipeline TF-IDF + LogisticRegression.
    Séparé de l'entraînement pour pouvoir le reconstruire facilement (ex: si on
    veut changer les hyperparamètres pour l'évaluation)."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,           # dataset petit -> on garde tous les mots
            strip_accents="unicode",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",  # catégories déséquilibrées possibles (section 7)
        )),
    ])


@lru_cache(maxsize=1)
def get_trained_model() -> Pipeline:
    """Entraîne le modèle une seule fois (mis en cache) sur TOUT le jeu de
    données disponible. Utilisé en production/démo, PAS pour l'évaluation
    (voir evaluate_classifier() qui fait un vrai split train/test séparé)."""
    textes = [t for t, _ in TRAINING_DATA]
    labels = [c for _, c in TRAINING_DATA]
    pipeline = _build_pipeline()
    pipeline.fit(textes, labels)
    return pipeline


def classify_ticket(ticket: TicketInput) -> ClassificationResult:
    model = get_trained_model()
    texte = ticket.texte

    proba = model.predict_proba([texte])[0]
    classes = model.classes_
    idx_meilleur = proba.argmax()
    categorie = classes[idx_meilleur]
    confiance = float(proba[idx_meilleur])

    priorite = _determiner_priorite(texte, categorie)
    equipe = CATEGORIE_VERS_EQUIPE.get(categorie, "support_niveau_1")

    return ClassificationResult(
        categorie=categorie,
        priorite=priorite,
        equipe=equipe,
        confiance=round(confiance, 3),
    )


def evaluate_classifier(test_size: float = 0.25, random_state: int = 42) -> dict:
    """Évaluation honnête : split train/test, jamais évalué sur les données
    d'entraînement. À lancer via `python -m app.classifier` ou dans le rapport.
    Retourne un dict prêt à être sauvegardé en JSON (livrable 6)."""
    textes = [t for t, _ in TRAINING_DATA]
    labels = [c for _, c in TRAINING_DATA]

    X_train, X_test, y_train, y_test = train_test_split(
        textes, labels, test_size=test_size, random_state=random_state, stratify=labels
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 3),
        "taille_train": len(X_train),
        "taille_test": len(X_test),
        "rapport_par_categorie": classification_report(
            y_test, y_pred, zero_division=0, output_dict=True
        ),
        "limite": (
            "Jeu de test très petit (dataset de démo écrit à la main) : ces "
            "chiffres illustrent la méthode, pas une performance généralisable. "
            "À refaire sur l'historique réel de tickets avant la remise finale."
        ),
    }


# ---------------------------------------------------------------------------
# 2. PRIORITÉ (règle explicite et justifiée, pas de ML sur trop peu de données)
# ---------------------------------------------------------------------------

# Sévérité de base par catégorie (0 = basse ... 3 = critique), justifiée par le
# fait qu'une panne réseau ou un incident cybersécurité a structurellement plus
# d'impact organisationnel qu'un mot de passe oublié individuel.
SEVERITE_BASE = {
    "cybersecurite": 2,
    "reseau_connectivite": 2,
    "materiel_informatique": 1,
    "logiciels_applications": 1,
    "comptes_authentification": 1,
    "droits_acces": 1,
    "imprimantes_peripheriques": 0,
    "autre_indetermine": 1,
}

MOTS_URGENCE = ["urgent", "bloqué", "bloque", "impossible de travailler",
                "immédiat", "immediat", "critique", "grave"]
MOTS_IMPACT_LARGE = ["tous les", "toute l'équipe", "toute l'equipe", "tout le service",
                      "personne ne peut", "plus personne", "l'ensemble"]

NIVEAUX = ["basse", "moyenne", "haute", "critique"]


def _determiner_priorite(texte: str, categorie: str) -> str:
    texte_lower = texte.lower()
    score = SEVERITE_BASE.get(categorie, 1)

    if any(m in texte_lower for m in MOTS_URGENCE):
        score += 1
    if any(m in texte_lower for m in MOTS_IMPACT_LARGE):
        score += 1  # impact sur plusieurs personnes -> escalade de priorité

    score = max(0, min(score, len(NIVEAUX) - 1))
    return NIVEAUX[score]


# ---------------------------------------------------------------------------
# 3. DIAGNOSTIC — extraction d'informations par règles (section 3.2 du sujet)
# ---------------------------------------------------------------------------

EQUIPEMENTS_CONNUS = ["ordinateur", "pc portable", "portable", "poste", "laptop",
                      "imprimante", "scanner", "écran", "ecran", "clavier", "souris"]
APPLICATIONS_CONNUES = ["word", "excel", "outlook", "crm", "vpn", "messagerie",
                         "logiciel de facturation", "application rh", "teams", "drive"]
MOTS_MOMENT = {
    r"\bce matin\b": "ce matin",
    r"\bhier\b": "hier",
    r"\bdepuis\s+\d+\s*(jour|jours|heure|heures|semaine|semaines)": None,  # capturé dynamiquement
    r"\baujourd'?hui\b": "aujourd'hui",
}
MOTS_MANIPULATIONS = ["j'ai redémarré", "j'ai redemarre", "j'ai déjà essayé",
                       "j'ai deja essaye", "j'ai réinstallé", "j'ai reinstalle",
                       "j'ai débranché", "j'ai debranche", "j'ai testé", "j'ai teste"]
MOTS_IMPACT = ["je ne peux plus travailler", "bloqué", "bloque", "impossible de",
               "urgent", "toute l'équipe", "toute l'equipe"]


def _detecter_element(texte_lower: str, liste: list[str]) -> str | None:
    for element in liste:
        if element in texte_lower:
            return element
    return None


def _detecter_moment(texte_lower: str) -> str | None:
    m = re.search(r"depuis\s+\d+\s*(jour|jours|heure|heures|semaine|semaines)", texte_lower)
    if m:
        return m.group(0)
    if "ce matin" in texte_lower:
        return "ce matin"
    if "hier" in texte_lower:
        return "hier"
    if "aujourd'hui" in texte_lower or "aujourdhui" in texte_lower:
        return "aujourd'hui"
    return None


def extract_diagnostic_info(ticket: TicketInput) -> DiagnosticResult:
    texte = ticket.texte
    texte_lower = texte.lower()

    equipement = _detecter_element(texte_lower, EQUIPEMENTS_CONNUS)
    application = _detecter_element(texte_lower, APPLICATIONS_CONNUES)
    moment = _detecter_moment(texte_lower)
    manipulation = _detecter_element(texte_lower, MOTS_MANIPULATIONS)
    impact = _detecter_element(texte_lower, MOTS_IMPACT)

    manquants: list[str] = []
    questions: list[str] = []

    # Un ticket trop court (< 4 mots) est presque toujours sous-spécifié
    # -> Scénario 3 du sujet ("Demande incomplète")
    trop_court = len(texte.split()) < 5

    if not equipement and not application:
        manquants.append("equipement_ou_application")
        questions.append("Quel équipement ou quelle application est concerné(e) précisément ?")
    if not moment:
        manquants.append("moment_apparition")
        questions.append("Depuis quand rencontrez-vous ce problème ?")
    if trop_court:
        manquants.append("description_detaillee")
        questions.append("Pouvez-vous décrire plus précisément le problème rencontré et son contexte ?")

    return DiagnosticResult(
        equipement=equipement,
        application_service=application,
        symptomes=texte,
        moment_apparition=moment,
        impact_activite=impact,
        manipulations_effectuees=manipulation,
        informations_manquantes=manquants,
        questions_a_poser=questions,
    )


if __name__ == "__main__":
    import json
    resultats = evaluate_classifier()
    print(json.dumps(resultats, indent=2, ensure_ascii=False, default=str))
