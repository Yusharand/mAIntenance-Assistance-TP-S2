"""
Version corrigée : génère les 8 catégories attendues par app/classifier.py
(alignées avec CATEGORIE_VERS_EQUIPE et SEVERITE_BASE), à partir du dataset
Kaggle adisongoh/it-service-ticket-classification-dataset.

Problème résolu par rapport à la v1 :
  Le CSV brut n'a que 8 "Topic_group" (Hardware, Access, Storage, Purchase,
  Internal Project, Administrative rights, HR Support, Miscellaneous) qui ne
  correspondent PAS aux 8 catégories métier attendues (pas de "réseau",
  "imprimantes", "authentification", "cybersécurité" dans le dataset brut).
  On résout ça par extraction de sous-ensembles par mots-clés à l'intérieur
  des groupes Hardware / Access / Miscellaneous, avant de retomber sur le
  reste comme catégories plus génériques.

Usage:
    python scripts/build_training_data.py
"""

import pandas as pd
import re
from pathlib import Path

RAW_PATH = Path(__file__).parent / "all_tickets_processed_improved_v3.csv"

df = pd.read_csv(RAW_PATH)
df["texte"] = df["Document"].astype(str).str.strip()
df = df[df["texte"].str.len() > 15].copy()
df["texte_lower"] = df["texte"].str.lower()

N_PAR_CATEGORIE = 150

# --- Mots-clés pour extraire les sous-catégories fines ---------------------
KEYWORDS = {
    "reseau_connectivite": ["wifi", "vpn", "network", "internet", "connection lost",
                             "router", "ethernet", "wlan", "connectivity"],
    "imprimantes_peripheriques": ["printer", "print ", "scanner", "toner", "cartridge"],
    "comptes_authentification": ["password", "login", "log in", "locked out",
                                  "authentication", "username", "account locked", "reset"],
    "cybersecurite": ["phishing", "virus", "malware", "security breach",
                       "suspicious", "hacked", "spam", "fraud"],
}

# Ordre de priorité d'assignation : un ticket qui matche plusieurs mots-clés
# est affecté à la première catégorie de cette liste qui matche (évite les
# doublons entre catégories).
ORDRE_PRIORITE = ["cybersecurite", "comptes_authentification",
                   "reseau_connectivite", "imprimantes_peripheriques"]

deja_pris = pd.Series(False, index=df.index)
categorie_series = pd.Series(index=df.index, dtype=object)

for cat in ORDRE_PRIORITE:
    kws = KEYWORDS[cat]
    pattern = "|".join(re.escape(k) for k in kws)
    mask = df["texte_lower"].str.contains(pattern, regex=True, na=False) & ~deja_pris
    categorie_series.loc[mask] = cat
    deja_pris |= mask

# --- Le reste retombe sur le mapping Topic_group classique -----------------
MAPPING_TOPIC_GROUP = {
    "Hardware": "materiel_informatique",
    "Access": "droits_acces",
    "Administrative rights": "droits_acces",
    "Miscellaneous": "logiciels_applications",
    "Storage": "autre_indetermine",
    "Purchase": "autre_indetermine",
    "Internal Project": "autre_indetermine",
    "HR Support": "autre_indetermine",
}

reste_mask = ~deja_pris
categorie_series.loc[reste_mask] = df.loc[reste_mask, "Topic_group"].map(MAPPING_TOPIC_GROUP)

df["categorie"] = categorie_series
df = df.dropna(subset=["categorie"])

print("Répartition finale (avant échantillonnage) :")
print(df["categorie"].value_counts())

# --- Échantillonnage équilibré (max N_PAR_CATEGORIE par catégorie) ---------
echantillons = []
for cat, groupe in df.groupby("categorie"):
    n = min(N_PAR_CATEGORIE, len(groupe))
    echantillons.append(groupe.sample(n=n, random_state=42))
    if n < N_PAR_CATEGORIE:
        print(f"⚠️ Catégorie '{cat}' : seulement {n} exemples disponibles (< {N_PAR_CATEGORIE})")

df_final = pd.concat(echantillons).sample(frac=1, random_state=42)

def nettoyer(texte: str) -> str:
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte[:500]

df_final["texte_clean"] = df_final["texte"].apply(nettoyer)

print(f"\nJeu final : {len(df_final)} tickets, {df_final['categorie'].nunique()} catégories")
print(df_final["categorie"].value_counts())

# --- Génération du fichier training_data.py ---------------------------------
OUTPUT_PATH = Path(__file__).parent.parent / "app" / "training_data.py"

lignes = [
    "# Généré automatiquement depuis le dataset Kaggle adisongoh/it-service-ticket-classification-dataset",
    "# Source : https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset (CC0)",
    "# Les 4 catégories réseau/imprimantes/authentification/cybersécurité sont",
    "# extraites par mots-clés depuis les groupes Hardware/Access/Miscellaneous",
    "# du dataset brut, qui ne les distingue pas nativement (voir scripts/build_training_data.py).",
    "",
    "TRAINING_DATA = [",
]
for _, row in df_final.iterrows():
    texte_echappe = row["texte_clean"].replace("\\", "\\\\").replace('"', '\\"')
    lignes.append(f'    ("{texte_echappe}", "{row["categorie"]}"),')
lignes.append("]")
lignes.append("")
lignes.append("CATEGORIE_VERS_EQUIPE = {")
lignes.append('    "materiel_informatique": "support_niveau_1",')
lignes.append('    "droits_acces": "securite_acces",')
lignes.append('    "logiciels_applications": "support_logiciels",')
lignes.append('    "comptes_authentification": "support_authentification",')
lignes.append('    "reseau_connectivite": "infrastructure",')
lignes.append('    "imprimantes_peripheriques": "support_peripheriques",')
lignes.append('    "cybersecurite": "securite",')
lignes.append('    "autre_indetermine": "support_niveau_1",')
lignes.append("}")

OUTPUT_PATH.write_text("\n".join(lignes), encoding="utf-8")
print(f"\n✅ Écrit : {OUTPUT_PATH} ({len(df_final)} exemples, {df_final['categorie'].nunique()} catégories)")
