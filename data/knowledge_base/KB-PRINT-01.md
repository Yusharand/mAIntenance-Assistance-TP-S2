# KB-PRINT-01 — Printing issues

## Standard procedure
1. Check the printer's status via `consulter_equipement`.
2. Check the print queue on the user's workstation.
3. Restart the print spooler if documents remain stuck in the queue.

## Common cases
- "Cartridge empty" when it is actually new: often a detection issue,
  remove and reinsert the cartridge before replacing it.
- Repeated paper jams: check the paper tray and the type of paper used.
- Cannot print over the network: check that the printer is on the same
  network as the workstation, restart the print service.
