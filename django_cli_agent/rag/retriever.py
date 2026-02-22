import chromadb
from rag.embeddings import embed_texts
from pathlib import Path
from rank_bm25 import BM25Okapi
import pickle
import numpy as np

CHROMA_PATH = Path(__file__).parent.parent / "data" / "vector_db"
BM25_INDEX_PATH = Path(__file__).parent.parent / "data" / "bm25_index.pkl"


class HybridRetriever:
    """
    Hybrid retrieval combining BM25 (keyword) + semantic (embedding) search.
    Optimized to reduce unnecessary document fetching and embedding overhead.
    """

    STOP_WORDS = {
        'what', 'is', 'the', 'a', 'an', 'how', 'does', 'do', 'can', 'i',
        'explain', 'tell', 'me', 'about', 'in', 'for', 'to', 'of', 'and'
    }

    DJANGO_TERMS = {
        'django', 'model', 'models', 'view', 'views', 'url', 'urls',
        'template', 'form', 'forms', 'admin', 'settings', 'migration',
        'queryset', 'orm', 'field', 'fields', 'foreignkey', 'manytomany',
        'charfield', 'integerfield', 'models.py', 'views.py', 'urls.py'
    }

    def __init__(self):
        self.chroma_client = None
        self.chroma_collection = None
        self.bm25 = None
        self.documents = []
        self.metadatas = []
        self._load_indexes()

    def _load_indexes(self):
        """Load both ChromaDB and BM25 indexes once at startup."""
        try:
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self.chroma_collection = self.chroma_client.get_collection("django_docs")
        except Exception as e:
            print(f"⚠️  Warning: Could not load ChromaDB: {e}")

        try:
            if BM25_INDEX_PATH.exists():
                with open(BM25_INDEX_PATH, 'rb') as f:
                    bm25_data = pickle.load(f)
                    self.bm25 = bm25_data['bm25']
                    self.documents = bm25_data['documents']
                    self.metadatas = bm25_data['metadatas']
            else:
                print(f"⚠️  Warning: BM25 index not found at {BM25_INDEX_PATH}")
        except Exception as e:
            print(f"⚠️  Warning: Could not load BM25 index: {e}")

    def _expand_query_for_semantic(self, query: str) -> str:
        lower_query = query.lower()
        expanded_terms = []

        if 'models.py' in lower_query or 'model file' in lower_query:
            expanded_terms.extend(['django models', 'database schema', 'ORM', 'model fields'])
        if 'views.py' in lower_query or 'view file' in lower_query:
            expanded_terms.extend(['django views', 'request handling', 'response'])
        if 'urls.py' in lower_query or 'url file' in lower_query:
            expanded_terms.extend(['django urls', 'url routing', 'path'])
        if 'forms.py' in lower_query or 'form file' in lower_query:
            expanded_terms.extend(['django forms', 'form validation', 'ModelForm'])
        if 'django' not in lower_query and not expanded_terms:
            expanded_terms.append('django')

        return f"{query} {' '.join(expanded_terms)}" if expanded_terms else query

    def _extract_keywords(self, query: str) -> str:
        tokens = query.lower().split()
        keywords = [
            token for token in tokens
            if token in self.DJANGO_TERMS or token not in self.STOP_WORDS
        ]
        return ' '.join(keywords) if keywords else query

    def retrieve(self, query: str, k: int = 3, alpha: float = 0.6):
        """
        Hybrid retrieval.

        Args:
            query: User's query string
            k: Final number of results to return (default lowered to 3)
            alpha: Semantic weight — 0.6 = slightly more semantic than BM25

        Returns:
            tuple: (combined_context_string, list_of_sources)
        """
        if not self.chroma_collection or not self.bm25:
            print("⚠️  Hybrid search not available, check setup")
            return "", []

        semantic_query = self._expand_query_for_semantic(query)
        keyword_query = self._extract_keywords(query)

        print(f"[DEBUG] Original query: {query}")
        print(f"[DEBUG] Semantic query: {semantic_query}")
        print(f"[DEBUG] Keyword query: {keyword_query}")

        # FIX: retrieve_k was k*3 (12 docs for k=4). Now k*2 capped at 10.
        # Fewer candidates = faster BM25 scoring + less fusion overhead.
        retrieve_k = min(k * 2, 10)

        semantic_results = self._semantic_search(semantic_query, retrieve_k)
        bm25_results = self._bm25_search(keyword_query, retrieve_k)

        fused_results = self._reciprocal_rank_fusion(
            semantic_results, bm25_results, alpha=alpha, k=k
        )

        contexts = [doc for doc, _ in fused_results]
        sources = list(set(meta['source'] for _, meta in fused_results))

        return "\n\n".join(contexts), sources

    def _semantic_search(self, query: str, k: int):
        try:
            query_embedding = embed_texts([query])[0]
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            semantic_results = []
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                similarity = 1 / (1 + distance)
                semantic_results.append((doc, meta, similarity, i))
            return semantic_results
        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            return []

    def _bm25_search(self, query: str, k: int):
        try:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_indices = np.argsort(scores)[::-1][:k]
            return [
                (self.documents[idx], self.metadatas[idx], scores[idx], rank)
                for rank, idx in enumerate(top_indices)
                if scores[idx] > 0
            ]
        except Exception as e:
            print(f"⚠️  BM25 search failed: {e}")
            return []

    def _reciprocal_rank_fusion(self, semantic_results, bm25_results, alpha=0.6, k=3):
        rrf_constant = 60
        doc_scores = {}

        for doc, meta, similarity, rank in semantic_results:
            doc_id = doc[:100]
            rrf_score = alpha * (1 / (rank + rrf_constant))
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': doc, 'meta': meta, 'score': 0}
            doc_scores[doc_id]['score'] += rrf_score

        for doc, meta, score, rank in bm25_results:
            doc_id = doc[:100]
            rrf_score = (1 - alpha) * (1 / (rank + rrf_constant))
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': doc, 'meta': meta, 'score': 0}
            doc_scores[doc_id]['score'] += rrf_score

        ranked_docs = sorted(
            doc_scores.values(), key=lambda x: x['score'], reverse=True
        )[:k]

        return [(d['doc'], d['meta']) for d in ranked_docs]


# Singleton — loaded once per worker process, reused across all requests
_hybrid_retriever = None


def get_hybrid_retriever():
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


def retrieve_context(query: str, k: int = 3, alpha: float = 0.6):
    """
    Main retrieval function.

    Args:
        query: User's query string
        k: Number of results (lowered from 4 to 3 for speed)
        alpha: Semantic vs BM25 weight (0.6 = slightly more semantic)

    Returns:
        tuple: (combined_context_string, list_of_sources)
    """
    retriever = get_hybrid_retriever()
    return retriever.retrieve(query, k=k, alpha=alpha)