"""Startup verification script for WorkGuard Admin Server.

This script checks that all components are properly configured and can be imported.
Run this after installation to verify the setup is correct.
"""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv

# Add admin-server to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")


def check_environment():
    """Verify environment variables are configured."""
    required_vars = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "WORKGUARD_AES_KEY_BASE64",
    ]
    
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print(f"   Copy .env.example to .env and fill in the values")
        return False
    
    print(f"✓ Environment variables configured")
    return True


def check_imports():
    """Verify all modules can be imported."""
    modules = [
        ("database.connection", "Database connection"),
        ("database.schema", "Database schema"),
        ("database.repository", "Database repository"),
        ("ingestion.encryption", "Ingestion encryption"),
        ("embeddings", "Embeddings"),
        ("llm", "LLM client"),
        ("tools.postgres_tools", "PostgreSQL tools"),
        ("tools.faiss_tools", "FAISS tools"),
        ("agents.state", "Agent state"),
        ("agents.supervisor_agent", "Supervisor agent"),
        ("agents.session_analysis_agent", "Session analysis agent"),
        ("agents.knowledge_agent", "Knowledge agent"),
        ("agents.security_agent", "Security agent"),
        ("agents.reporting_agent", "Reporting agent"),
        ("agents.workflow", "Agent workflow"),
        ("agents.processor", "Session processor"),
        ("api.routes", "API routes"),
    ]
    
    all_ok = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✓ {description} ({module_name})")
        except ImportError as e:
            print(f"❌ {description} ({module_name}): {e}")
            all_ok = False
        except Exception as e:
            print(f"⚠ {description} ({module_name}): {e}")
    
    return all_ok


def check_database():
    """Verify database connection."""
    try:
        from database.connection import get_connection
        conn = get_connection()
        conn.close()
        print(f"✓ PostgreSQL database connection")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL database connection: {e}")
        return False


def check_ollama():
    """Verify Ollama is available."""
    try:
        from llm import get_ollama_client
        client = get_ollama_client()
        if client.is_available():
            print(f"✓ Ollama LLM available")
            return True
        else:
            print(f"⚠ Ollama LLM not responding (may not be running)")
            return False
    except Exception as e:
        print(f"❌ Ollama LLM check failed: {e}")
        return False


def check_embeddings():
    """Verify embeddings can be initialized."""
    try:
        from embeddings import get_embedding_provider
        provider = get_embedding_provider()
        print(f"✓ Embedding model loaded ({provider.model_name})")
        return True
    except Exception as e:
        print(f"⚠ Embedding model: {e}")
        return False


def main():
    """Run all startup checks."""
    print("\n" + "="*60)
    print("WorkGuard Admin Server - Startup Verification")
    print("="*60 + "\n")
    
    checks = [
        ("Environment", check_environment),
        ("Imports", check_imports),
        ("Database", check_database),
        ("Ollama LLM", check_ollama),
        ("Embeddings", check_embeddings),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_ok = all(result for _, result in results)
    
    if all_ok:
        print("\n✓ All checks passed! Admin server is ready to start.")
        print(f"   Run: uvicorn main:app --reload")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
