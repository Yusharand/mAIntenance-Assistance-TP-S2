# KB-NET-01 — Panne ou lenteur réseau

## Diagnostic préalable
1. Vérifier l'état du service réseau via `verifier_etat_service("reseau_local")`.
2. Vérifier s'il existe déjà un incident actif de type réseau via
   `rechercher_incidents_actifs("reseau_connectivite")` avant de créer un doublon.
3. Demander à l'utilisateur s'il est en filaire ou en wifi, et si le problème
   touche un seul poste ou plusieurs personnes du service.

## Résolution niveau 1
- Redémarrer le routeur/switch local si le problème touche plusieurs postes.
- Si un seul poste est concerné : vérifier le câble réseau, redémarrer la carte
  réseau, tester avec un autre port.

## Escalade
Si l'incident touche plus de 5 utilisateurs simultanément, escalader
immédiatement vers l'équipe infrastructure sans attendre la confirmation de
l'utilisateur (impact large = priorité haute par défaut).
