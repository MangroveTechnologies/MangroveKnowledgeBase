import json
import pytest
from mangrove_kb.documents import DocumentStore, DocumentNotFoundError


@pytest.fixture(scope="module")
def store():
    return DocumentStore()


def test_every_overview_has_all_headings_without_body(store):
    for summary in store.list_documents()["documents"]:
        slug = summary["slug"]
        overview = store.get_document_page(slug, view="overview")
        original = store.get_document(slug)
        assert overview["summary"] == original["summary"]
        assert [s["anchor"] for s in overview["sections"]] == [
            s["anchor"] for s in original["sections"]
        ]
        assert overview["content"] == ""
        assert overview["next_offset"] is None and not overview["has_more"]
        assert all("content" not in section for section in overview["sections"])
        assert len(json.dumps(overview).encode()) <= 24000


def test_parent_section_includes_children_but_not_next_sibling(store):
    slug = "5-risk-management"
    overview = store.get_document_page(slug, view="overview")
    sections = overview["sections"]
    index = next(
        i for i, s in enumerate(sections) if s["anchor"] == "5-3-drawdown-controls"
    )
    stop = index + 1
    while stop < len(sections) and sections[stop]["level"] > sections[index]["level"]:
        stop += 1
    expected = store.get_document(slug)["content"][
        sections[index]["start_char"] : sections[stop - 1]["end_char"]
    ]
    chunks = []
    offset = 0
    while True:
        page = store.get_document_page(
            slug,
            view="section",
            section_anchor="5-3-drawdown-controls",
            offset=offset,
            max_chars=500,
        )
        assert page["content_length"] == len(expected)
        assert all(
            s["anchor"] in {x["anchor"] for x in sections[index:stop]}
            for s in page["sections"]
        )
        chunks.append(page["content"])
        if page["next_offset"] is None:
            break
        assert page["next_offset"] > offset
        offset = page["next_offset"]
    assert "".join(chunks) == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"view": "invalid"},
        {"view": "section"},
        {"view": "content", "section_anchor": "x"},
        {"view": "overview", "offset": 1},
        {"view": "overview", "max_chars": 1},
        {"view": "section", "section_anchor": "x", "full": True},
    ],
)
def test_conflicting_views_rejected(store, kwargs):
    with pytest.raises(ValueError):
        store.get_document_page("5-risk-management", **kwargs)


def test_missing_anchor_is_not_a_full_document_fallback(store):
    with pytest.raises(DocumentNotFoundError):
        store.get_document_page(
            "5-risk-management", view="section", section_anchor="unknown"
        )


def test_overview_response_is_isolated(store):
    first = store.get_document_page("5-risk-management", view="overview")
    first["sections"][0]["title"] = "changed"
    assert (
        store.get_document_page("5-risk-management", view="overview")["sections"][0][
            "title"
        ]
        != "changed"
    )


def test_rsi_section_contains_real_definition_formula_and_interpretation(store):
    result = store.get_document_page(
        '6-indicators', view='section',
        section_anchor='6-2-1-relative-strength-index-rsi',
    )
    assert '#### Definition' in result['content']
    assert 'RSI = 100 - (100 / (1 + RS))' in result['content']
    assert '#### Interpretation' in result['content']
    assert '### 6.2.2' not in result['content']
    assert result['returned_chars'] > 500


def test_every_section_matches_raw_markdown_subtree(store):
    from mangrove_kb.documents import _headings
    for entry in store.list_documents()['documents']:
        slug = entry['slug']
        source = store.get_document(slug)['content']
        headings = list(_headings(source))
        for section in store.get_document_page(slug, view='overview')['sections']:
            index = next(i for i, h in enumerate(headings) if h[3] == section['start_char'])
            heading = headings[index]
            end = next((h[2] for h in headings[index + 1:] if h[0] <= heading[0]), len(source))
            expected = source[heading[3]:end]
            chunks, offset = [], 0
            while True:
                page = store.get_document_page(slug, view='section', section_anchor=section['anchor'], offset=offset)
                assert page['content_length'] == len(expected)
                chunks.append(page['content'])
                if page['next_offset'] is None:
                    break
                assert page['next_offset'] > offset
                offset = page['next_offset']
            assert ''.join(chunks) == expected, (slug, section['anchor'])


def test_nested_unindexed_headings_and_fenced_headings_do_not_drop_content():
    from mangrove_kb.documents import _parse
    source = '# Guide\n\nSummary.\n\n## Topic\n\n### Indicator\n\n#### Definition\nBody\n##### Detail\nMore\n```\n## not a heading\n```\n\n### Next\nOther\n'
    parsed = _parse('01-guide.md', source)
    section = next(s for s in parsed['sections'] if s['title'] == 'Indicator')
    assert 'Body' in section['content'] and 'More' in section['content']
    assert '## not a heading' in section['content']
    assert '### Next' not in section['content']
