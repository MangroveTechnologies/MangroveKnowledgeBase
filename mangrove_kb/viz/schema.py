# Reimplemented against the trimmed vendored schema.sql (upstream: jarvis
# src/jarvis/session/schema.py). CC BY-NC-SA 4.0 — see ATTRIBUTION.md.
"""Schema loader — fills the ontology CHECK lists in `schema.sql` from `ontology.py`.

The vocabulary is declared exactly once, in the ontology, so the SQL constraints cannot drift from
the Python model.
"""
from __future__ import annotations

from pathlib import Path

_SCHEMA = Path(__file__).with_name("schema.sql")


def _sql_list(values) -> str:
    return ", ".join(f"'{v}'" for v in sorted(values))


def schema_ddl() -> str:
    from . import ontology as ont
    return (_SCHEMA.read_text()
            .replace("__PRIMITIVE_TYPES__", _sql_list(ont.PRIMITIVE_TYPES))
            .replace("__RELATIONS__", _sql_list(ont.RELATIONS)))
