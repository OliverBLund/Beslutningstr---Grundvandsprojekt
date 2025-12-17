"""
Compound categorization for contamination risk assessment.

Categorizes contamination substances into 11 literature-based categories plus
an "ANDRE" (other) catch-all category. Each category has an associated distance
threshold (in meters) representing how far the contamination can travel in groundwater.

Usage:
    from risikovurdering.compound_categories import categorize_substance

    category, distance_m = categorize_substance("benzen")
    # Returns: ("BTXER", 200)  # Uses specific override

    category, distance_m = categorize_substance("unknown stuff")
    # Returns: ("ANDRE", 500)  # Falls back to default
"""

from __future__ import annotations

from functools import lru_cache
import unicodedata
from typing import Dict

# -------------------------------------------------------------------
# Default distances
# -------------------------------------------------------------------
DEFAULT_DISTANCE = 500.0  # Default for ANDRE category

# -------------------------------------------------------------------
# Compound-specific distance overrides
# -------------------------------------------------------------------
# These override the general category distances for specific compounds
COMPOUND_SPECIFIC_DISTANCES = {
    'benzen': 200,   # Override BTXER category (50m) with specific distance
    'cod': 500,      # Chemical Oxygen Demand (landfill leachate indicator)
    'cyanid': 100,   # Cyanide compounds
}

# -------------------------------------------------------------------
# Literature-based compound categories
# -------------------------------------------------------------------
# Each category has:
# - distance_m: How far the compound can travel in groundwater (meters)
# - keywords: Words that identify this category (case-insensitive)
# - description: What this category contains

COMPOUND_CATEGORIES = {
    # 1. BTX compounds + Oil products - 50m
    'BTXER': {
        'distance_m': 50,
        'keywords': [
            'btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', 'xylene',
            'benzin', 'olie-benzen', 'aromater', 'aromat', 'c5-c10', 'c10-c25',
            'kulbrintefraktion', 'monocyk', 'bicyk', 'tex (sum)', 'styren',
            'olieprodukter', 'olie', 'fyringsolie', 'dieselolie', 'petroleum',
            'diesel', 'fyring', 'fedt', 'smøreolie', 'c25-c35', 'terpentin',
            'white spirit'
        ],
        'description': 'BTX compounds and oil products (diesel, heating oil, petroleum)',
    },

    # 2. Chlorinated hydrocarbons - 500m (D3: "Klorerede kulbrinter")
    # Merged from KLOREREDE_OPLØSNINGSMIDLER + KLOREDE_KULBRINTER
    'KLOREDE_KULBRINTER': {
        'distance_m': 500,
        'keywords': [
            # Original KLOREDE_KULBRINTER keywords
            'chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform',
            'dibromethane', 'bromerede',
            # Merged from KLOREREDE_OPLØSNINGSMIDLER
            '1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor',
            'tetrachlor', 'vinylchlorid', 'dichlorethylen', 'dichlorethan',
            'chlorerede', 'opl.midl', 'opløsningsmidl', 'cis-1,2-dichlorethyl',
            'trans-1,2-dichloreth', 'chlorethan', 'dichlormethan', 'pcb',
            'polychloreret', 'polykloreret'
        ],
        'description': 'Chlorinated hydrocarbons and solvents (D3: Klorerede kulbrinter)',
    },

    # 3. Polar compounds - 300m
    'POLARE_FORBINDELSER': {
        'distance_m': 300,
        'keywords': [
            'mtbe', 'methyl tert-butyl ether', 'acetone', 'keton',
            'methanol', 'ethanol', 'alkohol', 'phthalat', 'dehp',
            'diethylphthalat', 'formaldehyd'
        ],
        'description': 'Polar compounds (MTBE, alcohols, phthalates)',
    },

    # 4. Phenolic compounds - 100m
    'PHENOLER': {
        'distance_m': 100,
        'keywords': ['phenol', 'fenol', 'klorofenol'],
        'description': 'Phenolic compounds',
    },

    # 5. Other aromatic compounds - 150m (D3: "Andre aromatiske forbindelser")
    'ANDRE_AROMATISKE_FORBINDELSER': {
        'distance_m': 150,
        'keywords': [
            'chlorbenzen', 'chlorobenzene', 'monochlorbenzen', 'dichlorbenzen',
            'trichlorbenzen', 'tetrachlorbenzen', 'pentachlorbenzen', 'hexachlorbenzen'
        ],
        'description': 'Other aromatic compounds (D3: Andre aromatiske forbindelser)',
    },

    # 6. Chlorinated phenols - 200m
    'KLOREREDE_PHENOLER': {
        'distance_m': 200,
        'keywords': ['dichlorophenol', 'chlorphenol', 'diklorofenol', 'klorofenol'],
        'description': 'Chlorinated phenolic compounds',
    },

    # 7. PAH compounds - 30m
    'PAH_FORBINDELSER': {
        'distance_m': 30,
        'keywords': [
            'pah', 'fluoranthen', 'benzo', 'naftalen', 'naphtalen', 'naphthalen',
            'naphthacen', 'pyren', 'anthracen', 'antracen', 'tjære', 'tar',
            'phenanthren', 'fluoren', 'acenaphthen', 'acenaphthylen', 'chrysen',
            'chrysene', 'benzfluranthen', 'methylnaphthalen', 'benz(ghi)perylen'
        ],
        'description': 'Polycyclic Aromatic Hydrocarbons (low mobility, high sorption)',
    },

    # 8. Pesticides - 500m
    'PESTICIDER': {
        'distance_m': 500,
        'keywords': [
            'pesticid', 'herbicid', 'fungicid', 'mechlorprop', 'mcpp', 'atrazin',
            'glyphosat', 'mcpa', 'dichlorprop', '2,4-d', 'diuron', 'simazin',
            'fluazifop', 'ampa', 'ddt', 'triazol', 'dichlorbenzamid',
            'desphenyl chloridazon', 'chloridazon', 'dde', 'ddd', 'bentazon',
            'dithiocarbamat', 'dithiocarbamater', '4-cpp', '2-(2,6-dichlorphenoxy)',
            'hexazinon', 'isoproturon', 'lenacil', 'malathion', 'parathion',
            'terbuthylazin', 'metribuzin', 'deltamethrin', 'cypermethrin',
            'dieldrin', 'aldrin', 'clopyralid', 'tebuconazol', 'propiconazol',
            'dichlobenil', 'triadimenol', 'dimethachlor', 'pirimicarb', 'dimethoat',
            'phenoxysyrer', 'tfmp', 'propachlor', 'gamma lindan', 'thiamethoxam',
            'clothianidin', 'metazachlor', 'diflufenican', 'monuron', 'metamitron',
            'propyzamid', 'azoxystrobin', 'alachlor', 'chlorothalonil', 'asulam',
            'metsulfuron', 'boscalid', 'glufosinat', 'carbofuran', 'picloram',
            'sulfosulfuron', 'epoxiconazol', 'clomazon', 'prothioconazol',
            'aminopyralid', 'metalaxyl', 'dichlorvos', 'dicamba', 'triadimefon',
            'haloxyfop', 'quintozen', 'endosulfan', 'dichlorfluanid', 'florasulam',
            'aldicarb', 'imidacloprid', 'pendimethalin', 'dinoseb', 'dinoterb',
            'amitrol', 'ethofumesat', 'benazolin', 'deet', 'N,N-Dimethylsulfamid (DMS)',
            'dms'
        ],
        'description': 'Pesticides, herbicides, and fungicides (high mobility)',
    },

    # 9. PFAS compounds - 500m
    'PFAS': {
        'distance_m': 500,
        'keywords': [
            'perfluor', 'pfos', 'pfoa', 'pfas', 'perfluoroctansulfonsyre',
            'perfluoroctansyre', 'perfluorhexansulfonsyre', 'pfhxs',
            'perfluorheptansyre', 'pfhpa', 'perfluorpentansyre', 'pfpea',
            'perfluorhexansyre', 'pfhxa', 'perfluorbutansyre', 'pfba',
            'perfluoroctansulfonamid', 'pfosa', 'perfluorbutansulfonsyre', 'pfbs',
            '1h,1h,2h,2h-perfluoroctansulfonsyre', 'perfluornonansyre', 'pfna',
            'perfluorpentansulfonsyre', 'pfpes', 'perfluorheptansulfonsyre', 'pfhps'
        ],
        'description': 'PFAS "forever chemicals" (very high mobility and persistence)',
    },

    # 10. Inorganic compounds - 150m
    'UORGANISKE_FORBINDELSER': {
        'distance_m': 150,
        'keywords': [
            'arsen', 'arsenic', 'cyanid', 'cyanide', 'tungmetal', 'bly', 'cadmium',
            'krom', 'chrom', 'nikkel', 'zink', 'kobber', 'kviksølv', 'jern',
            'mangan', 'aluminium', 'sølv', 'barium', 'kobolt', 'metaller',
            'tributyltin', 'tbt', 'tin', 'molybden', 'antimon', 'calcium',
            'natrium', 'kalium', 'magnesium', 'thallium', 'bor', 'chlorid',
            'sulfat', 'nitrat', 'fluorid', 'fluor', 'ammoniak', 'ammonium',
            'phosphor', 'tributhyltinacetat', 'tributhyltinnaphth', 'nitrit'
        ],
        'description': 'Inorganic compounds (heavy metals, salts)',
    },

    # 11. Landfill leachate compounds - 100m
    'LOSSEPLADS': {
        'distance_m': 100,
        'keywords': [
            'lossepladsperkolat', 'perkolat', 'lossepladsgas', 'methan',
            'deponigas', 'biogas'
        ],
        'description': 'Landfill leachate and landfill gas (perkolat, methan)',
    },
}

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize text for matching: remove accents, lowercase."""
    if not isinstance(text, str):
        return ''
    # Remove accents/diacritics
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return ascii_text.lower()


def get_category_distance(category: str) -> float:
    """Get the default distance for a category."""
    if category in COMPOUND_CATEGORIES:
        return float(COMPOUND_CATEGORIES[category]['distance_m'])
    return DEFAULT_DISTANCE


def list_categories() -> list[str]:
    """Return list of all category names."""
    return list(COMPOUND_CATEGORIES.keys())


@lru_cache(maxsize=2048)
def categorize_substance(substance_text: str) -> tuple[str, float]:
    """
    Categorize a contamination substance and return its travel distance.

    Algorithm:
    1. Check for compound-specific overrides (e.g., 'benzen' → 200m)
    2. Check for category keywords (e.g., 'toluene' → BTXER → 50m)
    3. Fall back to ANDRE category with default distance

    Args:
        substance_text: The substance description (e.g., "benzen", "toluene", "unknown")

    Returns:
        Tuple of (category_name, distance_meters)

    Examples:
        >>> categorize_substance("benzen")
        ('BTXER', 200.0)  # Specific override

        >>> categorize_substance("toluene")
        ('BTXER', 50.0)  # Category default

        >>> categorize_substance("unknown stuff")
        ('ANDRE', 500.0)  # Fallback
    """
    normalized = _normalize(substance_text)
    if not normalized:
        return 'ANDRE', DEFAULT_DISTANCE

    # Step 1: Check compound-specific overrides
    for compound, specific_distance in COMPOUND_SPECIFIC_DISTANCES.items():
        if compound == 'benzen':
            # Special case: Only match pure "benzen", not compounds like "trichlorbenzen"
            if (normalized == 'benzen' or
                normalized.startswith('benzen ') or
                normalized.startswith('benzen-') or
                normalized.startswith('benzen,') or
                normalized.startswith('benzen;')):
                # Find which category it belongs to
                for category, info in COMPOUND_CATEGORIES.items():
                    if any(_normalize(kw) in normalized for kw in info['keywords']):
                        return category, float(specific_distance)
        else:
            # For other compounds, simple substring matching
            if compound in normalized:
                for category, info in COMPOUND_CATEGORIES.items():
                    if any(_normalize(kw) in normalized for kw in info['keywords']):
                        return category, float(specific_distance)

    # Step 2: Check general category keywords (longest keyword match wins)
    matches = []
    for category, info in COMPOUND_CATEGORIES.items():
        for keyword in info['keywords']:
            # Normalize keyword to match normalized input (handles Danish æøå)
            normalized_keyword = _normalize(keyword)
            if normalized_keyword and normalized_keyword in normalized:
                matches.append((len(normalized_keyword), category, info['distance_m']))

    if matches:
        # Sort by keyword length (longest match = most specific)
        matches.sort(reverse=True)
        _, category, distance = matches[0]
        return category, float(distance)

    # Step 3: Fallback to ANDRE category
    return 'ANDRE', DEFAULT_DISTANCE
