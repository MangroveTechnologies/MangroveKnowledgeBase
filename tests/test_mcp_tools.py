"""Tests for MCP tools registration and availability."""

import asyncio
import pytest
from kb_server.mcp.tools import create_mcp_server
from kb_server.services.signal_service import SignalService
from kb_server.services.indicator_service import IndicatorService


class TestMCPTools:
    def setup_method(self):
        self.signal_svc = SignalService()
        self.indicator_svc = IndicatorService()
        self.mcp = create_mcp_server(
            search_engine=None,
            cross_ref=None,
            signal_service=self.signal_svc,
            indicator_service=self.indicator_svc,
        )

    def _list_tools(self):
        """Helper to list tools (handles async)."""
        return asyncio.get_event_loop().run_until_complete(self.mcp.list_tools())

    def _tool_names(self):
        """Get set of tool names."""
        tools = self._list_tools()
        return {t.name for t in tools}

    def test_mcp_has_tools(self):
        tools = self._list_tools()
        # 9 KB + 4 signal/indicator + 2 compute + 1 status = 16
        assert len(tools) >= 14

    def test_kb_search_tool_exists(self):
        assert "kb_search" in self._tool_names()

    def test_kb_list_documents_tool_exists(self):
        assert "kb_list_documents" in self._tool_names()

    def test_kb_get_document_tool_exists(self):
        assert "kb_get_document" in self._tool_names()

    def test_kb_get_document_sections_tool_exists(self):
        assert "kb_get_document_sections" in self._tool_names()

    def test_kb_glossary_lookup_tool_exists(self):
        assert "kb_glossary_lookup" in self._tool_names()

    def test_kb_list_glossary_tool_exists(self):
        assert "kb_list_glossary" in self._tool_names()

    def test_kb_list_tags_tool_exists(self):
        assert "kb_list_tags" in self._tool_names()

    def test_kb_get_documents_by_tag_tool_exists(self):
        assert "kb_get_documents_by_tag" in self._tool_names()

    def test_kb_get_backlinks_tool_exists(self):
        assert "kb_get_backlinks" in self._tool_names()

    def test_kb_list_signals_tool_exists(self):
        assert "kb_list_signals" in self._tool_names()

    def test_kb_get_signal_tool_exists(self):
        assert "kb_get_signal" in self._tool_names()

    def test_kb_list_indicators_tool_exists(self):
        assert "kb_list_indicators" in self._tool_names()

    def test_kb_get_indicator_tool_exists(self):
        assert "kb_get_indicator" in self._tool_names()

    def test_evaluate_signal_tool_exists(self):
        assert "evaluate_signal" in self._tool_names()

    def test_compute_indicator_tool_exists(self):
        assert "compute_indicator" in self._tool_names()

    def test_kb_status_tool_exists(self):
        assert "kb_status" in self._tool_names()

    def test_total_tool_count(self):
        tools = self._list_tools()
        assert len(tools) == 16
