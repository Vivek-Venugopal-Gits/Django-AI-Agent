"""
Build BM25 index for hybrid search

Run this after initializing ChromaDB:
    python build_bm25_index.py

This script:
1. Reads all documents from your existing ChromaDB
2. Builds a BM25 keyword index
3. Saves it to data/bm25_index.pkl
"""

import sys
from pathlib import Path
import pickle
import chromadb
from rank_bm25 import BM25Okapi

# Project paths
project_root = Path(__file__).parent
CHROMA_PATH = project_root / "data" / "vector_db"
BM25_INDEX_PATH = project_root / "data" / "bm25_index.pkl"


def build_bm25_index():
    """
    Build BM25 index from existing ChromaDB documents
    """
    print("\n" + "="*60)
    print("🔨 BUILDING BM25 INDEX FOR HYBRID SEARCH")
    print("="*60 + "\n")
    
    # STEP 1: Load documents from ChromaDB
    print("📂 Step 1: Loading documents from ChromaDB...")
    print(f"   ChromaDB path: {CHROMA_PATH}")
    
    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection("django_docs")
        
        # Get all documents
        all_docs = collection.get(include=["documents", "metadatas"])
        
        documents = all_docs["documents"]
        metadatas = all_docs["metadatas"]
        
        print(f"   ✅ Loaded {len(documents)} documents from ChromaDB")
        
        if len(documents) == 0:
            print("   ❌ ERROR: No documents found in ChromaDB!")
            print("   Please run: python rag/initialise_rag.py first")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR loading ChromaDB: {e}")
        print("   Make sure you've run: python rag/initialise_rag.py first")
        return False
    
    # STEP 2: Tokenize documents for BM25
    print("\n✂️  Step 2: Tokenizing documents for BM25...")
    
    try:
        # Simple tokenization: lowercase + split by whitespace
        # Example: "Django Model Fields" → ["django", "model", "fields"]
        tokenized_docs = [doc.lower().split() for doc in documents]
        
        print(f"   ✅ Tokenized {len(tokenized_docs)} documents")
        
        # Show sample
        if len(tokenized_docs) > 0:
            sample_tokens = tokenized_docs[0][:10]
            print(f"   📝 Sample tokens: {sample_tokens}...")
        
    except Exception as e:
        print(f"   ❌ ERROR tokenizing: {e}")
        return False
    
    # STEP 3: Build BM25 index
    print("\n🔮 Step 3: Building BM25 index...")
    print("   (This calculates keyword scores for all documents)")
    
    try:
        bm25 = BM25Okapi(tokenized_docs)
        print(f"   ✅ BM25 index built successfully")
        
    except Exception as e:
        print(f"   ❌ ERROR building BM25: {e}")
        return False
    
    # STEP 4: Save BM25 index to disk
    print("\n💾 Step 4: Saving BM25 index to disk...")
    
    try:
        # Ensure directory exists
        BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Package everything together
        bm25_data = {
            'bm25': bm25,           # The BM25 index object
            'documents': documents,  # Original document texts
            'metadatas': metadatas   # Document metadata (source files)
        }
        
        # Save as pickle file
        with open(BM25_INDEX_PATH, 'wb') as f:
            pickle.dump(bm25_data, f)
        
        # Check file size
        file_size = BM25_INDEX_PATH.stat().st_size
        print(f"   ✅ BM25 index saved to: {BM25_INDEX_PATH}")
        print(f"   📊 Index size: {file_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"   ❌ ERROR saving index: {e}")
        return False
    
    # STEP 5: Verify the index works
    print("\n🔍 Step 5: Verifying BM25 index...")
    
    try:
        # Test query
        test_query = "Django models CharField ForeignKey"
        print(f"   Test query: '{test_query}'")
        
        # Tokenize and search
        tokenized_query = test_query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Get best match
        top_idx = scores.argmax()
        top_score = scores[top_idx]
        
        print(f"   ✅ Top result score: {top_score:.4f}")
        print(f"   📄 Top result preview: {documents[top_idx][:150]}...")
        print(f"   📚 Source: {metadatas[top_idx]['source']}")
        print(f"   ✅ BM25 index is working correctly!")
        
    except Exception as e:
        print(f"   ⚠️  Warning: Verification failed: {e}")
        print(f"   The index was saved but testing failed")
    
    # Summary
    print("\n" + "="*60)
    print("✅ BM25 INDEX BUILD COMPLETE")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   • Documents indexed: {len(documents)}")
    print(f"   • Index file: {BM25_INDEX_PATH}")
    print(f"   • Index size: {file_size / 1024:.2f} KB")
    print(f"\n💡 Your hybrid search system is ready!")
    print(f"   The agent will now use both:")
    print(f"   • Semantic search (ChromaDB) - for concepts")
    print(f"   • Keyword search (BM25) - for exact terms")
    print("\n🚀 You can now run: python main.py")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    success = build_bm25_index()
    
    if not success:
        print("\n❌ Build failed. Please fix errors above and try again.\n")
        sys.exit(1)