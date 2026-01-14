# import chromadb
# from rag.embeddings import embed_texts
# from pathlib import Path

# # Use relative path from the rag module
# CHROMA_PATH = Path(__file__).parent.parent / "data" / "vector_db"


# def retrieve_context(query, k=4):
#     """
#     Retrieve relevant context from the vector database.
    
#     Args:
#         query: User's query string
#         k: Number of results to retrieve
    
#     Returns:
#         tuple: (combined_context_string, list_of_sources)
#     """
#     # Create persistent client
#     client = chromadb.PersistentClient(
#         path=str(CHROMA_PATH)
#     )

#     try:
#         collection = client.get_collection("django_docs")
#     except Exception as e:
#         print(f"⚠️  Warning: Vector database not found. Run RAG setup first.")
#         print(f"   Error: {e}")
#         return "", []

#     query_embedding = embed_texts([query])[0]

#     results = collection.query(
#         query_embeddings=[query_embedding],
#         n_results=k
#     )

#     contexts = []
#     sources = set()

#     for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
#         contexts.append(doc)
#         sources.add(meta["source"])

#     return "\n\n".join(contexts), list(sources)

import chromadb
from rag.embeddings import embed_texts
from pathlib import Path
from rank_bm25 import BM25Okapi
import pickle
import numpy as np
import re

# Use relative path from the rag module
CHROMA_PATH = Path(__file__).parent.parent / "data" / "vector_db"
BM25_INDEX_PATH = Path(__file__).parent.parent / "data" / "bm25_index.pkl"


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. BM25 (keyword-based search) - great for exact terms
    2. Semantic Search (embedding-based) - great for concepts
    """
    
    # Common stop words that don't help with Django queries
    STOP_WORDS = {
        'what', 'is', 'the', 'a', 'an', 'how', 'does', 'do', 'can', 'i',
        'explain', 'tell', 'me', 'about', 'in', 'for', 'to', 'of', 'and'
    }
    
    # Django-specific important terms (never remove these)
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
        """Load both ChromaDB and BM25 indexes"""
        # Load ChromaDB (semantic search)
        try:
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self.chroma_collection = self.chroma_client.get_collection("django_docs")
        except Exception as e:
            print(f"⚠️  Warning: Could not load ChromaDB: {e}")
        
        # Load BM25 index (keyword search)
        try:
            if BM25_INDEX_PATH.exists():
                with open(BM25_INDEX_PATH, 'rb') as f:
                    bm25_data = pickle.load(f)
                    self.bm25 = bm25_data['bm25']
                    self.documents = bm25_data['documents']
                    self.metadatas = bm25_data['metadatas']
            else:
                print(f"⚠️  Warning: BM25 index not found at {BM25_INDEX_PATH}")
                print("   Run the setup script to build BM25 index")
        except Exception as e:
            print(f"⚠️  Warning: Could not load BM25 index: {e}")
    
    def _preprocess_query(self, query: str) -> dict:
        """
        Preprocess query to improve both semantic and keyword search
        
        Returns:
            dict with 'original', 'semantic_query', and 'keyword_query'
        """
        # Original query for semantic search (keep natural language)
        original = query
        
        # Enhanced semantic query (expand conceptual terms)
        semantic_query = self._expand_query_for_semantic(query)
        
        # Enhanced keyword query (focus on important terms)
        keyword_query = self._extract_keywords(query)
        
        return {
            'original': original,
            'semantic': semantic_query,
            'keyword': keyword_query
        }
    
    def _expand_query_for_semantic(self, query: str) -> str:
        """
        Expand query for better semantic search
        """
        lower_query = query.lower()
        expanded_terms = []
        
        # Detect concept and add related terms
        if 'models.py' in lower_query or 'model file' in lower_query:
            expanded_terms.extend(['django models', 'database schema', 'ORM', 'model fields'])
        
        if 'views.py' in lower_query or 'view file' in lower_query:
            expanded_terms.extend(['django views', 'request handling', 'response'])
        
        if 'urls.py' in lower_query or 'url file' in lower_query:
            expanded_terms.extend(['django urls', 'url routing', 'path'])
        
        if 'forms.py' in lower_query or 'form file' in lower_query:
            expanded_terms.extend(['django forms', 'form validation', 'ModelForm'])
        
        # Add generic Django context if not already specific
        if 'django' not in lower_query and not expanded_terms:
            expanded_terms.append('django')
        
        # Combine original with expansions
        if expanded_terms:
            return f"{query} {' '.join(expanded_terms)}"
        return query
    
    def _extract_keywords(self, query: str) -> str:
        """
        Extract important keywords for BM25 search
        Removes stop words but keeps Django-specific terms
        """
        # Tokenize
        tokens = query.lower().split()
        
        # Filter tokens
        keywords = []
        for token in tokens:
            # Keep if it's a Django term or not a stop word
            if token in self.DJANGO_TERMS or token not in self.STOP_WORDS:
                keywords.append(token)
        
        # Join back
        return ' '.join(keywords) if keywords else query
    
    def retrieve(self, query: str, k: int = 4, alpha: float = 0.5):
        """
        Hybrid retrieval using both BM25 and semantic search
        
        Args:
            query: User's query string
            k: Number of results to retrieve
            alpha: Weight for semantic vs BM25 (0.5 = equal weight)
                   0.0 = pure BM25, 1.0 = pure semantic
        
        Returns:
            tuple: (combined_context_string, list_of_sources)
        """
        if not self.chroma_collection or not self.bm25:
            print("⚠️  Hybrid search not available, check setup")
            return "", []
        
        # Preprocess query
        processed = self._preprocess_query(query)
        
        # DEBUG: Show query processing
        print(f"[DEBUG] Original query: {processed['original']}")
        print(f"[DEBUG] Semantic query: {processed['semantic']}")
        print(f"[DEBUG] Keyword query: {processed['keyword']}")
        
        # Get more results than needed for better fusion
        retrieve_k = min(k * 3, 20)
        
        # 1. SEMANTIC SEARCH (use expanded query)
        semantic_results = self._semantic_search(processed['semantic'], retrieve_k)
        
        # 2. BM25 KEYWORD SEARCH (use keyword query)
        bm25_results = self._bm25_search(processed['keyword'], retrieve_k)
        
        # 3. RECIPROCAL RANK FUSION
        fused_results = self._reciprocal_rank_fusion(
            semantic_results, 
            bm25_results, 
            alpha=alpha,
            k=k
        )
        
        # 4. Format output
        contexts = [doc for doc, _ in fused_results]
        sources = list(set([meta['source'] for _, meta in fused_results]))
        
        return "\n\n".join(contexts), sources
    
    def _semantic_search(self, query: str, k: int):
        """Perform semantic search using ChromaDB"""
        try:
            query_embedding = embed_texts([query])[0]
            
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            
            # Return list of (document, metadata, score, rank) tuples
            # ChromaDB returns distances, convert to similarity scores
            semantic_results = []
            for i, (doc, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                # Convert distance to similarity (lower distance = higher similarity)
                similarity = 1 / (1 + distance)
                semantic_results.append((doc, meta, similarity, i))
            
            return semantic_results
            
        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            return []
    
    def _bm25_search(self, query: str, k: int):
        """Perform BM25 keyword search"""
        try:
            # Tokenize query (simple whitespace split)
            tokenized_query = query.lower().split()
            
            # Get BM25 scores for all documents
            scores = self.bm25.get_scores(tokenized_query)
            
            # Get top-k indices
            top_indices = np.argsort(scores)[::-1][:k]
            
            # Return list of (document, metadata, score, rank) tuples
            bm25_results = []
            for rank, idx in enumerate(top_indices):
                if scores[idx] > 0:  # Only include non-zero scores
                    bm25_results.append((
                        self.documents[idx],
                        self.metadatas[idx],
                        scores[idx],
                        rank
                    ))
            
            return bm25_results
            
        except Exception as e:
            print(f"⚠️  BM25 search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, semantic_results, bm25_results, alpha=0.5, k=4):
        """
        Combine results using Reciprocal Rank Fusion (RRF)
        
        RRF formula: score = sum(1 / (rank + k)) for each result list
        k=60 is a common constant in RRF
        """
        rrf_constant = 60
        doc_scores = {}
        
        # Score semantic results
        for doc, meta, similarity, rank in semantic_results:
            doc_id = doc[:100]  # Use first 100 chars as ID
            rrf_score = alpha * (1 / (rank + rrf_constant))
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'meta': meta,
                    'score': 0
                }
            doc_scores[doc_id]['score'] += rrf_score
        
        # Score BM25 results
        for doc, meta, score, rank in bm25_results:
            doc_id = doc[:100]
            rrf_score = (1 - alpha) * (1 / (rank + rrf_constant))
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'meta': meta,
                    'score': 0
                }
            doc_scores[doc_id]['score'] += rrf_score
        
        # Sort by combined score and return top-k
        ranked_docs = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:k]
        
        return [(d['doc'], d['meta']) for d in ranked_docs]


# Singleton instance
_hybrid_retriever = None

def get_hybrid_retriever():
    """Get or create hybrid retriever instance"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


def retrieve_context(query: str, k: int = 4, alpha: float = 0.5):
    """
    Main retrieval function using hybrid search
    
    Args:
        query: User's query string
        k: Number of results to retrieve
        alpha: Semantic vs BM25 weight (0.5 = balanced, 0.7 = more semantic)
    
    Returns:
        tuple: (combined_context_string, list_of_sources)
    """
    retriever = get_hybrid_retriever()
    return retriever.retrieve(query, k=k, alpha=alpha)