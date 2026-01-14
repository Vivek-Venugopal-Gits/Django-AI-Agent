"""
Verify that the vector database is working correctly.

Run this to check:
    python verify_vector_db.py
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import chromadb
from rag.embeddings import embed_texts


def verify_vector_db():
    """Check if vector database exists and is working"""
    
    print("\n" + "="*60)
    print("🔍 VECTOR DATABASE VERIFICATION")
    print("="*60 + "\n")
    
    # CORRECTED: Use project root, not rag module path
    vector_db_path = project_root / "data" / "vector_db"
    
    print(f"📁 Vector DB Path: {vector_db_path}")
    print(f"   Absolute path: {vector_db_path.resolve()}")
    print(f"   Directory exists: {vector_db_path.exists()}\n")
    
    if vector_db_path.exists():
        # List contents
        contents = list(vector_db_path.rglob("*"))
        print(f"📂 Directory contents ({len(contents)} items):")
        for item in contents[:15]:  # Show first 15
            size = item.stat().st_size if item.is_file() else 0
            item_type = "📄" if item.is_file() else "📁"
            rel_path = item.relative_to(vector_db_path)
            print(f"   {item_type} {rel_path} ({size:,} bytes)")
        if len(contents) > 15:
            print(f"   ... and {len(contents) - 15} more items")
        print()
    else:
        print("❌ Vector DB directory does not exist!")
        print("\nSearching for vector_db in other locations...")
        
        # Search for it
        for search_path in [project_root, project_root.parent]:
            found = list(search_path.rglob("vector_db"))
            if found:
                print(f"\n✅ Found vector_db at:")
                for f in found:
                    print(f"   {f}")
        print()
    
    # Try to connect to ChromaDB
    try:
        print("🔌 Connecting to ChromaDB...")
        client = chromadb.PersistentClient(path=str(vector_db_path))
        
        # List collections
        collections = client.list_collections()
        print(f"✅ Connected successfully!")
        print(f"   Collections found: {len(collections)}\n")
        
        if len(collections) == 0:
            print("⚠️  WARNING: No collections found in database!")
            print("   This means the database exists but is empty.")
            print("   You may need to run: python initialize_rag.py\n")
            return False
        
        for coll in collections:
            print(f"📚 Collection: {coll.name}")
            count = coll.count()
            print(f"   Document count: {count}")
            
            if count > 0:
                # Get sample metadata
                sample = coll.get(limit=1, include=["metadatas"])
                if sample["metadatas"]:
                    print(f"   Sample metadata: {sample['metadatas'][0]}")
            print()
        
        # Test retrieval
        if len(collections) > 0:
            print("🧪 Testing retrieval...")
            collection = client.get_collection("django_docs")
            
            test_query = "How to create Django models?"
            print(f"   Query: '{test_query}'")
            
            query_embedding = embed_texts([test_query])[0]
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            print(f"✅ Retrieved {len(results['documents'][0])} results")
            
            if results['documents'][0]:
                print(f"\n📄 First result preview:")
                print(f"   {results['documents'][0][0][:200]}...")
                print(f"   Source: {results['metadatas'][0][0]['source']}")
        
        print("\n" + "="*60)
        print("✅ VECTOR DATABASE IS WORKING CORRECTLY")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        print("="*60)
        print("❌ VECTOR DATABASE NOT WORKING")
        print("="*60)
        print("\nSuggested actions:")
        print("1. Re-run: python initialize_rag.py")
        print("2. Check that sentence-transformers is installed")
        print("3. Ensure data/django_docs/ has .txt files")
        print("="*60 + "\n")
        return False


if __name__ == "__main__":
    verify_vector_db()