
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
    """Synthèse générative via Groq, activée uniquement si `use_llm=True` ET
    qu'une clé GROQ_API_KEY est configurée. Le prompt interdit explicitement
    toute information hors des passages fournis, afin d'éviter la génération
    d'une procédure inexistante (risque cité section 6 du sujet). En cas
    d'échec (clé absente, réseau, timeout...), l'appelant (answer_with_citations)
    retombe automatiquement sur la synthèse extractive — le LLM n'est jamais
    un point de défaillance unique."""
    from app.llm_client import call_llm

    contexte = "\n\n".join(f"[{s.document_id}]\n{s.extrait}" for s in sources)
    system = (
        "You are an IT support assistant. Answer the question ONLY using the "
        "passages provided below. If the passages are not sufficient, say "
        "explicitly that the information is not available. Cite document "
        "identifiers in brackets for every claim. Never propose a procedure "
        "that is not present in the passages."
    )
    prompt = f"""Available passages:
{contexte}

Question: {query}

Answer:"""
    reponse = call_llm(prompt, system=system, temperature=0.2, max_tokens=400)
    if reponse is None:
        raise NotImplementedError("Appel LLM indisponible (clé absente ou erreur réseau).")
    return reponse.strip()


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
    ("my password doesn't work anymore", "KB-AUTH-01"),
    ("the wifi is down for the whole department", "KB-NET-01"),
    ("my computer won't turn on anymore", "KB-HW-01"),
    ("I can't print from my workstation", "KB-PRINT-01"),
    ("I no longer have access to the shared folder", "KB-ACCESS-01"),
    ("I received a suspicious phishing email", "KB-SEC-01"),
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
