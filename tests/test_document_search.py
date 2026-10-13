import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from mangrove_kb.document_search import DocumentSearch
from mangrove_kb.document_synonyms import SynonymRegistry


@pytest.fixture(scope="module")
def search():
    return DocumentSearch()


@pytest.mark.parametrize(
    "query",
    [
        "stop loss placement",
        "stop loss placement and diversification correlation limits",
        "take-profit",
        "risk-reward",
        "p&l",
        "r:r",
        "RSI",
        "drawdown control and recovery",
        "risk management position sizing loss limits",
        '"unclosed quote',
        "risk) OR (ruin",
        "title:RSI",
        "*",
        "!!!",
        "",
    ],
)
@pytest.mark.parametrize("expand", [True, False])
def test_natural_queries_are_safe(search, query, expand):
    result = search.query(query, expand=expand)
    assert len(result["results"]) <= 5


def test_observed_stop_loss_failure_returns_real_matches(search):
    result = search.query("stop loss placement", expand=True)
    assert result["total_results"] > 0
    assert any(row["document_slug"] == "5-risk-management" for row in result["results"])


def test_every_synonym_is_valid_fts(search):
    for term, synonyms in SynonymRegistry.TRADING_SYNONYMS.items():
        for phrase in (term, *synonyms):
            search.query(phrase, limit=1)


def test_results_are_compact_and_truncation_is_explicit(search):
    result = search.query("risk", tags=["risk"], expand=False, limit=25)
    assert result["total_results"] > 0
    assert len(json.dumps(result).encode()) < 25_000
    assert any(row["tags_truncated"] for row in result["results"])
    assert all(len(row["tags"]) <= 16 for row in result["results"])
    assert all("risk" in row["tags"] for row in result["results"])
    assert len(result["tags_matched"]) <= 64


def test_limits_tags_only_and_result_isolation(search):
    assert search.query("risk", limit=0)["results"] == []
    result = search.query("*", tags=["risk"], limit=2)
    assert 0 < len(result["results"]) <= 2
    result["results"][0]["tags"].append("mutated")
    assert (
        "mutated" not in search.query("*", tags=["risk"], limit=2)["results"][0]["tags"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": -1},
        {"limit": True},
        {"limit": 101},
        {"expand": "true"},
        {"tags": [""]},
        {"tags": "risk"},
    ],
)
def test_invalid_options_fail_clearly(search, arguments):
    with pytest.raises(ValueError):
        search.query("risk", **arguments)


def test_concurrent_reads_are_consistent(search):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: search.query("stop loss placement"), range(8))
        )
    assert all(result == results[0] for result in results)


@pytest.mark.parametrize("query,tags", [("risk", None), ("*", ["risk"]), ("RSI", None)])
def test_response_budget_for_large_limits(search, query, tags):
    result = search.query(query, tags=tags, limit=100)
    assert len(json.dumps(result).encode()) <= 24_010
    assert result["returned"] == len(result["results"])
    assert result["truncated"] == (result["returned"] < result["total_results"])


def test_rsi_formula_search_returns_readable_section(search):
    from mangrove_kb.documents import DocumentStore
    results = search.query('RSI formula', limit=10)['results']
    section = next(r for r in results if r['document_slug'] == '6-indicators'
                   and r['section_anchor'] == '6-2-1-relative-strength-index-rsi')
    page = DocumentStore().get_document_page(section['document_slug'], view='section',
                                            section_anchor=section['section_anchor'])
    assert 'RSI = 100 - (100 / (1 + RS))' in page['content']
