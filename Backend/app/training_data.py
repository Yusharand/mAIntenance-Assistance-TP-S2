"""
Jeu de données d'entraînement pour la classification des tickets — Personne 1.

MÉTHODOLOGIE :
Ces exemples sont volontairement écrits à la main pour couvrir chaque catégorie
avec des formulations variées (registre familier, fautes, phrases courtes/longues)
car le sujet précise explicitement que les données réelles contiennent des fautes
d'orthographe, formulations vagues, etc. (section 7).

En conditions réelles de hackathon : remplacer/enrichir avec l'historique de
tickets fourni par l'organisation (data/tickets_history.json) dès qu'il est
disponible, et refaire l'entraînement -> aucune valeur numérique de ce module
n'est fixée "à la main" sans donnée, conformément au principe déjà retenu
sur l'IPEF : les poids/probabilités sortent du modèle entraîné sur les données,
pas d'une estimation qualitative.
"""

TRAINING_DATA = [
    # comptes_authentification
    ("Je n'arrive plus à me connecter, mot de passe oublié", "comptes_authentification"),
    ("Mon compte est verrouillé après plusieurs tentatives", "comptes_authentification"),
    ("impossible de me logger sur mon compte ce matin", "comptes_authentification"),
    ("j'ai oublié mon mot de passe pouvez vous le reinitialiser", "comptes_authentification"),
    ("Le systeme dit identifiant ou mot de passe incorrect", "comptes_authentification"),
    ("session expirée en boucle je ne peux pas m'authentifier", "comptes_authentification"),
    ("mon compte a ete bloqué je ne sais pas pourquoi", "comptes_authentification"),
    ("besoin de reinitialiser mon mdp svp", "comptes_authentification"),

    # reseau_connectivite
    ("Plus de connexion internet depuis ce matin au bureau", "reseau_connectivite"),
    ("le wifi ne fonctionne plus dans la salle de reunion", "reseau_connectivite"),
    ("connexion tres lente impossible de charger les pages", "reseau_connectivite"),
    ("le vpn narrive pas a se connecter depuis chez moi", "reseau_connectivite"),
    ("perte de reseau intermittente toutes les 10 minutes", "reseau_connectivite"),
    ("aucun acces internet sur tout mon etage", "reseau_connectivite"),
    ("le reseau local est tres instable aujourdhui", "reseau_connectivite"),
    ("impossible de joindre le serveur distant via vpn", "reseau_connectivite"),

    # materiel_informatique
    ("mon ordinateur ne s'allume plus du tout", "materiel_informatique"),
    ("l'ecran de mon pc reste noir au demarrage", "materiel_informatique"),
    ("le clavier de mon portable ne repond plus", "materiel_informatique"),
    ("panne materielle sur mon poste de travail", "materiel_informatique"),
    ("la souris ne fonctionne plus depuis hier", "materiel_informatique"),
    ("mon pc portable chauffe enormement et s'eteint seul", "materiel_informatique"),
    ("le disque dur fait un bruit bizarre et l'ordi rame", "materiel_informatique"),
    ("batterie du laptop ne charge plus", "materiel_informatique"),

    # logiciels_applications
    ("l'application comptable ne demarre plus du tout", "logiciels_applications"),
    ("le logiciel plante des que je l'ouvre", "logiciels_applications"),
    ("erreur au lancement de word je ne comprends pas le message", "logiciels_applications"),
    ("mon navigateur se ferme tout seul en permanence", "logiciels_applications"),
    ("l'appli crm affiche une page blanche", "logiciels_applications"),
    ("impossible d'installer la mise a jour du logiciel", "logiciels_applications"),
    ("le programme de facturation freeze systematiquement", "logiciels_applications"),
    ("bug affichage sur l'application interne rh", "logiciels_applications"),

    # imprimantes_peripheriques
    ("l'imprimante du service ne repond plus", "imprimantes_peripheriques"),
    ("impossible d'imprimer depuis mon poste", "imprimantes_peripheriques"),
    ("le scanner narrive pas a numeriser les documents", "imprimantes_peripheriques"),
    ("bourrage papier permanent sur l'imprimante", "imprimantes_peripheriques"),
    ("l'imprimante affiche cartouche vide alors qu'elle est neuve", "imprimantes_peripheriques"),
    ("le fax ne recoit plus aucun document", "imprimantes_peripheriques"),
    ("impossible de connecter l'imprimante en wifi", "imprimantes_peripheriques"),

    # droits_acces
    ("je n'ai plus acces au dossier partagé comptabilite", "droits_acces"),
    ("besoin d'un acces a l'application rh pour mon nouveau poste", "droits_acces"),
    ("acces refusé au partage reseau du service marketing", "droits_acces"),
    ("je ne peux plus consulter le drive de l'equipe", "droits_acces"),
    ("demande d'acces au logiciel de gestion de projet", "droits_acces"),
    ("mes droits sur le serveur ont ete supprimés par erreur", "droits_acces"),
    ("acces manquant a la boite mail partagée du service", "droits_acces"),

    # cybersecurite
    ("j'ai recu un email suspect qui demande mes identifiants", "cybersecurite"),
    ("je pense que mon poste est infecté par un virus", "cybersecurite"),
    ("courriel de phishing recu ce matin avec un lien douteux", "cybersecurite"),
    ("mon ordinateur affiche des popups etranges depuis hier", "cybersecurite"),
    ("quelqu'un a peut etre acceder a mon compte sans autorisation", "cybersecurite"),
    ("j'ai cliqué sur un lien suspect par erreur", "cybersecurite"),
    ("alerte antivirus déclenchée sur mon poste", "cybersecurite"),
    ("comportement anormal du systeme possible intrusion", "cybersecurite"),

    # autre_indetermine
    ("ça ne marche pas", "autre_indetermine"),
    ("j'ai un probleme avec mon ordinateur", "autre_indetermine"),
    ("aide moi s'il vous plait c'est urgent", "autre_indetermine"),
    ("quelque chose ne va pas depuis ce matin", "autre_indetermine"),
    ("besoin d'assistance rapide", "autre_indetermine"),
]

# Mapping catégorie -> équipe compétente (règle métier simple, documentée et modifiable)
CATEGORIE_VERS_EQUIPE = {
    "comptes_authentification": "support_niveau_1",
    "reseau_connectivite": "infrastructure",
    "materiel_informatique": "support_niveau_1",
    "logiciels_applications": "support_niveau_2",
    "imprimantes_peripheriques": "support_niveau_1",
    "droits_acces": "administration_systeme",
    "cybersecurite": "securite",
    "autre_indetermine": "support_niveau_1",
}
