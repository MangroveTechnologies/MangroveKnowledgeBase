import pytest
from mangrove_kb.document_glossary import get_glossary_entry, glossary_entries
from mangrove_kb.documents import DocumentNotFoundError


@pytest.mark.parametrize('alias,term', [('RSI', 'Relative Strength Index'), ('ATR', 'Average True Range'), ('MACD', 'Moving Average Convergence Divergence'), ('SMA', 'Simple Moving Average'), ('ADX', 'Average Directional Index')])
def test_declared_abbreviation(alias, term):
    result = get_glossary_entry(alias.lower())
    assert result['term'] == term
    assert result['definition']
    assert get_glossary_entry(term) == result


def test_substring_is_not_an_alias():
    with pytest.raises(DocumentNotFoundError):
        get_glossary_entry('version')


def test_ambiguous_term_requires_clarification():
    with pytest.raises(ValueError, match='Ambiguous'):
        get_glossary_entry('moving average')


def test_results_do_not_mutate_the_cache():
    result = get_glossary_entry('RSI')
    result['related_terms'].append('changed')
    assert 'changed' not in get_glossary_entry('RSI')['related_terms']
    entries = glossary_entries()
    keys = [(e['term'], e['document_slug']) for e in entries]
    assert len(keys) == len(set(keys))
