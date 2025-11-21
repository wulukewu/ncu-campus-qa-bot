#!/bin/bash

# =============================================================================
# NCU Campus QA Bot - RAG Database Builder
# =============================================================================
# This script builds the vector database for the RAG server
# Run this before starting the server for the first time

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAG_SERVER_DIR="$SCRIPT_DIR/rag_server"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       NCU Campus QA Bot - RAG Database Builder                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# --- Check if we're in the correct directory ---
if [ ! -f "$RAG_SERVER_DIR/DBHandler.py" ]; then
    echo "❌ Error: DBHandler.py not found in rag_server/"
    echo "   Please run this script from the 'server' directory:"
    echo "   cd server && ./build_database.sh"
    exit 1
fi

# --- Check if .env file exists ---
if [ ! -f "$RAG_SERVER_DIR/.env" ]; then
    echo "⚠️  Warning: .env file not found in rag_server/"
    echo "   Creating from .env.example..."
    if [ -f "$RAG_SERVER_DIR/.env.example" ]; then
        cp "$RAG_SERVER_DIR/.env.example" "$RAG_SERVER_DIR/.env"
        echo "✅ Created .env file"
        echo "⚠️  Please edit rag_server/.env and add your GEMINI_API_KEY"
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ Error: .env.example not found!"
        exit 1
    fi
fi

# --- Check if GEMINI_API_KEY is set ---
if grep -q "your_gemini_api_key_here" "$RAG_SERVER_DIR/.env"; then
    echo "❌ Error: GEMINI_API_KEY not configured in rag_server/.env"
    echo "   Please edit the file and add your actual API key"
    echo "   Get it from: https://aistudio.google.com/app/apikey"
    exit 1
fi

# --- Check if news data exists ---
NEWS_FILE="$RAG_SERVER_DIR/news/csie_news.csv"
if [ ! -f "$NEWS_FILE" ]; then
    echo "⚠️  Warning: News data not found at: $NEWS_FILE"
    echo "   The database will be created but may be empty."
    echo "   Consider running the crawler first to get data."
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# --- Virtual Environment Setup ---
echo "Step 1: Setting up Python environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$RAG_SERVER_DIR"

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# --- Install Dependencies ---
echo ""
echo "Step 2: Installing dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "requirements.txt" ]; then
    echo "📥 Installing packages from requirements.txt..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ Error: requirements.txt not found!"
    exit 1
fi

# --- Check if database already exists ---
echo ""
echo "Step 3: Checking existing database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "chroma_db" ]; then
    echo "⚠️  Warning: Existing database found at: chroma_db/"
    echo ""
    echo "Options:"
    echo "  1) Remove and rebuild (recommended)"
    echo "  2) Keep and append (may cause duplicates)"
    echo "  3) Abort"
    echo ""
    read -p "Choose (1/2/3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            echo "🗑️  Removing existing database..."
            # Handle macOS extended attributes
            if [[ "$OSTYPE" == "darwin"* ]]; then
                xattr -cr chroma_db 2>/dev/null || true
            fi
            # Try normal rm first
            rm -rf chroma_db 2>/dev/null || {
                echo "⚠️  Permission denied. Trying with sudo..."
                sudo rm -rf chroma_db
            }
            echo "✅ Old database removed"
            ;;
        2)
            echo "⚠️  Keeping existing database (may cause duplicates)"
            ;;
        3)
            echo "Aborted."
            exit 0
            ;;
        *)
            echo "Invalid choice. Aborting."
            exit 1
            ;;
    esac
else
    echo "✅ No existing database found"
fi

# --- Build Database ---
echo ""
echo "Step 4: Building vector database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🏗️  Running DBHandler.py..."
echo "   This may take a few minutes depending on data size..."
echo ""

# Run with output
python DBHandler.py

exit_code=$?

# --- Result ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $exit_code -eq 0 ]; then
    echo "✅ SUCCESS: Vector database created successfully!"
    echo ""
    echo "📊 Database info:"
    if [ -d "chroma_db" ]; then
        db_size=$(du -sh chroma_db | cut -f1)
        echo "   Location: $(pwd)/chroma_db"
        echo "   Size: $db_size"
    fi
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Start the RAG server:"
    echo "      cd $(dirname $SCRIPT_DIR)"
    echo "      docker-compose up"
    echo "      # or: make dev"
    echo ""
    echo "   2. Test the server:"
    echo "      curl http://localhost:8000/health"
else
    echo "❌ FAILURE: Database creation failed with exit code $exit_code"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   - Check if GEMINI_API_KEY is valid"
    echo "   - Verify news data exists in news/ folder"
    echo "   - Check error messages above"
    exit $exit_code
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
