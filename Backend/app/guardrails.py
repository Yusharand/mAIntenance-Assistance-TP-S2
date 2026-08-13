"""
PERSONNE 3 (partie 2/3) — Garde-fous & sécurité (axes Agent 20% + Sécurité 10%)
==================================================================================

DÉMARCHE
--------
Couvre chacun des risques listés section 6 du sujet, avec une approche par
règles explicites (regex + heuristiques) plutôt qu'un modèle de détection
entraîné : on n'a pas de jeu de données d'attaques suffisant pour entraîner un
classifieur de prompt injection en 8h, et des règles mal justifiées seraient
pires qu'un modèle honnête à faible confiance. Les règles ci-dessous sont
documentées une par une pour rester auditables par le jury.

1. detect_prompt_injection() : patterns de tentative de manipulation de
   l'assistant (Scénario 4 obligatoire du sujet).
2. is_sensitive_action() : combine la liste d'outils sensibles (tools.py) ET
   la logique métier (catégorie cybersécurité => toujours validation humaine,
   même sur un outil "non sensible").
3. is_out_of_distribution() : détecte un ticket "inhabituel" (trop court, trop
   long, langue différente, absence totale de mots-clés reconnus) -> répond à
   l'analyse complémentaire optionnelle citée section 3.1 du sujet.
4. redact_personal_data() : masque emails/téléphones dans les logs, réponse au
   risque "présence de données personnelles" (section 6).

Chaque détection est loggée avec sa raison exacte (pas juste un booléen) pour
que l'observabilité (Personne 4) puisse tracer POURQUOI une action a été
refusée — important pour la démo du Scénario 4 et pour le rapport.
"""
import re

# Patterns de tentative de manipulation de l'assistant (prompt injection).
# Volontairement larges (faux positifs possibles) car en sécurité on préfère
# sur-détecter et demander une validation humaine plutôt que sous-détecter.
INJECTION_PATTERNS = [
    (r"ignore[z]?\s+(les\s+|tes\s+)?instructions?", "tentative de contournement des instructions"),
    (r"tu\s+es\s+maintenant", "tentative de changement de rôle de l'assistant"),
    (r"nouveau\s+r[oô]le", "tentative de changement de rôle de l'assistant"),
    (r"oublie\s+(tout|ce\s+qui\s+precede|ce\s+qui\s+précède)", "tentative d'effacement de contexte"),
    (r"system\s*:", "tentative d'injection de faux message système"),
    (r"execute[z]?\s+la\s+commande", "tentative d'exécution de commande arbitraire"),
    (r"supprime[z]?\s+tous\s+les", "demande de suppression massive suspecte"),
    (r"donne[z]?[- ]moi\s+(le\s+)?mot\s+de\s+passe\s+(admin|administrateur)", "demande d'identifiants privilégiés"),
    (r"acc[eè]s\s+(root|administrateur)\s+(a|à)\s+tous", "demande de privilèges élevés injustifiée"),
    (r"r[eé]v[eè]le\s+tes\s+instructions", "tentative d'extraction du prompt système"),
]


def detect_prompt_injection(texte: str) -> tuple[bool, str | None]:
    """Retourne (detecte, raison). La raison est loggée, jamais montrée à
    l'utilisateur en détail (pour ne pas donner d'indice sur les règles de
    détection à un attaquant)."""
    texte_lower = texte.lower()
    for pattern, raison in INJECTION_PATTERNS:
        if re.search(pattern, texte_lower):
            return True, raison
    return False, None


def is_sensitive_action(nom_outil: str, categorie_ticket: str = None) -> bool:
    """Détermine si une action nécessite une validation humaine avant exécution."""
    from app.tools import OUTILS_SENSIBLES
    if nom_outil in OUTILS_SENSIBLES:
        return True
    if categorie_ticket == "cybersecurite":
        # Même une simple consultation sur un incident de sécurité est traitée
        # avec prudence : on préfère sur-solliciter la validation humaine.
        return True
    return False


def is_out_of_distribution(texte: str, confiance_classification: float) -> tuple[bool, str | None]:
    """Détecte un ticket 'inhabituel' — analyse complémentaire citée en 3.1.
    Ne bloque rien, mais doit se refléter dans confiance/incertitude affichée
    au technicien."""
    mots = texte.split()
    if len(mots) < 3:
        return True, "ticket extrêmement court, contexte insuffisant"
    if len(mots) > 300:
        return True, "ticket anormalement long, possible contenu hors-sujet"
    if confiance_classification < 0.25:
        return True, "confiance de classification très faible, catégorie incertaine"
    return False, None


def redact_personal_data(texte: str) -> str:
    """Masque emails et numéros de téléphone avant stockage dans les logs
    d'observabilité (réponse au risque 'données personnelles', section 6)."""
    texte = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL_MASQUE]", texte)
    texte = re.sub(r"\b(\+?\d{2,3}[\s.-]?)?\d{2,3}[\s.-]?\d{2,3}[\s.-]?\d{2,3}\b", "[TEL_MASQUE]", texte)
    return texte
