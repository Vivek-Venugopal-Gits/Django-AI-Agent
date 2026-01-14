from rag.loader import load_documents
from rag.splitter import split_documents
from rag.vector_store import build_vector_store
from pathlib import Path


def setup_rag():
    """
    Initialize the RAG system by:
    1. Loading Django documentation files
    2. Splitting into chunks
    3. Building vector store with embeddings
    """
    print("\n" + "="*60)
    print("🚀 INITIALIZING RAG SYSTEM")
    print("="*60 + "\n")

    # Step 1: Load documents
    print("📂 Step 1: Loading Django documentation files...")
    try:
        documents = load_documents()
        print(f"   ✅ Loaded {len(documents)} documents")
        
        if len(documents) == 0:
            print("   ❌ ERROR: No documents found!")
            print("   Check that .txt files exist in data/django_docs/")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR loading documents: {e}")
        return False

    # Step 2: Split documents
    print("\n✂️  Step 2: Splitting documents into chunks...")
    try:
        chunks = split_documents(documents)
        print(f"   ✅ Created {len(chunks)} chunks")
        
        if len(chunks) == 0:
            print("   ❌ ERROR: No chunks created!")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR splitting documents: {e}")
        return False

    # Step 3: Build vector store
    print("\n🔮 Step 3: Building vector store (this may take a few minutes)...")
    try:
        doc_count = build_vector_store(chunks)
        print(f"   ✅ Vector store created successfully!")
        
    except Exception as e:
        print(f"   ❌ ERROR building vector store: {e}")
        return False

    # Verification
    print("\n" + "="*60)
    print("✅ RAG SETUP COMPLETE")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   • Documents loaded: {len(documents)}")
    print(f"   • Chunks created: {len(chunks)}")
    print(f"   • Documents in DB: {doc_count}")
    print(f"   • Vector DB location: data/vector_db/")
    print("\n💡 You can now use the agent to query Django documentation!")
    print("   Run: python verify_vector_db.py to verify\n")
    
    return True


def verify_setup():
    """
    Verify that RAG system is working correctly
    """
    print("\n🔍 VERIFYING RAG SETUP...\n")
    
    try:
        from rag.retriever import retrieve_context
        
        # Test query
        test_query = "How to create Django models?"
        print(f"Test query: '{test_query}'")
        
        context, sources = retrieve_context(test_query, k=3)
        
        print(f"\n✅ Retrieval successful!")
        print(f"   • Context length: {len(context)} characters")
        print(f"   • Sources found: {len(sources)}")
        print(f"   • Source files: {sources}")
        
        if len(context) > 0:
            print(f"\n📄 Sample context (first 200 chars):")
            print(f"   {context[:200]}...")
            return True
        else:
            print("\n❌ WARNING: No context retrieved!")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}")
        return False


if __name__ == "__main__":
    # Run setup
    success = setup_rag()
    
    if success:
        # Verify it works
        print("\n" + "-"*60 + "\n")
        verify_setup()
    else:
        print("\n❌ Setup failed. Please check errors above.")