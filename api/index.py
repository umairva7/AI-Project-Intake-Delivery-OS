"""
Vercel Serverless Function entrypoint.
Exposes the FastAPI application instance for Vercel's Python runtime.
"""
import sys
import os
from pathlib import Path

# Add project root directory to Python module search path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Configure writable SQLite database location in serverless environment
if os.environ.get("VERCEL"):
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/intake.db")

from app.main import app
