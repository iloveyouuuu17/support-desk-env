"""
server/app.py — OpenEnv multi-mode deployment server entry point.
"""
import os
import sys

# Ensure root package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401

__all__ = ["app", "main"]


def main():
    """Start the SupportDeskEnv server (openenv multi-mode entry point)."""
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
