"""
Knowledge Base Document Server

A FastAPI application that serves the trading knowledge base with:
- Full-text search using SQLite FTS5 with Porter stemming
- Automatic cross-referencing with code-block safety
- Synonym support and query expansion
- Navigable HTML UI with stable anchors
"""

__version__ = "1.0.0"
