"""
Compound Categorization System for Step 5 Risk Assessment
=========================================================

Centralized compound categorization using keyword-based mapping to assign
contamination substances to risk categories with specific distance thresholds.

This module provides the authoritative COMPOUND_DISTANCE_MAPPING and categorization
functions used by all Step 5 analyses.

Created: August 2025
Author: Oliver Lund, DTU
"""

import pandas as pd

# Authoritative compound categorization system
# Based on scientific literature and regulatory guidelines for groundwater mobility
COMPOUND_DISTANCE_MAPPING = {
    # 1. BTX compounds - 50m (low mobility in groundwater)
    'BTXER': {
        'distance_m': 50,
        'keywords': ['btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', 'xylene', 'benzin', 'olie-benzen',
                    'aromater', 'aromat', 'c5-c10', 'c10-c25', 'kulbrintefraktion', 'monocyk', 'bicyk',
                    'tex (sum)', 'styren'],
        'description': 'BTX compounds including oil-benzene mixtures and aromatic hydrocarbons'
    },
    
    # 2. Chlorinated solvents - 500m (very high mobility)
    'CHLORINATED_SOLVENTS': {
        'distance_m': 500,
        'keywords': ['1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor', 'tetrachlor',
                    'vinylchlorid', 'dichlorethylen', 'dichlorethan', 'chlorerede', 'opl.midl', 'opløsningsmidl',
                    'cis-1,2-dichlorethyl', 'trans-1,2-dichloreth', 'chlorethan'],
        'description': 'Chlorinated solvents with very high groundwater mobility'
    },
    
    # 3. Polar compounds - 100m (moderate mobility)
    'POLARE': {
        'distance_m': 100,
        'keywords': ['mtbe', 'methyl tert-butyl ether', 'acetone', 'keton'],
        'description': 'Polar compounds like MTBE and acetone'
    },
    
    # 4. Phenolic compounds - 300m (moderate-high mobility)
    'PHENOLER': {
        'distance_m': 300,
        'keywords': ['phenol', 'fenol', 'cod', 'klorofenol'],
        'description': 'Phenolic compounds including COD'
    },
    
    # 5. Chlorinated hydrocarbons - 200m (moderate mobility)
    'KLOREDE_KULBRINTER': {
        'distance_m': 200,
        'keywords': ['chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform', 'dibromethane', 'bromerede'],
        'description': 'Chlorinated/brominated hydrocarbons'
    },
    
    # 6. Chlorinated phenols - 200m (moderate mobility)
    'CHLORPHENOLER': {
        'distance_m': 200,
        'keywords': ['dichlorophenol', 'chlorphenol', 'diklorofenol', 'klorofenol'],
        'description': 'Chlorinated phenolic compounds'
    },
    
    # 7. PAH compounds - 30m (very low mobility, high sorption)
    'PAHER': {
        'distance_m': 30,
        'keywords': ['pah', 'fluoranthen', 'benzo', 'naftalen', 'naphtalen', 'naphthalen', 'pyren', 'anthracen', 'antracen',
                    'tjære', 'tar', 'phenanthren', 'fluoren', 'acenaphthen', 'acenaphthylen', 'chrysen', 'chrysene',
                    'benzfluranthen', 'methylnaphthalen', 'benz(ghi)perylen'],
        'description': 'Polycyclic Aromatic Hydrocarbons - very low mobility due to high sorption'
    },
    
    # 8. Pesticides - 500m (high mobility, designed to be mobile)
    'PESTICIDER': {
        'distance_m': 500,
        'keywords': ['pesticid', 'herbicid', 'fungicid', 'mechlorprop', 'mcpp', 'atrazin', 'glyphosat',
                    'perfluor', 'pfos', 'pfoa', 'perfluoroctansulfonsyre', 'pfas', 'mcpa', 'dichlorprop',
                    '2,4-d', 'diuron', 'simazin', 'fluazifop', 'ampa', 'ddt', 'triazol', 'dichlorbenzamid',
                    'desphenyl chloridazon', 'chloridazon', 'dde', 'ddd', 'bentazon', 'dithiocarbamat',
                    'dithiocarbamater', '4-cpp', '2-(2,6-dichlorphenoxy)', 'hexazinon', 'isoproturon',
                    'lenacil', 'malathion', 'parathion', 'terbuthylazin', 'metribuzin', 'deltamethrin',
                    'cypermethrin', 'dieldrin', 'aldrin', 'clopyralid', 'tebuconazol', 'propiconazol',
                    'dichlobenil', 'triadimenol', 'dimethachlor', 'pirimicarb', 'dimethoat', 'phenoxysyrer',
                    'tfmp', 'propachlor', 'gamma lindan', 'thiamethoxam', 'clothianidin', 'metazachlor',
                    'diflufenican', 'monuron', 'metamitron', 'propyzamid', 'azoxystrobin', 'alachlor',
                    'chlorothalonil', 'asulam', 'metsulfuron', 'boscalid', 'glufosinat', 'carbofuran',
                    'picloram', 'sulfosulfuron', 'epoxiconazol', 'clomazon', 'prothioconazol', 'aminopyralid',
                    'metalaxyl', 'dichlorvos', 'dicamba', 'triadimefon', 'haloxyfop', 'quintozen', 'endosulfan',
                    'dichlorfluanid', 'florasulam', 'aldicarb', 'imidacloprid', 'pendimethalin', 'dinoseb',
                    'dinoterb', 'amitrol', 'ethofumesat', 'benazolin', 'deet'],
        'description': 'Pesticides, herbicides, fungicides and PFAS compounds - high mobility'
    },
    
    # 9. Inorganic compounds - 150m (variable mobility, conservative estimate)
    'UORGANISKE_FORBINDELSER': {
        'distance_m': 150,
        'keywords': ['arsen', 'arsenic', 'cyanid', 'cyanide', 'tungmetal', 'bly', 'cadmium', 'krom', 'chrom',
                    'nikkel', 'zink', 'kobber', 'kviksølv', 'jern', 'mangan', 'aluminium', 'sølv', 'barium',
                    'kobolt', 'metaller', 'tributyltin', 'tbt', 'tin', 'molybden', 'antimon', 'calcium',
                    'natrium', 'kalium', 'magnesium', 'thallium', 'bor', 'chlorid', 'sulfat', 'nitrat',
                    'fluorid', 'fluor', 'ammoniak', 'ammonium', 'phosphor', 'tributhyltinacetat',
                    'tributhyltinnaphth', 'nitrit'],
        'description': 'Inorganic compounds including heavy metals and salts'
    },
    
    # 10. Oil products - 200m (moderate mobility)
    'OLIEPRODUKTER': {
        'distance_m': 200,
        'keywords': ['olie', 'diesel', 'fyring', 'olieprodukter', 'fedt', 'petroleum', 'smøreolie',
                    'c25-c35', 'kulbrintefraktion', 'terpentin', 'white spirit', 'methyl-napthalen', 'naphthacen'],
        'description': 'General oil products and heavy hydrocarbons'
    },
    
    # 11. Complex waste - 500m (precautionary high distance)
    'KOMPLEKS_AFFALD': {
        'distance_m': 500,
        'keywords': ['kompleks', 'olie', 'affald', 'diverse', 'øvrige', 'sjældne', 'restgruppe',
                    'lægemidler', 'medicin', 'farmakologi', 'vandige', 'opløsning', 'udefinerbar',
                    'uidentificer', 'blandet', 'lossepladsperkolat', 'perkolat', 'deponi', 'pcb', 'asbeststøv', 'asbest'],
        'description': 'Complex waste mixtures requiring precautionary approach'
    },
    
    # 12. Polar solvents - 100m (moderate mobility)
    'POLARE_OPLØSNINGSMIDLER': {
        'distance_m': 100,
        'keywords': ['methanol', 'propanol', 'isopropanol', 'ethanol', 'glykoler', 'glycol', 'dioxan',
                    'diethylether', 'ether', 'dimethylsulfamid', 'dms', 'alkoholer', 'ethylenglykol',
                    'propylenglykol', 'ethylacetat', 'n-butyl-acetat', 'tetrahydrofuran', 'butanol',
                    'benzylalkohol', 'anilin', 'dimethylamin', 'pyridin'],
        'description': 'Polar solvents, alcohols, ethers and amines'
    },
    
    # 13. Specialty chemicals - 200m (moderate mobility)
    'SPECIALKEMIKALIER': {
        'distance_m': 200,
        'keywords': ['phthalater', 'phthalate', 'cresoler', 'cresol', 'kimtal', 'heterocy', 'cykl',
                    'fluorcarbon', 'fluorid', 'fluoranthen', 'formaldehyd', 'malathion',
                    'pftba', 'pfas', 'pfos', 'pfoa', 'acetonitril', 'dmso', 'dimethylsulfoxid',
                    'toluensulfonamid', 'epichlorhydrin', 'dichlorpropanol', 'phthalat', 'succinsyre',
                    'adipinsyre', 'glutarsyre', 'fumarsyre', 'hydrogensulfid', 'hydrogen sulfid',
                    'carbontetrachlorid', 'carbon tetrachlorid', 'tetrachlorcarbon'],
        'description': 'Specialty chemicals, plasticizers and cyclic compounds'
    },
    
    # 14. Gases - 500m (very high mobility)
    'GASSER': {
        'distance_m': 500,
        'keywords': ['methan', 'methane', 'carbondioxid', 'co2', 'hydrogen', 'gas'],
        'description': 'Gases with very high mobility in groundwater'
    },
    
    # 15. Additional halogenated compounds - 200m (moderate mobility)
    'HALOGENEREDE_FORBINDELSER': {
        'distance_m': 200,
        'keywords': ['monobromdichlormet', 'bromdichlormethan', 'brommethan', 'dichlormethan'],
        'description': 'Additional halogenated compounds'
    }
}


def categorize_contamination_substance(substance_text):
    """
    Categorize a contamination substance into one of the distance-based groups.
    
    Args:
        substance_text (str): The contamination substance text from V1/V2 data
        
    Returns:
        tuple: (category_name, distance_m) or ('UNCATEGORIZED', None) if no match
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'UNCATEGORIZED', None
    
    substance_lower = substance_text.lower().strip()
    
    # Check each category for keyword matches
    for category, info in COMPOUND_DISTANCE_MAPPING.items():
        for keyword in info['keywords']:
            if keyword in substance_lower:
                return category, info['distance_m']
    
    # If no match found
    return 'UNCATEGORIZED', None


def get_category_info(category_name):
    """
    Get detailed information about a specific category.
    
    Args:
        category_name (str): Name of the category
        
    Returns:
        dict: Category information including distance, keywords, and description
    """
    return COMPOUND_DISTANCE_MAPPING.get(category_name, None)


def get_all_categories():
    """
    Get list of all available categories.
    
    Returns:
        list: List of category names
    """
    return list(COMPOUND_DISTANCE_MAPPING.keys())


def get_distance_distribution():
    """
    Get distribution of distance thresholds across categories.
    
    Returns:
        dict: Distance threshold -> list of categories using that threshold
    """
    distance_dist = {}
    for category, info in COMPOUND_DISTANCE_MAPPING.items():
        distance = info['distance_m']
        if distance not in distance_dist:
            distance_dist[distance] = []
        distance_dist[distance].append(category)
    
    return distance_dist


def analyze_substance_list(substances):
    """
    Analyze a list of contamination substances and return categorization summary.
    
    Args:
        substances (list): List of substance strings
        
    Returns:
        dict: Analysis summary including categorized counts and uncategorized substances
    """
    results = {
        'total_substances': len(substances),
        'categorized': 0,
        'uncategorized': 0,
        'uncategorized_list': [],
        'category_counts': {},
        'distance_counts': {}
    }
    
    for substance in substances:
        if pd.isna(substance):
            continue
            
        category, distance = categorize_contamination_substance(substance)
        
        if category == 'UNCATEGORIZED':
            results['uncategorized'] += 1
            results['uncategorized_list'].append(substance)
        else:
            results['categorized'] += 1
            
            # Count by category
            if category not in results['category_counts']:
                results['category_counts'][category] = 0
            results['category_counts'][category] += 1
            
            # Count by distance
            if distance not in results['distance_counts']:
                results['distance_counts'][distance] = 0
            results['distance_counts'][distance] += 1
    
    return results


if __name__ == "__main__":
    # Test the categorization system
    test_substances = [
        "Benzin", "TCE", "Arsen", "PAH", "Atrazin", "Olie", 
        "Unknown substance", "Chloroform", "MTBE"
    ]
    
    print("Testing Compound Categorization System")
    print("=" * 50)
    
    for substance in test_substances:
        category, distance = categorize_contamination_substance(substance)
        print(f"{substance:20} -> {category:25} ({distance}m)")
    
    print(f"\nTotal categories: {len(get_all_categories())}")
    print(f"Distance distribution: {get_distance_distribution()}")
