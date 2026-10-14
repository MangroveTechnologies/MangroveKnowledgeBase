import json

import pytest

from mangrove_kb.documents import (
    DocumentNotFoundError,
    DocumentStore,
    DocumentUnavailableError,
)


TEXT = """# 1. Test guide

A short guide to RSI.

Tags: RSI, Momentum

## 1.1 Meaning
Relative strength.

```python
## Not a section
```

### Example
An example.
"""


@pytest.fixture
def artifact(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"schema_version": 1, "documents": ["01-test.md"]}))
    (tmp_path / "01-test.md").write_text(TEXT)
    return tmp_path, catalog


def test_expected_document_identity_and_sections(artifact):
    store = DocumentStore(*artifact)
    result = store.get_document("1-test")
    assert result["title"] == "Test guide"
    assert result["tags"] == ["momentum", "rsi"]
    assert result["content"] == TEXT
    assert result["truncated"] is False
    assert [s["anchor"] for s in result["sections"]] == ["1-1-meaning", "1-1-example"]
    assert result["sections"][1]["parent_anchor"] == "1-1-meaning"
    assert store.list_documents()["documents"] == [{
        "slug": "1-test", "title": "Test guide", "tags": ["momentum", "rsi"],
        "summary": "A short guide to RSI.", "section_count": 2,
    }]


def test_truncation_cannot_leak_full_content_through_sections(artifact):
    doc = DocumentStore(*artifact).get_document("1-test", 12)
    assert doc["content"] == TEXT[:12]
    assert doc["content_length"] == len(TEXT)
    assert doc["returned_chars"] == 12
    assert doc["truncated"] is True
    assert all(s["content"] == "" and s["truncated"] for s in doc["sections"])


@pytest.mark.parametrize("slug", ["../secret", "/etc/passwd", "1-test.md", "", None, "01/test", "a" * 129])
def test_invalid_slug(artifact, slug):
    with pytest.raises(ValueError):
        DocumentStore(*artifact).get_document(slug)


@pytest.mark.parametrize("limit", [True, -1, 1.5, "4", 1000001])
def test_invalid_bounds(artifact, limit):
    with pytest.raises(ValueError):
        DocumentStore(*artifact).get_document("1-test", limit)


def test_missing_is_distinct_from_broken_artifact(artifact):
    with pytest.raises(DocumentNotFoundError):
        DocumentStore(*artifact).get_document("absent")
    (artifact[0] / "01-test.md").unlink()
    with pytest.raises(DocumentUnavailableError, match="artifact is unavailable"):
        DocumentStore(*artifact)


def test_unlisted_private_files_are_not_exposed(artifact):
    (artifact[0] / "02-private.md").write_text("# Private\nSecret")
    store = DocumentStore(*artifact)
    assert store.list_documents()["total"] == 1
    with pytest.raises(DocumentNotFoundError):
        store.get_document("2-private")


def test_symlink_is_rejected(artifact, tmp_path):
    path = artifact[0] / "01-test.md"
    path.unlink()
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret")
    path.symlink_to(secret)
    with pytest.raises(DocumentUnavailableError):
        DocumentStore(*artifact)


def test_provenance_changes_with_content_and_results_are_isolated(artifact):
    store = DocumentStore(*artifact)
    original = store.get_document("1-test")
    altered = store.get_document("1-test")
    altered["sections"].clear()
    altered["tags"].append("private")
    assert store.get_document("1-test") == original
    path = artifact[0] / "01-test.md"
    path.write_text(TEXT + "Updated.\n")
    assert DocumentStore(*artifact).get_document("1-test")["source"] != original["source"]


def test_published_catalog_roundtrips():
    store = DocumentStore()
    result = store.list_documents()
    assert result["total"] == 11
    assert result["documents"][0]["slug"] == "0-table-of-contents"
    for doc in result["documents"]:
        assert store.get_document(doc["slug"])["title"] == doc["title"]
    assert "RSI" in store.get_document("6-indicators")["content"]


@pytest.mark.parametrize("manifest", [
    {}, [], None,
    {"schema_version": True, "documents": ["01-test.md"]},
    {"schema_version": 2, "documents": ["01-test.md"]},
    {"schema_version": 1, "documents": []},
    {"schema_version": 1, "documents": ["../01-test.md"]},
    {"schema_version": 1, "documents": ["01-test.md", "01-test.md"]},
    {"schema_version": 1, "documents": [None]},
])
def test_invalid_catalog_fails_closed(artifact, manifest):
    artifact[1].write_text(json.dumps(manifest))
    with pytest.raises(DocumentUnavailableError):
        DocumentStore(*artifact)


@pytest.mark.parametrize("raw", [b"\xff", b"No title", b"# Title\n" + b"a" * 2_000_000])
def test_corrupt_documents_fail_closed(artifact, raw):
    (artifact[0] / "01-test.md").write_bytes(raw)
    with pytest.raises(DocumentUnavailableError):
        DocumentStore(*artifact)


def test_zero_budget_and_complete_budget(artifact):
    store = DocumentStore(*artifact)
    assert store.get_document("1-test", 0)["content"] == ""
    assert store.get_document("1-test", len(TEXT))["truncated"] is False


def test_duplicate_headings_have_distinct_anchors(artifact):
    (artifact[0] / "01-test.md").write_text("# Test\n## Repeated\nOne\n## Repeated\nTwo\n")
    result = DocumentStore(*artifact).get_document("1-test")
    assert [s["anchor"] for s in result["sections"]] == ["repeated", "repeated-1"]


def test_source_checkout_never_claims_installed_package_version(artifact):
    source = DocumentStore(*artifact).list_documents()["source"]
    assert source["source_kind"] == "custom"
    assert source["package_version"] is None
