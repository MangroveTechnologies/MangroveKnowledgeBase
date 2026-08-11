"""MCP tools for the MangroveKnowledgeBase server.

Exposes 16 tools via FastMCP:
  - 9 free KB tools (search, documents, glossary, tags, backlinks)
  - 4 free signal/indicator discovery tools
  - 2 x402-gated compute tools (evaluate_signal, compute_indicator)
  - 1 status tool
"""

import json
import logging
from typing import Optional

import pandas as pd
from fastmcp import FastMCP

from ..services.search_engine import SearchEngine
from ..services.cross_reference import CrossReferenceEngine
from ..services.signal_service import SignalService
from ..services.indicator_service import IndicatorService

logger = logging.getLogger(__name__)


def create_mcp_server(
    search_engine: Optional[SearchEngine],
    cross_ref: Optional[CrossReferenceEngine],
    signal_service: Optional[SignalService],
    indicator_service: Optional[IndicatorService],
) -> FastMCP:
    """Create and return a FastMCP server with all KB tools registered."""

    mcp = FastMCP(
        "MangroveKnowledgeBase",
        instructions=(
            "Mangrove Knowledge Base MCP server. Provides trading education documents, "
            "signal metadata, indicator specs, glossary, and full-text search. "
            "evaluate_signal and compute_indicator require x402 payment."
        ),
    )

    # =========================================================================
    # KB search and document tools (9)
    # =========================================================================

    @mcp.tool()
    def kb_search(
        query: str,
        tags: Optional[str] = None,
        limit: int = 20,
        expand: bool = True,
    ) -> dict:
        """Search the trading knowledge base using full-text search with Porter stemming and synonym expansion.

        Args:
            query: Search query string.
            tags: Optional comma-separated tags to filter by.
            limit: Maximum results (1-100, default 20).
            expand: Enable synonym/stem expansion (default True).

        Returns:
            Search results with snippets, relevance scores, and matched tags.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        tag_list = None
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        result = search_engine.search(query=query, tags=tag_list, limit=limit, expand=expand)
        return result.model_dump()

    @mcp.tool()
    def kb_list_documents() -> dict:
        """List all documents in the knowledge base.

        Returns:
            Document summaries with slug, title, summary, tags, and section count.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        docs = search_engine.get_all_documents()
        return {"total": len(docs), "documents": docs}

    @mcp.tool()
    def kb_get_document(slug: str) -> dict:
        """Get a single document by slug with full content and sections.

        Args:
            slug: The document slug identifier.

        Returns:
            Full document with content, sections, and tags.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        doc = search_engine.get_document(slug)
        if doc is None:
            return {"error": f"Document '{slug}' not found"}
        return doc

    @mcp.tool()
    def kb_get_document_sections(slug: str) -> dict:
        """Get the section tree for a document.

        Args:
            slug: The document slug identifier.

        Returns:
            Hierarchical section structure for the document.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        doc = search_engine.get_document(slug)
        if doc is None:
            return {"error": f"Document '{slug}' not found"}
        return {
            "document_slug": slug,
            "document_title": doc["title"],
            "sections": doc["sections"],
        }

    @mcp.tool()
    def kb_glossary_lookup(term: str) -> dict:
        """Look up a specific glossary term with its definition and backlinks.

        Args:
            term: The glossary term to look up.

        Returns:
            Term definition, abbreviation, anchor, document slug, and backlinks.
        """
        if cross_ref is None:
            return {"error": "Cross-reference engine not initialized"}

        term_def = cross_ref.term_registry.get(term)
        if not term_def:
            term_lower = term.lower()
            for key in cross_ref.term_registry:
                if key.lower() == term_lower:
                    term_def = cross_ref.term_registry[key]
                    break

        if not term_def:
            return {"error": f"Term '{term}' not found"}

        backlinks = []
        if search_engine is not None:
            backlinks = search_engine.get_backlinks(term_def.anchor)

        return {
            "term": term_def.term,
            "abbreviation": term_def.abbreviation,
            "definition": term_def.definition,
            "anchor": term_def.anchor,
            "document_slug": term_def.document_slug,
            "backlinks": backlinks,
        }

    @mcp.tool()
    def kb_list_glossary() -> dict:
        """List all glossary entries with definitions.

        Returns:
            All glossary terms with abbreviations, definitions, and related terms.
        """
        if cross_ref is None:
            return {"error": "Cross-reference engine not initialized"}

        entries = cross_ref.get_glossary_entries()
        return {
            "total": len(entries),
            "entries": [e.model_dump() for e in entries],
        }

    @mcp.tool()
    def kb_list_tags() -> dict:
        """List all tags in the knowledge base with document counts.

        Returns:
            Tags with their associated document counts.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        tags = search_engine.get_all_tags()
        return {
            "total": len(tags),
            "tags": [{"name": name, "count": count} for name, count in tags.items()],
        }

    @mcp.tool()
    def kb_get_documents_by_tag(tag_name: str) -> dict:
        """Get all documents associated with a specific tag.

        Args:
            tag_name: The tag to filter by.

        Returns:
            Documents that have the specified tag.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        results = search_engine.search(query="*", tags=[tag_name.lower()], limit=100, expand=False)
        seen_docs = set()
        documents = []
        for result in results.results:
            if result.document_slug not in seen_docs:
                seen_docs.add(result.document_slug)
                documents.append({
                    "slug": result.document_slug,
                    "title": result.document_title,
                    "tags": result.tags,
                })
        return {"tag": tag_name, "total": len(documents), "documents": documents}

    @mcp.tool()
    def kb_get_backlinks(anchor: str) -> dict:
        """Get all documents and sections that reference a specific anchor.

        Args:
            anchor: The target anchor to find backlinks for.

        Returns:
            List of backlinks with source document info.
        """
        if search_engine is None:
            return {"error": "Search engine not initialized"}
        backlinks = search_engine.get_backlinks(anchor)
        return {"target_anchor": anchor, "total": len(backlinks), "backlinks": backlinks}

    # =========================================================================
    # Signal and indicator discovery tools (4)
    # =========================================================================

    @mcp.tool()
    def kb_list_signals(
        category: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> dict:
        """List available trading signals with optional filtering.

        Args:
            category: Filter by category (Oscillator, Momentum, Averaging,
                Volatility, Pattern, Trend, Flow, On-Chain, DeFi Pro).
            signal_type: Filter by type (TRIGGER or FILTER).

        Returns:
            List of signals with name, category, type, parameters, and requirements.
        """
        if signal_service is None:
            return {"error": "Signal service not initialized"}
        signals = signal_service.list_signals(category=category, signal_type=signal_type)
        return {"total": len(signals), "signals": signals}

    @mcp.tool()
    def kb_get_signal(name: str) -> dict:
        """Get full metadata for a specific signal.

        Args:
            name: The signal function name (e.g. rsi_oversold, macd_bullish_cross).

        Returns:
            Signal metadata including type, category, parameters with ranges and defaults, and requirements.
        """
        if signal_service is None:
            return {"error": "Signal service not initialized"}
        signal = signal_service.get_signal(name)
        if signal is None:
            return {"error": f"Signal '{name}' not found"}
        return signal

    @mcp.tool()
    def kb_list_indicators(
        category: Optional[str] = None,
    ) -> dict:
        """List available technical indicators with optional category filter.

        Args:
            category: Filter by category (Momentum, Trend, Volume, Volatility, Patterns, Returns).

        Returns:
            List of indicators with name, category, data requirements, parameters, and outputs.
        """
        if indicator_service is None:
            return {"error": "Indicator service not initialized"}
        indicators = indicator_service.list_indicators(category=category)
        return {"total": len(indicators), "indicators": indicators}

    @mcp.tool()
    def kb_get_indicator(name: str) -> dict:
        """Get full spec for a specific indicator.

        Args:
            name: The indicator class name (e.g. RSI, MACD, BollingerBands).

        Returns:
            Indicator spec including data requirements, parameters, and output columns.
        """
        if indicator_service is None:
            return {"error": "Indicator service not initialized"}
        indicator = indicator_service.get_indicator(name)
        if indicator is None:
            return {"error": f"Indicator '{name}' not found"}
        return indicator

    # =========================================================================
    # x402-gated compute tools (2)
    # =========================================================================

    @mcp.tool()
    def evaluate_signal(
        name: str,
        ohlcv_json: str,
        params_json: str = "{}",
    ) -> dict:
        """Evaluate a trading signal against OHLCV data. Requires x402 payment.

        Args:
            name: Signal function name (e.g. rsi_oversold).
            ohlcv_json: JSON string of OHLCV data as array of objects with columns: open, high, low, close, volume.
            params_json: JSON string of signal parameters (optional, uses defaults if omitted).

        Returns:
            Signal evaluation result (true/false) indicating whether the signal condition is met.
        """
        if signal_service is None:
            return {"error": "Signal service not initialized"}
        try:
            data = json.loads(ohlcv_json)
            df = pd.DataFrame(data)
            params = json.loads(params_json)
            result = signal_service.evaluate(name, df, params)
            return {"signal": name, "result": bool(result), "params": params}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Evaluation failed: {e}"}

    @mcp.tool()
    def compute_indicator(
        name: str,
        data_json: str,
        params_json: str = "{}",
    ) -> dict:
        """Compute a technical indicator from market data. Requires x402 payment.

        Args:
            name: Indicator class name (e.g. RSI, MACD).
            data_json: JSON string of input data. Format depends on the indicator's data requirements.
            params_json: JSON string of indicator parameters (optional, uses defaults if omitted).

        Returns:
            Computed indicator values as a dictionary of output columns.
        """
        if indicator_service is None:
            return {"error": "Indicator service not initialized"}
        try:
            data_raw = json.loads(data_json)
            params = json.loads(params_json)
            # Convert lists/arrays to pandas Series for computation
            data = {}
            for key, value in data_raw.items():
                if isinstance(value, list):
                    data[key] = pd.Series(value)
                else:
                    data[key] = value
            result = indicator_service.compute(name, data, params)
            # Convert any pandas objects to JSON-serializable format
            serializable = {}
            for key, value in result.items():
                if isinstance(value, pd.Series):
                    serializable[key] = value.tolist()
                elif isinstance(value, pd.DataFrame):
                    serializable[key] = value.to_dict(orient="list")
                else:
                    serializable[key] = value
            return {"indicator": name, "result": serializable, "params": params}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Computation failed: {e}"}

    # =========================================================================
    # Status tool (1)
    # =========================================================================

    @mcp.tool()
    def kb_status() -> dict:
        """Get the current status of the MangroveKnowledgeBase server.

        Returns:
            Health status, document count, tag count, signal count, and indicator count.
        """
        status = {"status": "healthy"}

        if search_engine is not None:
            docs = search_engine.get_all_documents()
            tags = search_engine.get_all_tags()
            status["documents_count"] = len(docs)
            status["tags_count"] = len(tags)

        if cross_ref is not None:
            status["terms_registered"] = len(cross_ref.term_registry)

        if signal_service is not None:
            status["signals_count"] = len(signal_service.list_signals())

        if indicator_service is not None:
            status["indicators_count"] = len(indicator_service.list_indicators())

        return status

    return mcp
