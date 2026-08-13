
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
        )
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

MOTS_URGENCE = ["urgent", "blocked", "can't work", "cannot work",
                "immediate", "immediately", "critical", "severe", "asap"]
MOTS_IMPACT_LARGE = ["everyone", "the whole team", "the entire team", "the whole department",
                      "nobody can", "no one can", "all of us"]

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

EQUIPEMENTS_CONNUS = ["computer", "laptop", "workstation", "desktop", "pc",
                      "printer", "scanner", "screen", "monitor", "keyboard", "mouse"]
APPLICATIONS_CONNUES = ["word", "excel", "outlook", "crm", "vpn", "email",
                         "mail server", "mail", "billing software", "hr application",
                         "teams", "drive", "server"]
MOTS_MOMENT = {
    r"\bthis morning\b": "this morning",
    r"\byesterday\b": "yesterday",
    r"\bsince\s+\d+\s*(day|days|hour|hours|week|weeks)": None,  # captured dynamically
    r"\btoday\b": "today",
}
MOTS_MANIPULATIONS = ["i restarted", "i already tried", "i tried",
                       "i reinstalled", "i unplugged", "i tested",
                       "i rebooted", "i checked"]
MOTS_IMPACT = ["i can't work anymore", "i cannot work", "blocked", "unable to",
               "urgent", "the whole team", "the entire team"]


def _detecter_element(texte_lower: str, liste: list[str]) -> str | None:
    for element in liste:
        if element in texte_lower:
            return element
    return None


def _detecter_moment(texte_lower: str) -> str | None:
    m = re.search(r"since\s+\d+\s*(day|days|hour|hours|week|weeks)", texte_lower)
    if m:
        return m.group(0)
    if "this morning" in texte_lower:
        return "this morning"
    if "yesterday" in texte_lower:
        return "yesterday"
    if "today" in texte_lower:
        return "today"
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
        questions.append("Which device or application exactly is affected?")
    if not moment:
        manquants.append("moment_apparition")
        questions.append("Since when have you been experiencing this issue?")
    if trop_court:
        manquants.append("description_detaillee")
        questions.append("Could you describe the problem and its context in more detail?")

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
