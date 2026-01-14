from pathlib import Path

# Use relative path from the rag module
DOCS_PATH = Path(__file__).parent.parent / "data" / "django_docs"


def load_documents():
    """
    Load all .txt files from the Django documentation directory.
    
    Returns:
        List of document dictionaries with 'text' and 'metadata'
    """
    documents = []
    
    # Verify path exists
    if not DOCS_PATH.exists():
        raise FileNotFoundError(f"Documentation path not found: {DOCS_PATH}")
    
    # Find all .txt files
    txt_files = list(DOCS_PATH.glob("*.txt"))
    
    if len(txt_files) == 0:
        raise FileNotFoundError(f"No .txt files found in: {DOCS_PATH}")
    
    print(f"   Found {len(txt_files)} .txt files")
    
    # Load each file
    for i, file_path in enumerate(txt_files, 1):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            if len(text.strip()) > 0:
                documents.append({
                    "text": text,
                    "metadata": {
                        "source": file_path.name
                    }
                })
            
            # Progress indicator
            if i % 20 == 0:
                print(f"   Loading... {i}/{len(txt_files)} files")
                
        except Exception as e:
            print(f"   ⚠️  Warning: Could not load {file_path.name}: {e}")
            continue
    
    return documents