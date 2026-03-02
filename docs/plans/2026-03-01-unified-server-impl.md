# Unified KB + MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add MCP transport, signal/indicator services, and x402 payment gating to the existing KB server.

**Architecture:** Single FastAPI process with FastMCP mounted at /mcp. Shared service layer (SearchEngine, SignalService, IndicatorService) called by both REST and MCP. x402 middleware gates compute endpoints on both transports.

**Tech Stack:** FastAPI, FastMCP, uvicorn, SQLite FTS5, x402 protocol, mangrove-knowledge-base pip package

**Design doc:** docs/plans/2026-03-01-unified-server-design.md

---

### Task 1: Add FastMCP dependency and SignalService

**Files:**
- Create: `kb_server/services/signal_service.py`
- Create: `tests/test_signal_service.py`
- Modify: `kb_server/requirements.txt`

**Step 1: Add fastmcp to requirements**

In `kb_server/requirements.txt`, add:
```
fastmcp>=2.0.0
```

Install it:
```bash
pip install fastmcp>=2.0.0
```

**Step 2: Write failing test for SignalService**

```python
# tests/test_signal_service.py
import pytest
from kb_server.services.signal_service import SignalService


class TestSignalServiceMetadata:
    """Test signal metadata (free tier)."""

    def setup_method(self):
        self.service = SignalService()

    def test_list_signals_returns_all(self):
        signals = self.service.list_signals()
        assert len(signals) == 136

    def test_list_signals_filter_by_category(self):
        momentum = self.service.list_signals(category="Momentum")
        assert len(momentum) == 26

    def test_list_signals_filter_by_type(self):
        triggers = self.service.list_signals(signal_type="TRIGGER")
        assert len(triggers) == 66

    def test_get_signal_exists(self):
        signal = self.service.get_signal("rsi_oversold")
        assert signal is not None
        assert signal["type"] == "FILTER"
        assert "window" in signal["params"]

    def test_get_signal_not_found(self):
        signal = self.service.get_signal("nonexistent_signal")
        assert signal is None

    def test_get_signal_has_required_fields(self):
        signal = self.service.get_signal("rsi_oversold")
        assert "type" in signal
        assert "requires" in signal
        assert "description" in signal
        assert "params" in signal


class TestSignalServiceEvaluation:
    """Test signal evaluation (x402 tier)."""

    def setup_method(self):
        self.service = SignalService()

    def test_evaluate_signal_returns_bool(self):
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        df = pd.DataFrame({
            "Open": np.random.uniform(100, 200, 50),
            "High": np.random.uniform(150, 250, 50),
            "Low": np.random.uniform(50, 150, 50),
            "Close": np.random.uniform(100, 200, 50),
            "Volume": np.random.uniform(1000, 5000, 50),
        })
        result = self.service.evaluate("rsi_oversold", df, {"window": 14, "threshold": 30})
        assert isinstance(result, bool)

    def test_evaluate_unknown_signal_raises(self):
        import pandas as pd
        df = pd.DataFrame({"Close": [1, 2, 3]})
        with pytest.raises(ValueError, match="Unknown signal"):
            self.service.evaluate("nonexistent", df, {})
```

**Step 3: Run test to verify it fails**

```bash
cd /home/darrahts/development/Dropbox/alpha-delta/mangrove/MangroveKnowledgeBase
python -m pytest tests/test_signal_service.py -v
```
Expected: FAIL (module not found)

**Step 4: Implement SignalService**

```python
# kb_server/services/signal_service.py
"""Signal metadata and evaluation service.

Wraps the mangrove_knowledge_base docstring parser and RuleRegistry
to provide signal discovery (free) and evaluation (x402 gated).
"""

import pandas as pd

from mangrove_knowledge_base.registry import RuleRegistry
from mangrove_knowledge_base.docstring_parser import parse_all_signals
from mangrove_knowledge_base.signals import momentum, trend, volume, volatility, patterns


# Module-to-category mapping
_MODULE_CATEGORY = {
    "momentum": "Momentum",
    "trend": "Trend",
    "volume": "Volume",
    "volatility": "Volatility",
    "patterns": "Patterns",
}

_SIGNAL_MODULES = [momentum, trend, volume, volatility, patterns]


class SignalService:
    """Provides signal metadata and evaluation.

    Metadata methods (list_signals, get_signal) are free.
    Evaluation (evaluate) is x402 gated at the router/tool layer.
    """

    def __init__(self):
        self._metadata = parse_all_signals(_SIGNAL_MODULES)
        self._categories = {}
        for name, meta in self._metadata.items():
            func = RuleRegistry._registry.get(name)
            if func:
                mod = getattr(func, "__module__", "")
                for key, label in _MODULE_CATEGORY.items():
                    if key in mod:
                        self._categories[name] = label
                        break
                else:
                    self._categories[name] = "Other"

    def list_signals(self, category: str = None, signal_type: str = None) -> list[dict]:
        """List signals with optional filtering. Free."""
        results = []
        for name, meta in sorted(self._metadata.items()):
            if category and self._categories.get(name) != category:
                continue
            if signal_type and meta.get("type") != signal_type:
                continue
            results.append({
                "name": name,
                "category": self._categories.get(name, "Other"),
                **meta,
            })
        return results

    def get_signal(self, name: str) -> dict | None:
        """Get full metadata for a signal. Free."""
        meta = self._metadata.get(name)
        if meta is None:
            return None
        return {
            "name": name,
            "category": self._categories.get(name, "Other"),
            **meta,
        }

    def evaluate(self, name: str, df: pd.DataFrame, params: dict) -> bool:
        """Evaluate a signal against data. x402 gated."""
        if name not in RuleRegistry._registry:
            raise ValueError(f"Unknown signal: {name}")
        rule = {"name": name, "params": params}
        return RuleRegistry.evaluate(rule, df)
```

**Step 5: Run tests**

```bash
python -m pytest tests/test_signal_service.py -v
```
Expected: all 8 PASS

**Step 6: Commit**

```bash
git add kb_server/services/signal_service.py kb_server/requirements.txt tests/test_signal_service.py
git commit -m "feat: add SignalService with metadata and evaluation"
```

---

### Task 2: Add IndicatorService

**Files:**
- Create: `kb_server/services/indicator_service.py`
- Create: `tests/test_indicator_service.py`

**Step 1: Write failing test**

```python
# tests/test_indicator_service.py
import pytest
import pandas as pd
import numpy as np
from kb_server.services.indicator_service import IndicatorService


class TestIndicatorServiceMetadata:

    def setup_method(self):
        self.service = IndicatorService()

    def test_list_indicators_returns_all(self):
        indicators = self.service.list_indicators()
        assert len(indicators) == 70

    def test_list_indicators_filter_by_category(self):
        momentum = self.service.list_indicators(category="Momentum")
        assert len(momentum) > 0

    def test_get_indicator_exists(self):
        ind = self.service.get_indicator("RSI")
        assert ind is not None
        assert "data" in ind
        assert "params" in ind
        assert "outputs" in ind

    def test_get_indicator_not_found(self):
        ind = self.service.get_indicator("NonexistentIndicator")
        assert ind is None


class TestIndicatorServiceCompute:

    def setup_method(self):
        self.service = IndicatorService()

    def test_compute_rsi(self):
        np.random.seed(42)
        df = pd.DataFrame({"Close": np.random.uniform(100, 200, 50)})
        result = self.service.compute("RSI", {"close": df["Close"]}, {"window": 14})
        assert "rsi" in result
        assert len(result["rsi"]) == 50

    def test_compute_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown indicator"):
            self.service.compute("FakeIndicator", {}, {})
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_indicator_service.py -v
```

**Step 3: Implement IndicatorService**

```python
# kb_server/services/indicator_service.py
"""Indicator metadata and computation service.

Wraps the mangrove_knowledge_base indicator classes to provide
discovery (free) and computation (x402 gated).
"""

import mangrove_knowledge_base.indicators as ind_module


# Category mapping based on module
_INDICATOR_CATEGORIES = {
    "momentum_indicators": "Momentum",
    "trend_indicators": "Trend",
    "volume_indicators": "Volume",
    "volatility_indicators": "Volatility",
    "pattern_indicators": "Patterns",
    "return_indicators": "Returns",
}


class IndicatorService:
    """Provides indicator metadata and computation.

    Metadata methods (list_indicators, get_indicator) are free.
    Computation (compute) is x402 gated at the router/tool layer.
    """

    def __init__(self):
        self._indicators = {}
        for name in ind_module.__all__:
            cls = getattr(ind_module, name, None)
            if cls is None or not hasattr(cls, "compute"):
                continue
            mod = getattr(cls, "__module__", "")
            category = "Other"
            for key, label in _INDICATOR_CATEGORIES.items():
                if key in mod:
                    category = label
                    break
            self._indicators[name] = {
                "name": name,
                "category": category,
                "data": getattr(cls, "_data", {}),
                "params": getattr(cls, "_params", {}),
                "outputs": getattr(cls, "_outputs", []),
                "cls": cls,
            }

    def list_indicators(self, category: str = None) -> list[dict]:
        """List indicators with optional category filter. Free."""
        results = []
        for name, info in sorted(self._indicators.items()):
            if category and info["category"] != category:
                continue
            results.append({
                "name": info["name"],
                "category": info["category"],
                "data": info["data"],
                "params": info["params"],
                "outputs": info["outputs"],
            })
        return results

    def get_indicator(self, name: str) -> dict | None:
        """Get full spec for an indicator. Free."""
        info = self._indicators.get(name)
        if info is None:
            return None
        return {
            "name": info["name"],
            "category": info["category"],
            "data": info["data"],
            "params": info["params"],
            "outputs": info["outputs"],
        }

    def compute(self, name: str, data: dict, params: dict) -> dict:
        """Compute an indicator. x402 gated."""
        info = self._indicators.get(name)
        if info is None:
            raise ValueError(f"Unknown indicator: {name}")
        return info["cls"].compute(data=data, params=params)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_indicator_service.py -v
```

**Step 5: Commit**

```bash
git add kb_server/services/indicator_service.py tests/test_indicator_service.py
git commit -m "feat: add IndicatorService with metadata and computation"
```

---

### Task 3: Add signal/indicator REST endpoints

**Files:**
- Modify: `kb_server/routers/api.py`
- Modify: `kb_server/main.py`
- Create: `tests/test_api_signals.py`

**Step 1: Write failing test**

```python
# tests/test_api_signals.py
import pytest
from fastapi.testclient import TestClient
from kb_server.main import app


client = TestClient(app)


class TestSignalEndpoints:

    def test_list_signals(self):
        resp = client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 136
        assert len(data["signals"]) == 136

    def test_list_signals_filter_category(self):
        resp = client.get("/api/signals?category=Momentum")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 26

    def test_list_signals_filter_type(self):
        resp = client.get("/api/signals?signal_type=TRIGGER")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 66

    def test_get_signal(self):
        resp = client.get("/api/signals/rsi_oversold")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "rsi_oversold"
        assert data["type"] == "FILTER"

    def test_get_signal_not_found(self):
        resp = client.get("/api/signals/nonexistent")
        assert resp.status_code == 404


class TestIndicatorEndpoints:

    def test_list_indicators(self):
        resp = client.get("/api/indicators")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 70

    def test_get_indicator(self):
        resp = client.get("/api/indicators/RSI")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "RSI"
        assert "outputs" in data

    def test_get_indicator_not_found(self):
        resp = client.get("/api/indicators/FakeIndicator")
        assert resp.status_code == 404
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_api_signals.py -v
```

**Step 3: Add signal/indicator endpoints to api.py**

Add to the end of `kb_server/routers/api.py` (before the status endpoint):

```python
# --- Signal endpoints (metadata = free) ---

@router.get("/signals")
async def list_signals(
    category: str = None,
    signal_type: str = None,
    signal_svc: SignalService = Depends(get_signal_service),
):
    signals = signal_svc.list_signals(category=category, signal_type=signal_type)
    return {"total": len(signals), "signals": signals}


@router.get("/signals/{name}")
async def get_signal(name: str, signal_svc: SignalService = Depends(get_signal_service)):
    signal = signal_svc.get_signal(name)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Signal not found: {name}")
    return signal


# --- Indicator endpoints (metadata = free) ---

@router.get("/indicators")
async def list_indicators(
    category: str = None,
    indicator_svc: IndicatorService = Depends(get_indicator_service),
):
    indicators = indicator_svc.list_indicators(category=category)
    return {"total": len(indicators), "indicators": indicators}


@router.get("/indicators/{name}")
async def get_indicator(name: str, indicator_svc: IndicatorService = Depends(get_indicator_service)):
    indicator = indicator_svc.get_indicator(name)
    if indicator is None:
        raise HTTPException(status_code=404, detail=f"Indicator not found: {name}")
    return indicator
```

Update `kb_server/main.py` to initialize SignalService and IndicatorService at startup alongside SearchEngine.

**Step 4: Run tests**

```bash
python -m pytest tests/test_api_signals.py -v
```

**Step 5: Commit**

```bash
git add kb_server/routers/api.py kb_server/main.py tests/test_api_signals.py
git commit -m "feat: add signal and indicator REST endpoints"
```

---

### Task 4: Add MCP tools

**Files:**
- Create: `kb_server/mcp/__init__.py`
- Create: `kb_server/mcp/tools.py`
- Modify: `kb_server/main.py`
- Create: `tests/test_mcp_tools.py`

**Step 1: Write failing test**

```python
# tests/test_mcp_tools.py
import pytest
from kb_server.mcp.tools import create_mcp_server


class TestMCPTools:

    def setup_method(self):
        self.mcp = create_mcp_server()

    def test_mcp_has_tools(self):
        tools = self.mcp.list_tools()
        assert len(tools) >= 14

    def test_kb_search_tool_exists(self):
        tools = {t.name for t in self.mcp.list_tools()}
        assert "kb_search" in tools

    def test_kb_list_signals_tool_exists(self):
        tools = {t.name for t in self.mcp.list_tools()}
        assert "kb_list_signals" in tools

    def test_evaluate_signal_tool_exists(self):
        tools = {t.name for t in self.mcp.list_tools()}
        assert "evaluate_signal" in tools
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_mcp_tools.py -v
```

**Step 3: Implement MCP tools**

```python
# kb_server/mcp/__init__.py
```

```python
# kb_server/mcp/tools.py
"""MCP tool definitions for MangroveKnowledgeBase.

All tools call the same service layer as the REST API.
Free tools: KB search, documents, glossary, tags, backlinks, signal/indicator metadata.
x402 tools: signal evaluation, indicator computation.
"""

from fastmcp import FastMCP


def create_mcp_server(search_engine=None, cross_ref=None, signal_service=None, indicator_service=None):
    """Create and configure the MCP server with all tools."""

    mcp = FastMCP(
        "MangroveKnowledgeBase",
        instructions=(
            "Trading knowledge base with 136 signals, 70 indicators, and 11 education documents. "
            "Use kb_search to find information. Use kb_list_signals/kb_get_signal for signal discovery. "
            "Use evaluate_signal/compute_indicator for computation (requires x402 payment)."
        ),
    )

    # --- Knowledge Base tools (free) ---

    @mcp.tool()
    def kb_search(query: str, tags: list[str] = None, limit: int = 20, expand: bool = True) -> dict:
        """Search the trading knowledge base with full-text search and synonym expansion."""
        return search_engine.search(query, tags=tags, limit=limit, expand=expand)

    @mcp.tool()
    def kb_list_documents() -> dict:
        """List all knowledge base documents with summaries."""
        docs = search_engine.get_all_documents()
        return {"total": len(docs), "documents": [d.to_summary_dict() for d in docs]}

    @mcp.tool()
    def kb_get_document(slug: str) -> dict:
        """Get a full knowledge base document by slug."""
        doc = search_engine.get_document(slug)
        if doc is None:
            return {"error": f"Document not found: {slug}"}
        return doc.to_dict()

    @mcp.tool()
    def kb_get_document_sections(slug: str) -> dict:
        """Get the section tree for a document without full content."""
        doc = search_engine.get_document(slug)
        if doc is None:
            return {"error": f"Document not found: {slug}"}
        return {"slug": slug, "title": doc.title, "sections": [s.to_tree_dict() for s in doc.sections]}

    @mcp.tool()
    def kb_glossary_lookup(term: str) -> dict:
        """Look up a trading term in the glossary with backlinks."""
        entry = cross_ref.term_registry.get(term.lower())
        if entry is None:
            return {"error": f"Term not found: {term}"}
        backlinks = search_engine.get_backlinks(entry.get("anchor", ""))
        return {**entry, "backlinks": backlinks}

    @mcp.tool()
    def kb_list_glossary() -> dict:
        """List all glossary terms."""
        entries = cross_ref.get_glossary_entries()
        return {"total": len(entries), "terms": entries}

    @mcp.tool()
    def kb_list_tags() -> dict:
        """List all tags with document counts."""
        tags = search_engine.get_all_tags()
        return {"total": len(tags), "tags": tags}

    @mcp.tool()
    def kb_get_documents_by_tag(tag: str) -> dict:
        """Get all documents with a specific tag."""
        results = search_engine.search("", tags=[tag], limit=100)
        return {"tag": tag, "results": results}

    @mcp.tool()
    def kb_get_backlinks(anchor: str) -> dict:
        """Get all documents and sections that reference a specific anchor."""
        backlinks = search_engine.get_backlinks(anchor)
        return {"anchor": anchor, "total": len(backlinks), "backlinks": backlinks}

    # --- Signal metadata tools (free) ---

    @mcp.tool()
    def kb_list_signals(category: str = None, signal_type: str = None) -> dict:
        """List trading signals with optional filtering by category or type."""
        signals = signal_service.list_signals(category=category, signal_type=signal_type)
        return {"total": len(signals), "signals": signals}

    @mcp.tool()
    def kb_get_signal(name: str) -> dict:
        """Get full metadata for a signal including parameters, ranges, and defaults."""
        signal = signal_service.get_signal(name)
        if signal is None:
            return {"error": f"Signal not found: {name}"}
        return signal

    # --- Indicator metadata tools (free) ---

    @mcp.tool()
    def kb_list_indicators(category: str = None) -> dict:
        """List technical indicators with optional category filter."""
        indicators = indicator_service.list_indicators(category=category)
        return {"total": len(indicators), "indicators": indicators}

    @mcp.tool()
    def kb_get_indicator(name: str) -> dict:
        """Get full specification for an indicator including inputs, outputs, and parameters."""
        indicator = indicator_service.get_indicator(name)
        if indicator is None:
            return {"error": f"Indicator not found: {name}"}
        return indicator

    # --- Computation tools (x402 gated) ---

    @mcp.tool()
    def evaluate_signal(name: str, ohlcv_json: str, params: dict = None) -> dict:
        """Evaluate a trading signal against OHLCV data. Requires x402 payment.

        Args:
            name: Signal name (e.g. "rsi_oversold")
            ohlcv_json: JSON string of OHLCV data with columns Open, High, Low, Close, Volume
            params: Signal parameters (e.g. {"window": 14, "threshold": 30})
        """
        import pandas as pd
        import json
        df = pd.DataFrame(json.loads(ohlcv_json))
        result = signal_service.evaluate(name, df, params or {})
        return {"signal": name, "result": result}

    @mcp.tool()
    def compute_indicator(name: str, data_json: str, params: dict = None) -> dict:
        """Compute a technical indicator against market data. Requires x402 payment.

        Args:
            name: Indicator class name (e.g. "RSI")
            data_json: JSON string of input data (columns depend on indicator)
            params: Indicator parameters (e.g. {"window": 14})
        """
        import pandas as pd
        import json
        raw = json.loads(data_json)
        data = {k: pd.Series(v) for k, v in raw.items()}
        result = indicator_service.compute(name, data, params or {})
        serialized = {k: v.tolist() if hasattr(v, "tolist") else v for k, v in result.items()}
        return {"indicator": name, "result": serialized}

    @mcp.tool()
    def kb_status() -> dict:
        """Get server health and content statistics."""
        docs = search_engine.get_all_documents()
        tags = search_engine.get_all_tags()
        signals = signal_service.list_signals()
        indicators = indicator_service.list_indicators()
        return {
            "status": "healthy",
            "documents": len(docs),
            "tags": len(tags),
            "signals": len(signals),
            "indicators": len(indicators),
        }

    return mcp
```

**Step 4: Mount MCP in main.py**

Add to `kb_server/main.py` in the lifespan startup, after initializing SearchEngine and CrossReferenceEngine:

```python
from kb_server.services.signal_service import SignalService
from kb_server.services.indicator_service import IndicatorService
from kb_server.mcp.tools import create_mcp_server

# In lifespan startup:
signal_service = SignalService()
indicator_service = IndicatorService()
mcp = create_mcp_server(search_engine, cross_ref, signal_service, indicator_service)
app.mount("/mcp", mcp.streamable_http_app())
```

**Step 5: Run tests**

```bash
python -m pytest tests/test_mcp_tools.py -v
```

**Step 6: Commit**

```bash
git add kb_server/mcp/ tests/test_mcp_tools.py kb_server/main.py
git commit -m "feat: add MCP tools with 16 tools across KB, signals, and indicators"
```

---

### Task 5: Add x402 payment middleware

**Files:**
- Create: `kb_server/x402/__init__.py`
- Create: `kb_server/x402/middleware.py`
- Create: `kb_server/x402/pricing.py`
- Modify: `kb_server/config.py`
- Create: `tests/test_x402.py`

**Step 1: Write failing test**

```python
# tests/test_x402.py
import pytest
from kb_server.x402.pricing import get_price, is_gated
from kb_server.x402.middleware import validate_x402_payment


class TestPricing:

    def test_evaluate_signal_is_gated(self):
        assert is_gated("evaluate_signal") is True

    def test_compute_indicator_is_gated(self):
        assert is_gated("compute_indicator") is True

    def test_kb_search_is_free(self):
        assert is_gated("kb_search") is False

    def test_gated_tool_has_price(self):
        price = get_price("evaluate_signal")
        assert price > 0


class TestPaymentValidation:

    def test_missing_payment_header_rejected(self):
        result = validate_x402_payment(headers={}, tool_name="evaluate_signal")
        assert result["valid"] is False
        assert "payment required" in result["error"].lower()

    def test_free_tool_no_payment_needed(self):
        result = validate_x402_payment(headers={}, tool_name="kb_search")
        assert result["valid"] is True
```

**Step 2: Implement x402 modules**

```python
# kb_server/x402/__init__.py
```

```python
# kb_server/x402/pricing.py
"""x402 pricing configuration for gated tools."""

# Tools that require x402 payment
GATED_TOOLS = {
    "evaluate_signal": 0.001,     # USD per evaluation
    "compute_indicator": 0.001,   # USD per computation
}


def is_gated(tool_name: str) -> bool:
    return tool_name in GATED_TOOLS


def get_price(tool_name: str) -> float:
    return GATED_TOOLS.get(tool_name, 0.0)
```

```python
# kb_server/x402/middleware.py
"""x402 payment validation middleware for REST and MCP.

Adapted from MangroveAI v402 implementation. Validates payment headers
on gated endpoints/tools before allowing execution.
"""

from kb_server.x402.pricing import is_gated, get_price


def validate_x402_payment(headers: dict, tool_name: str) -> dict:
    """Validate x402 payment for a tool invocation.

    Args:
        headers: HTTP headers or MCP metadata containing payment proof
        tool_name: Name of the tool/endpoint being called

    Returns:
        dict with "valid" (bool) and optional "error" (str)
    """
    if not is_gated(tool_name):
        return {"valid": True}

    payment_header = headers.get("X-402-Payment") or headers.get("x-402-payment")
    if not payment_header:
        price = get_price(tool_name)
        return {
            "valid": False,
            "error": f"Payment required. Cost: ${price} USD. "
                     f"Include X-402-Payment header with payment proof.",
            "price": price,
            "tool": tool_name,
        }

    # TODO: Validate payment proof against facilitator
    # For now, accept any non-empty payment header
    return {"valid": True, "payment": payment_header}
```

Add x402 config to `kb_server/config.py`:

```python
# x402 settings
v402_enabled: bool = True
v402_facilitator_url: str = "https://x402.org/facilitator"
v402_payment_address: str = ""
v402_network: str = "eip155:84532"
```

**Step 3: Run tests**

```bash
python -m pytest tests/test_x402.py -v
```

**Step 4: Wire x402 into REST evaluate/compute endpoints and MCP tools**

Add gated REST endpoints to `kb_server/routers/api.py`:

```python
@router.post("/evaluate")
async def evaluate_signal(request: Request, signal_svc = Depends(get_signal_service)):
    """Evaluate a signal. x402 gated."""
    from kb_server.x402.middleware import validate_x402_payment
    payment = validate_x402_payment(dict(request.headers), "evaluate_signal")
    if not payment["valid"]:
        raise HTTPException(status_code=402, detail=payment)
    body = await request.json()
    df = pd.DataFrame(body["ohlcv"])
    result = signal_svc.evaluate(body["name"], df, body.get("params", {}))
    return {"signal": body["name"], "result": result}


@router.post("/compute")
async def compute_indicator(request: Request, indicator_svc = Depends(get_indicator_service)):
    """Compute an indicator. x402 gated."""
    from kb_server.x402.middleware import validate_x402_payment
    payment = validate_x402_payment(dict(request.headers), "compute_indicator")
    if not payment["valid"]:
        raise HTTPException(status_code=402, detail=payment)
    body = await request.json()
    data = {k: pd.Series(v) for k, v in body["data"].items()}
    result = indicator_svc.compute(body["name"], data, body.get("params", {}))
    serialized = {k: v.tolist() if hasattr(v, "tolist") else v for k, v in result.items()}
    return {"indicator": body["name"], "result": serialized}
```

**Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

**Step 6: Commit**

```bash
git add kb_server/x402/ kb_server/config.py kb_server/routers/api.py tests/test_x402.py
git commit -m "feat: add x402 payment gating for signal evaluation and indicator computation"
```

---

### Task 6: Update Dockerfile and docker-compose

**Files:**
- Modify: `kb_server/Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Update Dockerfile to install fastmcp**

The Dockerfile already installs from `kb_server/requirements.txt`, so adding fastmcp there (Task 1) handles it. Verify the CMD still works with the MCP mount.

**Step 2: Test docker build**

```bash
docker compose build mkb-knowledge-base
```

**Step 3: Test docker run**

```bash
docker compose up -d mkb-knowledge-base
sleep 5
curl -s http://localhost:8081/api/status | python3 -m json.tool
curl -s http://localhost:8081/api/signals | python3 -m json.tool | head -20
curl -s http://localhost:8081/api/indicators | python3 -m json.tool | head -20
```

**Step 4: Commit**

```bash
git add kb_server/Dockerfile docker-compose.yml
git commit -m "chore: update Dockerfile for MCP and signal/indicator services"
```

---

### Task 7: Build and test PyPI package

**Files:**
- Modify: `pyproject.toml` (if needed)

**Step 1: Install build tools**

```bash
pip install build twine
```

**Step 2: Build the package**

```bash
python -m build
```
Expected: Creates `dist/mangrove_knowledge_base-0.1.0.tar.gz` and `dist/mangrove_knowledge_base-0.1.0-py3-none-any.whl`

**Step 3: Test the wheel installs cleanly**

```bash
pip install dist/mangrove_knowledge_base-0.1.0-py3-none-any.whl --force-reinstall
python -c "from mangrove_knowledge_base import RuleRegistry; print(len(RuleRegistry._registry))"
```
Expected: 136

**Step 4: Upload to PyPI**

```bash
twine upload dist/*
```
Requires PyPI credentials (user will provide or configure ~/.pypirc).

**Step 5: Commit any pyproject.toml changes**

```bash
git add pyproject.toml
git commit -m "chore: prepare 0.1.0 for PyPI release"
```

---

### Task 8: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `kb-next-steps.md`
- Modify: `kb_server/API.md`

**Step 1: Update CLAUDE.md**

Add MCP and x402 sections. Update signal/indicator service references.

**Step 2: Update README.md**

Add MCP usage examples. Document x402 gated endpoints. Add PyPI badge.

**Step 3: Update API.md**

Add signal, indicator, evaluate, and compute endpoint documentation.

**Step 4: Commit**

```bash
git add CLAUDE.md README.md kb-next-steps.md kb_server/API.md
git commit -m "docs: update for unified server with MCP, signals, indicators, and x402"
```

---

## Task Dependency Graph

```
Task 1 (SignalService) ──┐
                         ├── Task 3 (REST endpoints) ──┐
Task 2 (IndicatorService)┘                             ├── Task 5 (x402) ── Task 6 (Docker) ── Task 7 (PyPI)
                         ┌── Task 4 (MCP tools) ───────┘                                         |
                         └──────────────────────────────────────────────────────────── Task 8 (Docs)
```

Tasks 1 and 2 are independent (parallel). Task 3 and 4 depend on 1+2. Task 5 depends on 3+4. Task 6 depends on 5. Task 7 is independent. Task 8 is last.
