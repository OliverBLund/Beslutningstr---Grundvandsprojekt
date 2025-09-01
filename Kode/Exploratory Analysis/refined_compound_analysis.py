"""
Refined Compound Categorization Analysis - Literature-Based Categories Only
===========================================================================

This script analyzes V1/V2 contamination data using only the 9 literature-based 
compound categories plus a catch-all "OTHER" category. Results are exported to 
Excel for easy review.

Author: Analysis for Boss Discussion
Date: January 2025
"""

import pandas as pd
import numpy as np
from collections import Counter
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import V1_CSV_PATH, V2_CSV_PATH

# REFINED COMPOUND MAPPING - Literature-based categories only
LITERATURE_COMPOUND_MAPPING = {
    # 1. BTX compounds + Oil products - 50m (literature-based)
    'BTXER': {
        'fractile_60_m': 15,        # 60% of plumes within this distance
        'fractile_75_m': 20,        # 75% of plumes within this distance  
        'fractile_90_m': 25,        # 90% of plumes within this distance
        'maksimal_m': 50,           # Maximum plume length (current distance_m)
        'distance_m': 50,           # Keep for backward compatibility
        'keywords': ['btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', 'xylene', 'benzin', 'olie-benzen',
                    'aromater', 'aromat', 'c5-c10', 'c10-c25', 'kulbrintefraktion', 'monocyk', 'bicyk',
                    'tex (sum)', 'styren', 'olieprodukter', 'olie', 'fyringsolie', 'dieselolie', 'petroleum',
                    'diesel', 'fyring', 'fedt', 'smøreolie', 'c25-c35', 'terpentin', 'white spirit'],
        'description': 'BTX compounds and oil products including diesel, heating oil, and petroleum products',
        'literature_basis': 'Scientific studies on BTEX mobility in groundwater + oil product mobility'
    },
    
    # 2. Chlorinated solvents - 500m (literature-based)
    'CHLORINATED_SOLVENTS': {
        'fractile_60_m': 125,       # 60% of plumes within this distance
        'fractile_75_m': 180,       # 75% of plumes within this distance  
        'fractile_90_m': 500,       # 90% of plumes within this distance
        'maksimal_m': 500,          # Maximum plume length
        'distance_m': 500,          # Keep for backward compatibility
        'keywords': ['1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor', 'tetrachlor',
                    'vinylchlorid', 'dichlorethylen', 'dichlorethan', 'chlorerede', 'opl.midl', 'opløsningsmidl',
                    'cis-1,2-dichlorethyl', 'trans-1,2-dichloreth', 'chlorethan'],
        'description': 'Chlorinated solvents with very high groundwater mobility',
        'literature_basis': 'Regulatory distance tables for chlorinated solvents'
    },
    
    # 3. Polar compounds - 100m (literature-based)
    'POLARE': {
        'fractile_60_m': 75,        # 60% of plumes within this distance
        'fractile_75_m': 110,        # 75% of plumes within this distance  
        'fractile_90_m': 150,        # 90% of plumes within this distance
        'maksimal_m': 300,          # Maximum plume length
        'distance_m': 300,          # Keep for backward compatibility
        'keywords': ['mtbe', 'methyl tert-butyl ether', 'acetone', 'keton'],
        'description': 'Polar compounds like MTBE and acetone',
        'literature_basis': 'MTBE groundwater mobility studies'
    },
    
    # 4. Phenolic compounds - 300m (literature-based)
    'PHENOLER': {
        'fractile_60_m': 50,        # 60% of plumes within this distance
        'fractile_75_m': 60,       # 75% of plumes within this distance  
        'fractile_90_m': 70,       # 90% of plumes within this distance
        'maksimal_m': 100,          # Maximum plume length
        'distance_m': 100,          # Keep for backward compatibility
        'keywords': ['phenol', 'fenol', 'cod', 'klorofenol'],
        'description': 'Phenolic compounds including COD',
        'literature_basis': 'Phenol mobility and degradation studies'
    },
    
    # 5. Chlorinated hydrocarbons - 200m (literature-based)
    'KLOREDE_KULBRINTER': {
        'fractile_60_m': 60,        # 60% of plumes within this distance
        'fractile_75_m': 100,       # 75% of plumes within this distance  
        'fractile_90_m': 160,       # 90% of plumes within this distance
        'maksimal_m': 200,          # Maximum plume length
        'distance_m': 200,          # Keep for backward compatibility
        'keywords': ['chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform', 'dibromethane', 'bromerede'],
        'description': 'Chlorinated/brominated hydrocarbons',
        'literature_basis': 'Chloroform and brominated compound mobility data'
    },
    
    # 6. Chlorinated phenols - 200m (literature-based)
    'CHLORPHENOLER': {
        'fractile_60_m': 60,        # 60% of plumes within this distance
        'fractile_75_m': 100,       # 75% of plumes within this distance  
        'fractile_90_m': 160,       # 90% of plumes within this distance
        'maksimal_m': 200,          # Maximum plume length
        'distance_m': 200,          # Keep for backward compatibility
        'keywords': ['dichlorophenol', 'chlorphenol', 'diklorofenol', 'klorofenol'],
        'description': 'Chlorinated phenolic compounds',
        'literature_basis': 'Chlorinated phenol transport studies'
    },
    
    # 7. PAH compounds - 30m (literature-based)
    'PAHER': {
        'fractile_60_m': 9,         # 60% of plumes within this distance
        'fractile_75_m': 15,        # 75% of plumes within this distance  
        'fractile_90_m': 24,        # 90% of plumes within this distance
        'maksimal_m': 30,           # Maximum plume length
        'distance_m': 30,           # Keep for backward compatibility
        'keywords': ['pah', 'fluoranthen', 'benzo', 'naftalen', 'naphtalen', 'naphthalen', 'pyren', 'anthracen', 'antracen',
                    'tjære', 'tar', 'phenanthren', 'fluoren', 'acenaphthen', 'acenaphthylen', 'chrysen', 'chrysene',
                    'benzfluranthen', 'methylnaphthalen', 'benz(ghi)perylen'],
        'description': 'Polycyclic Aromatic Hydrocarbons - very low mobility due to high sorption',
        'literature_basis': 'PAH sorption and transport studies'
    },
    
    # 8. Pesticides - 500m (literature-based)
    'PESTICIDER': {
        'fractile_60_m': 150,       # 60% of plumes within this distance
        'fractile_75_m': 250,       # 75% of plumes within this distance  
        'fractile_90_m': 400,       # 90% of plumes within this distance
        'maksimal_m': 500,          # Maximum plume length
        'distance_m': 500,          # Keep for backward compatibility
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
        'description': 'Pesticides, herbicides, fungicides and PFAS compounds - high mobility',
        'literature_basis': 'Pesticide leaching studies and regulatory guidelines'
    },
    
    # 9. Inorganic compounds - 150m (literature-based)
    'UORGANISKE_FORBINDELSER': {
        'fractile_60_m': 45,        # 60% of plumes within this distance
        'fractile_75_m': 75,        # 75% of plumes within this distance  
        'fractile_90_m': 120,       # 90% of plumes within this distance
        'maksimal_m': 150,          # Maximum plume length
        'distance_m': 150,          # Keep for backward compatibility
        'keywords': ['arsen', 'arsenic', 'cyanid', 'cyanide', 'tungmetal', 'bly', 'cadmium', 'krom', 'chrom',
                    'nikkel', 'zink', 'kobber', 'kviksølv', 'jern', 'mangan', 'aluminium', 'sølv', 'barium',
                    'kobolt', 'metaller', 'tributyltin', 'tbt', 'tin', 'molybden', 'antimon', 'calcium',
                    'natrium', 'kalium', 'magnesium', 'thallium', 'bor', 'chlorid', 'sulfat', 'nitrat',
                    'fluorid', 'fluor', 'ammoniak', 'ammonium', 'phosphor', 'tributhyltinacetat',
                    'tributhyltinnaphth', 'nitrit'],
        'description': 'Inorganic compounds including heavy metals and salts',
        'literature_basis': 'Heavy metal mobility and salt transport studies'
    }
}

def categorize_contamination_substance_refined(substance_text):
    """
    Categorize using only literature-based categories + OTHER.
    
    Args:
        substance_text (str): The contamination substance text
        
    Returns:
        tuple: (category_name, distance_m) or ('OTHER', None) if no match
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'OTHER', None
    
    substance_lower = substance_text.lower().strip()
    
    # Check each literature-based category for keyword matches
    for category, info in LITERATURE_COMPOUND_MAPPING.items():
        for keyword in info['keywords']:
            if keyword in substance_lower:
                return category, info['distance_m']
    
    # If no match found in literature categories
    return 'OTHER', None

def analyze_and_export_compounds():
    """
    Analyze V1/V2 compounds using refined categorization and export to Excel.
    """
    print("REFINED COMPOUND CATEGORIZATION ANALYSIS")
    print("=" * 60)
    print("Using only 9 literature-based categories + OTHER catch-all")
    print()
    
    # Load data
    try:
        v1_data = pd.read_csv(V1_CSV_PATH, encoding='utf-8')
        v2_data = pd.read_csv(V2_CSV_PATH, encoding='utf-8')
        print(f"Loaded V1: {len(v1_data)} rows")
        print(f"Loaded V2: {len(v2_data)} rows")
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # Combine datasets
    v1_data['dataset'] = 'V1'
    v2_data['dataset'] = 'V2'
    combined_data = pd.concat([v1_data, v2_data], ignore_index=True)
    
    # Get contamination substances
    substances = combined_data['Lokalitetensstoffer'].dropna()
    print(f"Total contamination records: {len(substances)}")
    
    # Categorize all substances
    results = []
    for idx, substance in enumerate(substances):
        if idx % 10000 == 0:
            print(f"Processing... {idx:,}/{len(substances):,}")
            
        category, distance = categorize_contamination_substance_refined(substance)
        results.append({
            'substance': substance,
            'category': category,
            'distance_m': distance,
            'dataset': combined_data.loc[substances.index[idx], 'dataset'] if idx < len(combined_data) else 'Unknown'
        })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Summary statistics
    print(f"\nCATEGORIZATION SUMMARY")
    print("=" * 30)
    
    category_counts = results_df['category'].value_counts()
    total_substances = len(results_df)
    
    for category, count in category_counts.items():
        pct = round(count / total_substances * 100, 1)
        if category in LITERATURE_COMPOUND_MAPPING:
            distance = LITERATURE_COMPOUND_MAPPING[category]['distance_m']
            print(f"{category:25} : {count:6,} ({pct:5.1f}%) - {distance}m")
        else:
            print(f"{category:25} : {count:6,} ({pct:5.1f}%) - No distance")
    
    # Create detailed Excel export
    excel_file = "compound_categorization_review.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = []
        for category, count in category_counts.items():
            if category in LITERATURE_COMPOUND_MAPPING:
                info = LITERATURE_COMPOUND_MAPPING[category]
                summary_data.append({
                    'Category': category,
                    'Count': count,
                    'Percentage': round(count / total_substances * 100, 1),
                    'Distance_m': info['distance_m'],
                    'Description': info['description'],
                    'Literature_Basis': info['literature_basis']
                })
            else:
                summary_data.append({
                    'Category': category,
                    'Count': count,
                    'Percentage': round(count / total_substances * 100, 1),
                    'Distance_m': 'TBD',
                    'Description': 'Catch-all category for uncategorized substances',
                    'Literature_Basis': 'None - requires decision'
                })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Sheet 2: Detailed substance breakdown by category
        for category in category_counts.index:
            if category == 'OTHER':
                # For OTHER category, show top substances for manual review
                other_substances = results_df[results_df['category'] == 'OTHER']['substance'].value_counts()
                other_df = pd.DataFrame({
                    'Substance': other_substances.index,
                    'Frequency': other_substances.values,
                    'Notes': ['Needs manual review'] * len(other_substances)
                })
                sheet_name = 'OTHER_substances'[:31]  # Excel sheet name limit
                other_df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # For categorized substances, show what was matched
                cat_substances = results_df[results_df['category'] == category]['substance'].value_counts()
                cat_df = pd.DataFrame({
                    'Substance': cat_substances.index,
                    'Frequency': cat_substances.values,
                    'Category': category,
                    'Distance_m': LITERATURE_COMPOUND_MAPPING[category]['distance_m']
                })
                sheet_name = category[:31]  # Excel sheet name limit
                cat_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Sheet 3: All raw data for reference
        results_df.to_excel(writer, sheet_name='Raw_Data', index=False)
    
    # Additional analysis: Locality-level patterns  
    print(f"\nADDITIONAL ANALYSIS")
    print("=" * 25)
    
    # 1. Multiple compounds per locality
    print(f"Analyzing contamination per locality (Lokalitetsnr)...")
    locality_substances = combined_data.groupby('Lokalitetsnr')['Lokalitetensstoffer'].apply(
        lambda x: len(set(s.strip() for row in x.dropna() for s in str(row).split(';') if s.strip()))
    )
    
    print(f"Localities with contamination data: {len(locality_substances):,}")
    print(f"Substances per locality - Min: {locality_substances.min()}, Max: {locality_substances.max()}")
    print(f"Substances per locality - Mean: {locality_substances.mean():.1f}, Median: {locality_substances.median():.1f}")
    
    multi_substance_localities = (locality_substances > 1).sum()
    print(f"Localities with multiple substances: {multi_substance_localities:,} ({multi_substance_localities/len(locality_substances)*100:.1f}%)")
    
    # 2. OTHER category breakdown
    other_substances = results_df[results_df['category'] == 'OTHER']['substance'].value_counts()
    print(f"\nOTHER category analysis:")
    print(f"Total OTHER substances: {len(other_substances):,} unique substances")
    print(f"Top 10 OTHER substances:")
    for i, (substance, count) in enumerate(other_substances.head(10).items(), 1):
        pct = count / len(results_df[results_df['category'] == 'OTHER']) * 100
        print(f"  {i:2d}. '{substance}': {count:,} ({pct:.1f}%)")
    
    print(f"\nExcel file created: {excel_file}")
    print("\nReady for boss review!")
    print("\nNext steps:")
    print("1. Review OTHER category substances in Excel")
    print("2. Check multi-substance localities")
    print("3. Decide on default distance for OTHER category")
    
    return results_df, excel_file

if __name__ == "__main__":
    results_df, excel_file = analyze_and_export_compounds()