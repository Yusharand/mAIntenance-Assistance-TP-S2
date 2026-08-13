"""
Utilise le dataset Kaggle "Customer IT Support - Ticket Dataset"
(tobiasbueck/multilingual-customer-support-tickets) pour deux choses :

1. Extraire un jeu d'entraînement priorité (Low/Medium/Critical) -> app/training_priority.py
2. Construire une base de connaissances synthétique pour le RAG (P2)
   à partir des réponses d'agent, groupées par queue -> data/knowledge_base/*.md

Usage:
    python scripts/build_priority_and_kb.py

Prérequis:
    kaggle datasets download -d tobiasbueck/multilingual-customer-support-tickets -p data/raw/ --unzip
"""

import pandas as pd
import re
from pathlib import Path

RAW_PATH =  Path(__file__).parent/ "dataset-tickets-multi-lang3-4k.csv"  # adapte le nom exact après unzip
# Fais `ls data/raw/` après téléchargement — plusieurs CSV sont fournis (versions/langues différentes).
# Prends de préférence un fichier filtré sur "en" (anglais) si vous ne voulez pas gérer le multilingue.

df = pd.read_csv(RAW_PATH)
print("Colonnes disponibles :", df.columns.tolist())

# Filtre optionnel sur l'anglais si la colonne 'language' existe
if "language" in df.columns:
    df = df[df["language"] == "en"]

df = df.dropna(subset=["subject", "body", "priority", "queue"])

# --- 1. Jeu d'entraînement priorité ---------------------------------------
MAPPING_PRIORITE = {
    "1": "basse", "low": "basse",
    "2": "moyenne", "medium": "moyenne",
    "3": "critique", "critical": "critique", "high": "critique",
}

def normaliser_priorite(p):
    return MAPPING_PRIORITE.get(str(p).strip().lower(), None)

df["priorite_norm"] = df["priority"].apply(normaliser_priorite)
df_prio = df.dropna(subset=["priorite_norm"])

N_PAR_PRIORITE = 100
echantillons = []
for prio, groupe in df_prio.groupby("priorite_norm"):
    n = min(N_PAR_PRIORITE, len(groupe))
    echantillons.append(groupe.sample(n=n, random_state=42))
df_prio_final = pd.concat(echantillons)

output_prio = Path("app/training_priority.py")
lignes = [
    "# Généré depuis tobiasbueck/multilingual-customer-support-tickets (Kaggle)",
    "PRIORITY_TRAINING_DATA = [",
]
for _, row in df_prio_final.iterrows():
    texte = f"{row['subject']} {row['body']}".strip()
    texte = re.sub(r"\s+", " ", texte)[:500].replace('"', '\\"')
    lignes.append(f'    ("{texte}", "{row["priorite_norm"]}"),')
lignes.append("]")
output_prio.write_text("\n".join(lignes), encoding="utf-8")
print(f"✅ Écrit : {output_prio} ({len(df_prio_final)} exemples)")

# --- 2. Base de connaissances synthétique pour le RAG ----------------------
# On regroupe les réponses d'agent par queue, on garde les plus longues
# (donc probablement plus informatives) et on les assemble en documents.
KB_DIR = Path("data/knowledge_base")
KB_DIR.mkdir(parents=True, exist_ok=True)

answer_col = "answer" if "answer" in df.columns else None
if answer_col is None:
    print("⚠️ Pas de colonne 'answer' trouvée — vérifie les colonnes disponibles ci-dessus.")
else:
    for queue, groupe in df.groupby("queue"):
        groupe = groupe.dropna(subset=[answer_col])
        groupe["longueur"] = groupe[answer_col].str.len()
        top = groupe.sort_values("longueur", ascending=False).head(8)

        nom_fichier = re.sub(r"[^a-z0-9]+", "_", str(queue).lower()).strip("_") + ".md"
        chemin = KB_DIR / nom_fichier

        contenu = [f"# Base de connaissances — {queue}", ""]
        contenu.append(
            "> ⚠️ Document généré automatiquement à partir de réponses d'agents "
            "réelles (dataset public Kaggle), à relire et corriger avant usage en démo.\n"
        )
        for i, (_, row) in enumerate(top.iterrows(), 1):
            contenu.append(f"## {row.get('subject', f'Cas {i}')}")
            reponse = re.sub(r"\s+", " ", str(row[answer_col])).strip()
            contenu.append(reponse)
            contenu.append("")

        chemin.write_text("\n".join(contenu), encoding="utf-8")
        print(f"✅ Écrit : {chemin} ({len(top)} extraits)")

print("\nÉtape suivante : relire manuellement chaque .md dans data/knowledge_base/")
print("pour corriger le contenu généré, puis relancer `python -m app.rag`.")
