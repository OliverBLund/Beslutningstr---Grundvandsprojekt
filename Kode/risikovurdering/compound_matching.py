"""Keyword-based compound categorisation helpers used in Step 5."""

from __future__ import annotations

from functools import lru_cache
import unicodedata
from typing import Dict, Iterable, Tuple

from . import refined_compound_analysis as rca

DEFAULT_DISTANCE = 500.0

CATEGORY_DEFAULT_DISTANCES: Dict[str, float] = {
    category: float(info['distance_m'])
    for category, info in rca.LITERATURE_COMPOUND_MAPPING.items()
}

# Manual hint for specific compounds that do not appear directly in the keyword list
SPECIFIC_CATEGORY_HINTS: Dict[str, str] = {
    'cod': 'LOSSEPLADS',  # Chemical Oxygen Demand measurements typically originate from landfill leachate
}

def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ''
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return ascii_text.lower()

_KEYWORD_INDEX: Tuple[Tuple[str, str, float], ...] = tuple(
    (normalized_keyword, category, float(info['distance_m']))
    for category, info in rca.LITERATURE_COMPOUND_MAPPING.items()
    for keyword in info['keywords']
    for normalized_keyword in (_normalize(keyword),)
    if normalized_keyword
)

_SPECIFIC_DISTANCE_INDEX: Tuple[Tuple[str, float], ...] = tuple(
    (_normalize(keyword), float(distance))
    for keyword, distance in rca.COMPOUND_SPECIFIC_DISTANCES.items()
)

def list_categories() -> Iterable[str]:
    """Return the available category names."""
    return rca.LITERATURE_COMPOUND_MAPPING.keys()

def get_default_distance(category: str) -> float:
    """Return the default distance (in metres) for a category."""
    return CATEGORY_DEFAULT_DISTANCES.get(category, DEFAULT_DISTANCE)

@lru_cache(maxsize=None)
def categorize_substance(substance_text: str) -> Tuple[str, float]:
    """Return (category, distance_m) for a given substance description."""
    normalized = _normalize(substance_text)
    if not normalized:
        return 'ANDRE', DEFAULT_DISTANCE

    matches = [
        (len(keyword), category, distance)
        for keyword, category, distance in _KEYWORD_INDEX
        if keyword and keyword in normalized
    ]

    if matches:
        matches.sort(reverse=True)
        _, category, distance = matches[0]
    else:
        category, distance = 'ANDRE', DEFAULT_DISTANCE

    for specific_keyword, override_distance in _SPECIFIC_DISTANCE_INDEX:
        if specific_keyword and specific_keyword in normalized:
            category = SPECIFIC_CATEGORY_HINTS.get(specific_keyword, category)
            distance = override_distance
            break

    return category, float(distance)

__all__ = [
    'DEFAULT_DISTANCE',
    'CATEGORY_DEFAULT_DISTANCES',
    'categorize_substance',
    'get_default_distance',
    'list_categories',
]
