"""Trading synonym rules retained from the retired document service."""

from __future__ import annotations

import re
from typing import Dict, List, Set


class SynonymRegistry:
    TRADING_SYNONYMS: Dict[str, List[str]] = {
        "pnl": ["profit and loss", "p&l", "profit loss"],
        "profit and loss": ["pnl", "p&l"],
        "rr": ["risk reward", "risk-reward", "risk reward ratio", "r:r"],
        "risk reward": ["rr", "risk-reward", "r:r"],
        "risk-reward": ["rr", "risk reward", "r:r"],
        "ma": ["moving average"],
        "moving average": ["ma"],
        "sma": ["simple moving average"],
        "simple moving average": ["sma"],
        "ema": ["exponential moving average"],
        "exponential moving average": ["ema"],
        "dema": ["double exponential moving average"],
        "tema": ["triple exponential moving average"],
        "sl": ["stop loss", "stop-loss", "stoploss"],
        "stop loss": ["sl", "stop-loss", "stoploss"],
        "stop-loss": ["sl", "stop loss", "stoploss"],
        "tp": ["take profit", "take-profit", "takeprofit"],
        "take profit": ["tp", "take-profit", "takeprofit"],
        "take-profit": ["tp", "take profit", "takeprofit"],
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
        "poc": ["point of control"],
        "point of control": ["poc"],
        "va": ["value area"],
        "value area": ["va"],
        "vah": ["value area high"],
        "value area high": ["vah"],
        "val": ["value area low"],
        "value area low": ["val"],
        "rth": ["regular trading hours"],
        "regular trading hours": ["rth"],
        "onh": ["overnight high"],
        "overnight high": ["onh"],
        "onl": ["overnight low"],
        "overnight low": ["onl"],
        "oco": ["one cancels other", "one-cancels-other"],
        "one cancels other": ["oco"],
        "gtc": ["good till cancelled", "good til canceled"],
        "good till cancelled": ["gtc"],
        "fvg": ["fair value gap"],
        "fair value gap": ["fvg"],
        "snr": ["support and resistance", "s&r", "sr"],
        "support and resistance": ["snr", "s&r", "sr"],
        "sr": ["support resistance", "support and resistance", "snr"],
        "mtf": ["multi timeframe", "multi-timeframe", "multiple timeframe"],
        "multi timeframe": ["mtf", "multi-timeframe"],
        "kelly": ["kelly criterion", "kelly formula"],
        "kelly criterion": ["kelly", "kelly formula"],
        "var": ["value at risk"],
        "value at risk": ["var"],
        "h&s": ["head and shoulders", "head shoulders"],
        "head and shoulders": ["h&s", "head shoulders"],
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
        self._synonyms = dict(self.TRADING_SYNONYMS)
        self._reverse_index: Dict[str, Set[str]] = {}
        self._build_reverse_index()

    def _build_reverse_index(self):
        self._reverse_index.clear()
        for term, synonyms in self._synonyms.items():
            term_lower = term.lower()
            if term_lower not in self._reverse_index:
                self._reverse_index[term_lower] = set()
            for syn in synonyms:
                syn_lower = syn.lower()
                self._reverse_index[term_lower].add(syn_lower)
                if syn_lower not in self._reverse_index:
                    self._reverse_index[syn_lower] = set()
                self._reverse_index[syn_lower].add(term_lower)

    def get_synonyms(self, term: str) -> List[str]:
        term_lower = term.lower()
        if term_lower in self._synonyms:
            return list(self._synonyms[term_lower])
        if term_lower in self._reverse_index:
            return sorted(self._reverse_index[term_lower])
        return []

    def expand_query(self, query: str, *, expand: bool = True) -> str:
        words = re.findall(r"\w+(?:[-:&'/]\w+)*", query, re.UNICODE)
        groups = []
        i = 0
        while i < len(words):
            variants = [words[i]]
            consumed = 1
            if expand:
                for length in range(min(4, len(words) - i), 0, -1):
                    phrase = " ".join(words[i : i + length])
                    synonyms = self.get_synonyms(phrase)
                    if synonyms:
                        variants = [phrase, *synonyms]
                        consumed = length
                        break
            literals = [
                '"' + value.replace('"', '""') + '"'
                for value in dict.fromkeys(variants)
            ]
            groups.append("(" + " OR ".join(literals) + ")")
            i += consumed
        return " AND ".join(groups)
