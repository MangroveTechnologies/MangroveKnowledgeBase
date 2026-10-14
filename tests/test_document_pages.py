import json
import pytest
from mangrove_kb.documents import DocumentStore


@pytest.fixture(scope="module")
def store():
    return DocumentStore()


def test_every_document_reconstructs_without_gaps_or_duplicate_text(store):
    for summary in store.list_documents()["documents"]:
        slug = summary["slug"]
        expected = store.get_document(slug)["content"]
        offset, chunks = 0, []
        while True:
            page = store.get_document_page(slug, offset=offset)
            assert page["offset"] == offset
            assert page["returned_chars"] == len(page["content"])
            assert all("content" not in section for section in page["sections"])
            assert len(json.dumps(page).encode()) <= 24000
            chunks.append(page["content"])
            if not page["has_more"]:
                assert page["next_offset"] is None
                break
            assert page["next_offset"] == offset + page["returned_chars"] > offset
            offset = page["next_offset"]
        assert "".join(chunks) == expected


def test_full_download_is_explicit_and_not_duplicated(store):
    page = store.get_document_page("10-signals-quick-reference", full=True)
    assert (
        page["content"] == store.get_document("10-signals-quick-reference")["content"]
    )
    assert page["next_offset"] is None
    assert page["truncated"] is False
    assert all("content" not in section for section in page["sections"])


def test_observed_requests_are_bounded(store):
    for budget in (None, 1, 18000, 1000000):
        page = store.get_document_page("10-signals-quick-reference", max_chars=budget)
        assert len(json.dumps(page).encode()) <= 24000
        assert page["returned_chars"] <= 12000
        assert page["has_more"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"offset": -1},
        {"offset": True},
        {"offset": 1.5},
        {"offset": 1000001},
        {"full": "true"},
        {"full": True, "offset": 1},
        {"full": True, "max_chars": 10},
    ],
)
def test_invalid_page_arguments(store, kwargs):
    with pytest.raises(ValueError):
        store.get_document_page("10-signals-quick-reference", **kwargs)


def test_end_and_metadata_only(store):
    slug = "10-signals-quick-reference"
    length = len(store.get_document(slug)["content"])
    end = store.get_document_page(slug, offset=length)
    assert end["content"] == "" and end["next_offset"] is None
    with pytest.raises(ValueError):
        store.get_document_page(slug, offset=length + 1)
    meta = store.get_document_page(slug, max_chars=0)
    assert meta["content"] == "" and meta["next_offset"] == 0
