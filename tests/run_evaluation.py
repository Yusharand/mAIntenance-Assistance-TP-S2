"""
Génère data/resultats_evaluation.json — livrable obligatoire n°6 du sujet
("les résultats de l'évaluation"). Lancer avec : python -m tests.run_evaluation
"""
import sys, json
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.classifier import evaluate_classifier
from app.rag import evaluate_rag, ingest_knowledge_base

OUTPUT = Path(__file__).parent.parent / "data" / "resultats_evaluation.json"


def main():
    ingest_knowledge_base()
    resultats = {
        "classification_p1": evaluate_classifier(),
        "rag_p2": evaluate_rag(),
    }
    OUTPUT.write_text(json.dumps(resultats, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Résultats écrits dans {OUTPUT}")
    print(json.dumps(resultats, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
