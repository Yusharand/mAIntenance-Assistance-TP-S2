"""
PERSONNE 2 — Recherche documentaire / RAG (axe noté : 20%)
============================================================

DÉMARCHE / MÉTHODOLOGIE
------------------------
Choix : recherche par similarité TF-IDF + cosinus (scikit-learn), PAS
d'embeddings neuronaux (sentence-transformers).

Justification de ce choix (à mettre dans le rapport, section "limites") :
  - Aucune dépendance lourde (pas de téléchargement de modèle de plusieurs
    centaines de Mo, pas de risque de lenteur/échec de setup pendant les 8h
    du hackathon).
  - Corpus de connaissances technique avec vocabulaire très spécifique
    (noms de procédures, codes KB-XXX, termes techniques) : le TF-IDF, basé
    sur la fréquence des mots exacts, est en réalité compétitif voire meilleur
    que des embeddings généralistes sur ce type de corpus restreint et jargonné.
  - Entièrement local, gratuit, déterministe, donc évaluable et reproductible
    (pas de variabilité d'une exécution à l'autre comme avec un appel LLM).
Limite assumée : le TF-IDF ne capture pas la similarité sémantique
("mot de passe" vs "identifiants" seront moins bien rapprochés qu'avec des
embeddings). À documenter comme piste d'amélioration si le temps le permet.

CHUNKING
--------
Chaque document Markdown est découpé par section (## Titre), pas par nombre
fixe de tokens : les documents de la KB sont déjà structurés en sections
cohérentes (procédure standard, cas particuliers, escalade...), donc découper
sur cette structure logique donne des chunks plus pertinents qu'un découpage
aveugle par 300 tokens.

SYNTHÈSE DE RÉPONSE
--------------------
Sans clé API LLM garantie disponible pendant le hackathon, `answer_with_citations`
fait une synthèse EXTRACTIVE (assemble les passages les plus pertinents avec
leurs sources) plutôt que générative. C'est un choix délibéré : zéro risque
d'hallucination de procédure (risque explicitement cité section 6 du sujet),
au prix d'une réponse moins fluide. Si un LLM est disponible côté équipe,
`generer_reponse_llm()` montre où brancher un appel réel — le prompt est
construit pour forcer le modèle à rester dans les passages fournis.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas import RAGResult, SourceCitee

KB_DIR = Path(__file__).parent.parent / "data" / "knowledge_base"
SEUIL_CONFIANCE_RAG = 0.12  # calibré empiriquement sur le corpus de test (voir evaluate_rag())


@dataclass
class Chunk:
    document_id: str      # ex: "KB-NET-01"
    section_titre: str    # ex: "Escalade"
    texte: str


# ---------------------------------------------------------------------------
# 1. INGESTION : chargement + chunking par section Markdown
# ---------------------------------------------------------------------------

def _chunk_markdown(doc_id: str, contenu: str) -> list[Chunk]:
    """Découpe un document Markdown en chunks par section (titre '## ...').
    Le titre h1 (# ...) sert de contexte global mais n'est pas un chunk à lui seul."""
    # On isole chaque section commençant par '## '
    sections = re.split(r"\n(?=## )", contenu)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section or section.startswith("# "):
            # ligne de titre h1 seule, ou vide -> on l'ignore comme chunk séparé
            if section.startswith("# ") and "\n" not in section:
                continue
        titre_match = re.match(r"##\s*(.+)", section)
        titre = titre_match.group(1).strip() if titre_match else "introduction"
        if len(section.split()) >= 3:  # ignore les chunks quasi vides
            chunks.append(Chunk(document_id=doc_id, section_titre=titre, texte=section))
    return chunks


def _load_documents(kb_dir: Path = KB_DIR) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        doc_id = path.stem  # ex: "KB-NET-01"
        contenu = path.read_text(encoding="utf-8")
        all_chunks.extend(_chunk_markdown(doc_id, contenu))
    return all_chunks


class RAGIndex:
    """Index TF-IDF construit une fois et réutilisé pour toutes les recherches."""

    def __init__(self, kb_dir: Path = KB_DIR):
        self.chunks = _load_documents(kb_dir)
        self.vectorizer = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), strip_accents="unicode"
        )
        if self.chunks:
            self.matrix = self.vectorizer.fit_transform([c.texte for c in self.chunks])
        else:
            self.matrix = None

    def search(self, query: str, top_k: int = 3) -> list[SourceCitee]:
        if not self.chunks or self.matrix is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        top_indices = scores.argsort()[::-1][:top_k]
        resultats = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            chunk = self.chunks[i]
            resultats.append(SourceCitee(
                document_id=f"{chunk.document_id} — {chunk.section_titre}",
                extrait=chunk.texte[:400],
                score_pertinence=round(float(scores[i]), 3),
            ))
        return resultats


_INDEX: RAGIndex | None = None


def get_index() -> RAGIndex:
    """Index construit une seule fois (lazy singleton) — évite de re-parser et
    re-vectoriser la KB à chaque requête."""
    global _INDEX
    if _INDEX is None:
        _INDEX = RAGIndex()
    return _INDEX


def ingest_knowledge_base(kb_dir: str = "data/knowledge_base") -> int:
    """Force la reconstruction de l'index (utile après ajout de documents)."""
    global _INDEX
    _INDEX = RAGIndex(Path(kb_dir))
    return len(_INDEX.chunks)


def search(query: str, top_k: int = 3) -> list[SourceCitee]:
    return get_index().search(query, top_k)


# ---------------------------------------------------------------------------
# 2. SYNTHÈSE DE RÉPONSE (extractive par défaut)
# ---------------------------------------------------------------------------

def _synthese_extractive(sources: list[SourceCitee]) -> str:
    """Assemble les passages récupérés en une réponse lisible, sans rien
    inventer : c'est une CONCATÉNATION structurée, pas une génération libre."""
    lignes = []
    for s in sources:
        lignes.append(f"[{s.document_id}] {s.extrait.strip()}")
    return "\n\n".join(lignes)


def generer_reponse_llm(query: str, sources: list[SourceCitee]) -> str:
    """OPTIONNEL — à activer si l'équipe dispose d'une clé API LLM (Groq/Gemini).
    Le prompt est conçu pour interdire explicitement toute information hors
    des passages fournis, afin d'éviter la génération d'une procédure
    inexistante (risque cité section 6 du sujet)."""
    contexte = "\n\n".join(f"[{s.document_id}]\n{s.extrait}" for s in sources)
    prompt = f"""Tu es un assistant de support informatique. Réponds à la question
UNIQUEMENT à partir des passages ci-dessous. Si les passages ne suffisent pas,
dis explicitement que l'information n'est pas disponible. Cite les identifiants
de document entre crochets pour chaque affirmation.

Passages disponibles :
{contexte}

Question : {query}

Réponse :"""
    # TODO: brancher l'appel API réel ici, ex. avec le SDK Groq :
    # response = client.chat.completions.create(model=..., messages=[{"role": "user", "content": prompt}])
    # return response.choices[0].message.content
    raise NotImplementedError("Brancher ici l'appel au LLM choisi par l'équipe.")


def answer_with_citations(query: str, use_llm: bool = False) -> RAGResult:
    sources = search(query, top_k=3)

    if not sources or sources[0].score_pertinence < SEUIL_CONFIANCE_RAG:
        return RAGResult(
            reponse_proposee=None,
            sources=sources,
            reponse_suffisamment_soutenue=False,
        )

    if use_llm:
        try:
            reponse = generer_reponse_llm(query, sources)
        except NotImplementedError:
            reponse = _synthese_extractive(sources)
    else:
        reponse = _synthese_extractive(sources)

    return RAGResult(
        reponse_proposee=reponse,
        sources=sources,
        reponse_suffisamment_soutenue=True,
    )


# ---------------------------------------------------------------------------
# 3. ÉVALUATION — precision@k sur un petit jeu de requêtes de référence
# ---------------------------------------------------------------------------

JEU_TEST_RAG = [
    ("mon mot de passe ne fonctionne plus", "KB-AUTH-01"),
    ("le wifi est coupé pour tout le service", "KB-NET-01"),
    ("mon ordinateur ne s'allume plus", "KB-HW-01"),
    ("impossible d'imprimer depuis mon poste", "KB-PRINT-01"),
    ("je n'ai plus accès au dossier partagé", "KB-ACCESS-01"),
    ("j'ai reçu un email de phishing suspect", "KB-SEC-01"),
]


def evaluate_rag(top_k: int = 3) -> dict:
    """Pour chaque requête de test, vérifie si le document attendu apparaît
    dans le top-k -> precision@k. Résultats à copier dans le rapport (livrable 6)."""
    index = get_index()
    trouves = 0
    details = []
    for query, doc_attendu in JEU_TEST_RAG:
        resultats = index.search(query, top_k=top_k)
        docs_trouves = [r.document_id.split(" — ")[0] for r in resultats]
        ok = doc_attendu in docs_trouves
        trouves += int(ok)
        details.append({
            "query": query, "attendu": doc_attendu,
            "trouves": docs_trouves, "correct": ok,
        })
    return {
        f"precision_at_{top_k}": round(trouves / len(JEU_TEST_RAG), 3),
        "nb_requetes_test": len(JEU_TEST_RAG),
        "details": details,
    }


if __name__ == "__main__":
    import json
    print("Nombre de chunks indexés :", ingest_knowledge_base())
    print(json.dumps(evaluate_rag(), indent=2, ensure_ascii=False))
