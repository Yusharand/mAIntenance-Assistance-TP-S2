# KB-ACCESS-01 — Demandes de droits d'accès

## Procédure standard
1. Vérifier l'identité et le service de l'utilisateur via `rechercher_utilisateur`.
2. Vérifier que la demande correspond bien au périmètre de son service
   (un accès en dehors du périmètre habituel nécessite validation du responsable).
3. Toute modification de droits est une action sensible : elle nécessite
   systématiquement une validation humaine avant application, même pour une
   simple demande d'accès à un dossier partagé.

## Cas particulier
Une suppression de droits non demandée par l'utilisateur (ex: "mes droits ont
été supprimés par erreur") doit être traitée comme un incident potentiel de
sécurité et vérifiée avant toute réattribution automatique.
