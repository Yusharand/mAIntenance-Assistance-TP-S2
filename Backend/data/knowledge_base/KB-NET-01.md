# KB-NET-01 — Network outage or slowness

## Preliminary diagnosis
1. Check the network service status via `verifier_etat_service("reseau_local")`.
2. Check whether an active network-type incident already exists via
   `rechercher_incidents_actifs("reseau_connectivite")` before creating a duplicate.
3. Ask the user whether they are on wired or wifi, and whether the issue
   affects a single workstation or several people in the department.

## Level-1 resolution
- Restart the local router/switch if the issue affects several workstations.
- If only one workstation is affected: check the network cable, restart the
  network adapter, test with another port.

## Escalation
If the incident affects more than 5 users simultaneously, escalate
immediately to the infrastructure team without waiting for user
confirmation (large impact = high priority by default).
