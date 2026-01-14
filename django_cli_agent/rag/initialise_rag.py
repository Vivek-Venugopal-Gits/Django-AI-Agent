"""
Standalone script to initialize the RAG system.

Run this file directly:
    python initialize_rag.py

Or from command line:
    python -m initialize_rag
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import rag modules
sys.path.insert(0, str(Path(__file__).parent))

from rag.setup import setup_rag, verify_setup


if __name__ == "__main__":
    print("\n" + "🤖 DJANGO AI AGENT - RAG INITIALIZATION".center(60))
    print("="*60 + "\n")
    
    # Run setup
    success = setup_rag()
    
    if success:
        # Verify it works
        print("\n" + "-"*60 + "\n")
        verify_setup()
        
        print("\n" + "="*60)
        print("🎉 All done! Your RAG system is ready to use.")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("❌ Setup failed. Please fix errors above and try again.")
        print("="*60 + "\n")
        sys.exit(1)