"""
server/app.py — OpenEnv multi-mode deployment entry point.

This module re-exports the FastAPI app from the root app.py so the
openenv validator can locate the server entry point at server/app.py.
"""
import sys
import os

# Ensure root package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, main  # noqa: F401

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
