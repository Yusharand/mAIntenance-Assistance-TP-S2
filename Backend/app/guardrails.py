import re

# Patterns de tentative de manipulation de l'assistant (prompt injection).
# Volontairement larges (faux positifs possibles) car en sécurité on préfère
# sur-détecter et demander une validation humaine plutôt que sous-détecter.
INJECTION_PATTERNS = [
    (r"ignore\s+(your\s+|all\s+|previous\s+)?instructions?", "tentative de contournement des instructions"),
    (r"you\s+are\s+now\s+", "tentative de changement de rôle de l'assistant"),
    (r"new\s+role", "tentative de changement de rôle de l'assistant"),
    (r"forget\s+(everything|all\s+of\s+the\s+above|the\s+above)", "tentative d'effacement de contexte"),
    (r"system\s*:", "tentative d'injection de faux message système"),
    (r"execute\s+the\s+command", "tentative d'exécution de commande arbitraire"),
    (r"delete\s+all\s+", "demande de suppression massive suspecte"),
    (r"give\s+me\s+the\s+(admin|administrator)\s+password", "demande d'identifiants privilégiés"),
    (r"(root|administrator)\s+access\s+(to|for)\s+everyone", "demande de privilèges élevés injustifiée"),
    (r"reveal\s+your\s+(system\s+)?instructions", "tentative d'extraction du prompt système"),
    (r"disregard\s+(your\s+|all\s+|previous\s+)?instructions?", "tentative de contournement des instructions"),
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
