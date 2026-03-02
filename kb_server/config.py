"""
Configuration settings for the Knowledge Base Document Server.
"""

import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

    # Knowledge base paths
    # Default: look for knowledge-base/ one level up from kb_server/
    kb_path: Path = Path(__file__).parent.parent / "knowledge-base"
    db_path: Path = Path(__file__).parent / "data" / "knowledge.db"

    # Search settings
    default_search_limit: int = 20
    snippet_length: int = 200
    enable_query_expansion: bool = True

    # Cross-reference settings
    max_links_per_section: int = 1  # Only first occurrence gets linked

    # x402 payment settings
    v402_enabled: bool = True
    v402_facilitator_url: str = "https://x402.org/facilitator"
    v402_payment_address: str = ""
    v402_network: str = "eip155:84532"

    class Config:
        env_prefix = "KB_SERVER_"


def get_settings() -> Settings:
    """Get application settings, loading from environment if available."""
    settings = Settings()

    # Override with environment variables if set
    if os.getenv("KB_SERVER_KB_PATH"):
        settings.kb_path = Path(os.getenv("KB_SERVER_KB_PATH"))
    if os.getenv("KB_SERVER_DB_PATH"):
        settings.db_path = Path(os.getenv("KB_SERVER_DB_PATH"))
    if os.getenv("KB_SERVER_PORT"):
        settings.port = int(os.getenv("KB_SERVER_PORT"))
    if os.getenv("KB_SERVER_DEBUG"):
        settings.debug = os.getenv("KB_SERVER_DEBUG").lower() == "true"

    return settings


# Global settings instance
settings = get_settings()
