"""
Synonym Registry for trading terminology.

Provides bidirectional synonym mappings for query expansion.
"""

from typing import Dict, List, Set, Optional
import re


class SynonymRegistry:
    """
    Registry of trading terminology synonyms for search query expansion.

    Supports bidirectional lookups and abbreviation expansion.
    """

    # Core synonym mappings: primary term -> list of synonyms
    TRADING_SYNONYMS: Dict[str, List[str]] = {
        # Profit/Loss
        "pnl": ["profit and loss", "p&l", "profit loss"],
        "profit and loss": ["pnl", "p&l"],

        # Risk-Reward
        "rr": ["risk reward", "risk-reward", "risk reward ratio", "r:r"],
        "risk reward": ["rr", "risk-reward", "r:r"],
        "risk-reward": ["rr", "risk reward", "r:r"],

        # Moving Averages
        "ma": ["moving average"],
        "moving average": ["ma"],
        "sma": ["simple moving average"],
        "simple moving average": ["sma"],
        "ema": ["exponential moving average"],
        "exponential moving average": ["ema"],
        "dema": ["double exponential moving average"],
        "tema": ["triple exponential moving average"],

        # Stop Loss / Take Profit
        "sl": ["stop loss", "stop-loss", "stoploss"],
        "stop loss": ["sl", "stop-loss", "stoploss"],
        "stop-loss": ["sl", "stop loss", "stoploss"],
        "tp": ["take profit", "take-profit", "takeprofit"],
        "take profit": ["tp", "take-profit", "takeprofit"],
        "take-profit": ["tp", "take profit", "takeprofit"],

        # Indicators
        "atr": ["average true range"],
        "average true range": ["atr"],
        "rsi": ["relative strength index"],
        "relative strength index": ["rsi"],
        "macd": ["moving average convergence divergence"],
        "moving average convergence divergence": ["macd"],
        "adx": ["average directional index"],
        "average directional index": ["adx"],
        "obv": ["on balance volume", "on-balance volume"],
        "on balance volume": ["obv"],
        "vwap": ["volume weighted average price"],
        "volume weighted average price": ["vwap"],
        "cci": ["commodity channel index"],
        "commodity channel index": ["cci"],
        "mfi": ["money flow index"],
        "money flow index": ["mfi"],

        # Market Structure
        "hh": ["higher high"],
        "higher high": ["hh"],
        "hl": ["higher low"],
        "higher low": ["hl"],
        "ll": ["lower low"],
        "lower low": ["ll"],
        "lh": ["lower high"],
        "lower high": ["lh"],
        "bos": ["break of structure", "structure break"],
        "break of structure": ["bos", "structure break"],
        "choch": ["change of character"],
        "change of character": ["choch"],

        # Volume Profile
        "poc": ["point of control"],
        "point of control": ["poc"],
        "va": ["value area"],
        "value area": ["va"],
        "vah": ["value area high"],
        "value area high": ["vah"],
        "val": ["value area low"],
        "value area low": ["val"],

        # Session Terms
        "rth": ["regular trading hours"],
        "regular trading hours": ["rth"],
        "onh": ["overnight high"],
        "overnight high": ["onh"],
        "onl": ["overnight low"],
        "overnight low": ["onl"],

        # Order Types
        "oco": ["one cancels other", "one-cancels-other"],
        "one cancels other": ["oco"],
        "gtc": ["good till cancelled", "good til canceled"],
        "good till cancelled": ["gtc"],

        # Trading Concepts
        "fvg": ["fair value gap"],
        "fair value gap": ["fvg"],
        "snr": ["support and resistance", "s&r", "sr"],
        "support and resistance": ["snr", "s&r", "sr"],
        "sr": ["support resistance", "support and resistance", "snr"],
        "mtf": ["multi timeframe", "multi-timeframe", "multiple timeframe"],
        "multi timeframe": ["mtf", "multi-timeframe"],

        # Position Sizing
        "kelly": ["kelly criterion", "kelly formula"],
        "kelly criterion": ["kelly", "kelly formula"],
        "var": ["value at risk"],
        "value at risk": ["var"],

        # Patterns
        "h&s": ["head and shoulders", "head shoulders"],
        "head and shoulders": ["h&s", "head shoulders"],

        # General Trading
        "dca": ["dollar cost averaging", "dollar-cost averaging"],
        "dollar cost averaging": ["dca"],
        "roi": ["return on investment"],
        "return on investment": ["roi"],
        "ytd": ["year to date"],
        "year to date": ["ytd"],
        "mtd": ["month to date"],
        "month to date": ["mtd"],
    }

    def __init__(self):
        """Initialize the synonym registry."""
        self._synonyms = dict(self.TRADING_SYNONYMS)
        self._reverse_index: Dict[str, Set[str]] = {}
        self._build_reverse_index()

    def _build_reverse_index(self):
        """Build reverse index for fast synonym lookups."""
        self._reverse_index.clear()

        for term, synonyms in self._synonyms.items():
            term_lower = term.lower()
            if term_lower not in self._reverse_index:
                self._reverse_index[term_lower] = set()

            # Add all synonyms to the reverse index
            for syn in synonyms:
                syn_lower = syn.lower()
                self._reverse_index[term_lower].add(syn_lower)

                if syn_lower not in self._reverse_index:
                    self._reverse_index[syn_lower] = set()
                self._reverse_index[syn_lower].add(term_lower)

    def get_synonyms(self, term: str) -> List[str]:
        """
        Get all synonyms for a term.

        Args:
            term: The term to look up

        Returns:
            List of synonyms (empty if none found)
        """
        term_lower = term.lower()

        # Direct lookup
        if term_lower in self._synonyms:
            return list(self._synonyms[term_lower])

        # Reverse index lookup
        if term_lower in self._reverse_index:
            return list(self._reverse_index[term_lower])

        return []

    def get_all_variants(self, term: str) -> Set[str]:
        """
        Get all variants of a term including the term itself.

        Args:
            term: The term to expand

        Returns:
            Set of all variants including the original term
        """
        variants = {term.lower()}
        variants.update(syn.lower() for syn in self.get_synonyms(term))
        return variants

    def expand_query(self, query: str) -> str:
        """
        Expand a search query with synonym variants.

        Args:
            query: Original search query

        Returns:
            Expanded query with OR clauses for synonyms
        """
        words = query.split()
        expanded_parts = []
        i = 0

        while i < len(words):
            # Try multi-word phrases (up to 4 words)
            matched = False
            for phrase_len in range(min(4, len(words) - i), 0, -1):
                phrase = ' '.join(words[i:i + phrase_len])
                phrase_lower = phrase.lower()

                synonyms = self.get_synonyms(phrase_lower)
                if synonyms:
                    # Build OR group
                    all_variants = [phrase] + synonyms
                    or_group = ' OR '.join(f'"{v}"' if ' ' in v else v for v in all_variants)
                    expanded_parts.append(f"({or_group})")
                    i += phrase_len
                    matched = True
                    break

            if not matched:
                # Check single word
                word = words[i]
                synonyms = self.get_synonyms(word.lower())
                if synonyms:
                    all_variants = [word] + synonyms
                    or_group = ' OR '.join(f'"{v}"' if ' ' in v else v for v in all_variants)
                    expanded_parts.append(f"({or_group})")
                else:
                    expanded_parts.append(word)
                i += 1

        return ' '.join(expanded_parts)

    def add_synonym(self, term: str, synonyms: List[str]):
        """
        Add a new synonym mapping.

        Args:
            term: Primary term
            synonyms: List of synonyms
        """
        term_lower = term.lower()
        if term_lower not in self._synonyms:
            self._synonyms[term_lower] = []

        for syn in synonyms:
            syn_lower = syn.lower()
            if syn_lower not in self._synonyms[term_lower]:
                self._synonyms[term_lower].append(syn_lower)

        self._build_reverse_index()

    def get_all_terms(self) -> List[str]:
        """Get all registered terms and their synonyms."""
        all_terms = set()
        for term, synonyms in self._synonyms.items():
            all_terms.add(term)
            all_terms.update(synonyms)
        return sorted(all_terms)

    def to_dict(self) -> Dict[str, List[str]]:
        """Export synonyms as dictionary for database storage."""
        return dict(self._synonyms)

    @classmethod
    def from_dict(cls, data: Dict[str, List[str]]) -> "SynonymRegistry":
        """Create registry from dictionary."""
        registry = cls()
        registry._synonyms = data
        registry._build_reverse_index()
        return registry


# Global singleton instance
_registry: Optional[SynonymRegistry] = None


def get_synonym_registry() -> SynonymRegistry:
    """Get the global synonym registry instance."""
    global _registry
    if _registry is None:
        _registry = SynonymRegistry()
    return _registry
