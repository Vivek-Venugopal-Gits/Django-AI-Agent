import chromadb
from chromadb.config import Settings
from rag.embeddings import embed_texts
from pathlib import Path

# Use relative path from the rag module
CHROMA_PATH = Path(__file__).parent.parent / "data" / "vector_db"


def build_vector_store(chunks):
    """
    Build ChromaDB vector store from document chunks.
    
    Args:
        chunks: List of chunk dictionaries with 'text' and 'metadata'
    """
    # Ensure directory exists
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    
    print(f"   Vector DB path: {CHROMA_PATH}")
    
    # Create persistent client with explicit settings
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    # Delete existing collection if it exists
    try:
        client.delete_collection(name="django_docs")
        print(f"   Deleted existing collection")
    except:
        pass

    # Create new collection with explicit distance function
    collection = client.get_or_create_collection(
        name="django_docs",
        metadata={"hnsw:space": "cosine"}
    )

    # Extract data
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    print(f"   Generating embeddings for {len(texts)} chunks...")
    
    # Generate embeddings (this takes time)
    embeddings = embed_texts(texts)
    
    print(f"   Storing in vector database...")

    # Add to collection in batches to avoid memory issues
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        end_idx = min(i + batch_size, len(texts))
        
        collection.add(
            documents=texts[i:end_idx],
            metadatas=metadatas[i:end_idx],
            embeddings=embeddings[i:end_idx],
            ids=[str(j) for j in range(i, end_idx)]
        )
        
        print(f"   Stored {end_idx}/{len(texts)} chunks")
    
    # Verify collection was created
    final_count = collection.count()
    print(f"   Persisting to disk...")
    print(f"   ✅ Final collection count: {final_count} documents")
    
    return final_count