import pandas as pd
import numpy as np
from collections import Counter
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import V1_CSV_PATH, V2_CSV_PATH


def load_data():
    """Load V1 and V2 CSV files."""
    print("Loading V1 and V2 CSV data...")
    
    # Load V1 data
    try:
        v1_data = pd.read_csv(V1_CSV_PATH, encoding='utf-8')
        print(f"✓ V1 data loaded: {len(v1_data)} rows")
    except Exception as e:
        print(f"✗ Error loading V1 data: {e}")
        v1_data = pd.DataFrame()
    
    # Load V2 data
    try:
        v2_data = pd.read_csv(V2_CSV_PATH, encoding='utf-8')
        print(f"✓ V2 data loaded: {len(v2_data)} rows")
    except Exception as e:
        print(f"✗ Error loading V2 data: {e}")
        v2_data = pd.DataFrame()
    
    return v1_data, v2_data

v1, v2 = load_data()

# Compound grouping system based on the exact groups from the distance tables
COMPOUND_DISTANCE_MAPPING = {
    # 1. BTX'er (oil and benzene compounds) - 50m from table
    'BTXER': {
        'distance_m': 50,
        'keywords': ['btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', 'xylene', 'benzin', 'olie-benzen', 
                    'aromater', 'aromat', 'c5-c10', 'c10-c25', 'kulbrintefraktion', 'monocyk', 'bicyk',
                    'tex (sum)', 'styren'],
        'description': 'BTX compounds including oil-benzene mixtures and aromatic hydrocarbons',
        'examples': ['Benzin', 'Olie-benzen', 'BTX', 'BTEX', 'Xylen', 'Toluen', 'Aromater', 'TEX (sum)', 'Styren']
    },
    
    # 2. Chlorinated solvents (1,1,1-TCA and TCE) - 500m from table  
    'CHLORINATED_SOLVENTS': {
        'distance_m': 500,
        'keywords': ['1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor', 'tetrachlor',
                    'vinylchlorid', 'dichlorethylen', 'dichlorethan', 'chlorerede', 'opl.midl', 'opløsningsmidl',
                    'cis-1,2-dichlorethyl', 'trans-1,2-dichloreth', 'chlorethan'],
        'description': 'Chlorinated solvents like TCE, TCA, vinyl chloride and dichloroethylenes',
        'examples': ['1,1,1-TCA', 'TCE', 'Tetrachlorethylen', 'Vinylchlorid', 'Dichlorethylen', 'Cis-1,2-dichlorethyl']
    },
    
    # 3. Polære (MTBE) - 100m from table
    'POLARE': {
        'distance_m': 100,
        'keywords': ['mtbe', 'methyl tert-butyl ether', 'acetone', 'keton'],
        'description': 'Polar compounds like MTBE and acetone',
        'examples': ['MTBE', 'Acetone']
    },
    
    # 4. Phenoler (Phenol and COD) - 300m for phenol, 500m for COD
    'PHENOLER': {
        'distance_m': 300,
        'keywords': ['phenol', 'fenol', 'cod', 'klorofenol'],
        'description': 'Phenolic compounds including COD',
        'examples': ['Phenol', 'COD', 'Klorofenol']
    },
    
    # 5. Klorede kulbrinter (Chloroform) - 200m from table
    'KLOREDE_KULBRINTER': {
        'distance_m': 200,
        'keywords': ['chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform', 'dibromethane', 'bromerede'],
        'description': 'Chlorinated/brominated hydrocarbons like chloroform and bromoform',
        'examples': ['Chloroform', 'Bromoform', '1,2-Dibromethane', 'Klorede kulbrinter']
    },
    
    # 6. Chlorphenoler (2,6-dichlorophenol) - 200m from table
    'CHLORPHENOLER': {
        'distance_m': 200,
        'keywords': ['dichlorophenol', 'chlorphenol', 'diklorofenol', 'klorofenol'],
        'description': 'Chlorinated phenols',
        'examples': ['2,6-dichlorophenol', 'Chlorphenol']
    },
    
    # 7. PAH'er (Fluoranthen) - 30m from table
    'PAHER': {
        'distance_m': 30,
        'keywords': ['pah', 'fluoranthen', 'benzo', 'naftalen', 'naphtalen', 'naphthalen', 'pyren', 'anthracen', 'antracen',
                    'tjære', 'tar', 'phenanthren', 'fluoren', 'acenaphthen', 'acenaphthylen', 'chrysen', 'chrysene',
                    'benzfluranthen', 'methylnaphthalen', 'benz(ghi)perylen'],
        'description': 'Polycyclic Aromatic Hydrocarbons and coal tar compounds',
        'examples': ['Fluoranthen', 'PAH', 'Benzo(a)pyren', 'Naphtalen', 'Tjære', 'Phenanthren', 'Antracen', 'Chrysen']
    },
    
    # 8. Pesticider (Mechlorprop-p) - 500m from table
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
        'description': 'Pesticides, herbicides, fungicides and PFAS compounds',
        'examples': ['Mechlorprop-p', 'MCPP', 'Atrazin', 'Bentazon', 'DDE', 'DDD', 'Isoproturon', 'Malathion', 'Deltamethrin']
    },
    
    # 9. Uorganiske forbindelser (Arsenic, Cyanide) - 100-200m from table
    'UORGANISKE_FORBINDELSER': {
        'distance_m': 150,
        'keywords': ['arsen', 'arsenic', 'cyanid', 'cyanide', 'tungmetal', 'bly', 'cadmium', 'krom', 'chrom',
                    'nikkel', 'zink', 'kobber', 'kviksølv', 'jern', 'mangan', 'aluminium', 'sølv', 'barium',
                    'kobolt', 'metaller', 'tributyltin', 'tbt', 'tin', 'molybden', 'antimon', 'calcium',
                    'natrium', 'kalium', 'magnesium', 'thallium', 'bor', 'chlorid', 'sulfat', 'nitrat',
                    'fluorid', 'fluor', 'ammoniak', 'ammonium', 'phosphor', 'tributhyltinacetat', 
                    'tributhyltinnaphth', 'nitrit'],
        'description': 'Inorganic compounds including heavy metals, organometallics and salts',
        'examples': ['Arsen', 'Cyanid', 'Tungmetaller', 'Bly', 'Chrom', 'Sølv', 'Tin', 'Molybden', 'Chlorid', 'Sulfat']
    },
    
    # FOR THE AI: EVERYTHING BELOW THIS POINT IS NOT A COMPOUNDGROUP THAT COMES FROM THE ACTUAL LITTERATURE AND SHOULD THEREORE BE ADRESSED AS SUCH
    # 10. General oil products that don't fit BTX
    'OLIEPRODUKTER': {
        'distance_m': 200,
        'keywords': ['olie', 'diesel', 'fyring', 'olieprodukter', 'fedt', 'petroleum', 'smøreolie', 
                    'c25-c35', 'kulbrintefraktion', 'terpentin', 'white spirit', 'methyl-napthalen', 'naphthacen'],
        'description': 'General oil products and heavy hydrocarbons (non-BTX)',
        'examples': ['Olie', 'Dieselolie', 'Fyringsolie', 'C25-C35 kulbrintefraktion', 'Terpentin']
    },
    
    # 11. Complex waste/leachate - assign moderate distance
    'KOMPLEKS_AFFALD': {
        'distance_m': 300,
        'keywords': ['lossepladsperkolat', 'perkolat', 'affald', 'leachate', 'deponi', 'pcb', 'asbeststøv', 'asbest'],
        'description': 'Complex waste mixtures, PCBs and asbestos',
        'examples': ['Lossepladsperkolat', 'PCB', 'Asbeststøv']
    },
    
    # 12. Polar solvents and alcohols - 100m (similar to MTBE)
    'POLARE_OPLØSNINGSMIDLER': {
        'distance_m': 100,
        'keywords': ['methanol', 'propanol', 'isopropanol', 'ethanol', 'glykoler', 'glycol', 'dioxan', 
                    'diethylether', 'ether', 'dimethylsulfamid', 'dms', 'alkoholer', 'ethylenglykol',
                    'propylenglykol', 'ethylacetat', 'n-butyl-acetat', 'tetrahydrofuran', 'butanol',
                    'benzylalkohol', 'anilin', 'dimethylamin', 'pyridin'],
        'description': 'Polar solvents, alcohols, ethers and amines',
        'examples': ['Methanol', '2-propanol', 'Glykoler', 'Dioxan', 'DMS', 'Alkoholer', 'Ethylacetat', 'Tetrahydrofuran']
    },
    
    # 13. Specialty chemicals and plasticizers - 200m (moderate mobility)
    'SPECIALKEMIKALIER': {
        'distance_m': 200,
        'keywords': ['phthalater', 'phthalate', 'cresoler', 'cresol', 'kimtal', 'heterocy', 'cykl',
                    'fluorcarbon', 'fluorid', 'fluoranthen', 'formaldehyd', 'malathion',
                    'pftba', 'pfas', 'pfos', 'pfoa', 'acetonitril', 'dmso', 'dimethylsulfoxid',
                    'toluensulfonamid', 'epichlorhydrin', 'dichlorpropanol', 'phthalat', 'succinsyre',
                    'adipinsyre', 'glutarsyre', 'fumarsyre', 'hydrogensulfid', 'hydrogen sulfid',
                    'carbontetrachlorid', 'carbon tetrachlorid', 'tetrachlorcarbon'],
        'description': 'Specialty chemicals, plasticizers and cyclic compounds',
        'examples': ['Phthalater', 'Cresoler', 'Cykl./heterocy. forb', 'Fluorcarbon', 'Formaldehyd', 'PFAS']
    },
    
    # 14. Gases - very high mobility, 500m
    'GASSER': {
        'distance_m': 500,
        'keywords': ['methan', 'methane', 'carbondioxid', 'co2', 'hydrogen', 'gas'],
        'description': 'Gases with very high mobility',
        'examples': ['Methan', 'Carbondioxid', 'Hydrogen']
    },
    
    # 15. Additional halogenated compounds - 200m
    'HALOGENEREDE_FORBINDELSER': {
        'distance_m': 200,
        'keywords': ['monobromdichlormet', 'bromdichlormethan', 'brommethan', 'dichlormethan'],
        'description': 'Additional halogenated compounds',
        'examples': ['Monobromdichlormet', 'Bromdichlormethan']
    },
    
    # 16. Complex waste mixtures - 500m (high precaution)
    'KOMPLEKS_AFFALD': {
        'distance_m': 500,
        'keywords': ['kompleks', 'olie', 'affald', 'diverse', 'øvrige', 'sjældne', 'restgruppe',
                    'lægemidler', 'medicin', 'farmakologi', 'vandige', 'opløsning', 'udefinerbar',
                    'uidentificer', 'blandet'],
        'description': 'Complex waste mixtures and undefined contamination',
        'examples': ['Kompleks affald', 'Olie', 'Diverse', 'Lægemidler', 'Vandige opløsninger']
    }
}

def categorize_contamination_substance(substance_text):
    """
    Categorize a contamination substance into one of the distance-based groups.
    
    Args:
        substance_text (str): The contamination substance text from V1/V2 data
        
    Returns:
        tuple: (category_name, distance_m) or (None, None) if no match
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return None, None
    
    substance_lower = substance_text.lower()
    
    # Check each category for keyword matches
    for category, info in COMPOUND_DISTANCE_MAPPING.items():
        for keyword in info['keywords']:
            if keyword in substance_lower:
                return category, info['distance_m']
    
    # If no match found
    return 'UNCATEGORIZED', None

def analyze_contamination_categorization(data, dataset_name):
    """Analyze how well the contamination substances can be categorized."""
    print(f"\n{'='*60}")
    print(f"CONTAMINATION CATEGORIZATION ANALYSIS: {dataset_name}")
    print(f"{'='*60}")
    
    if 'Lokalitetensstoffer' not in data.columns:
        print("No 'Lokalitetensstoffer' column found")
        return
    
    # Get all contamination substances
    substances = data['Lokalitetensstoffer'].dropna()
    print(f"Total records with contamination data: {len(substances)}")
    
    # Categorize each substance
    categorization_results = []
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        categorization_results.append({
            'original_substance': substance,
            'category': category,
            'distance_m': distance
        })
    
    # Convert to DataFrame for analysis
    results_df = pd.DataFrame(categorization_results)
    
    # Category distribution
    category_counts = results_df['category'].value_counts()
    print(f"\nCategorization results:")
    for category, count in category_counts.items():
        pct = round(count / len(results_df) * 100, 1)
        if str(category) in COMPOUND_DISTANCE_MAPPING:
            distance = COMPOUND_DISTANCE_MAPPING[str(category)]['distance_m']
            print(f"  {category}: {count} ({pct}%) - Distance: {distance}m")
        else:
            print(f"  {category}: {count} ({pct}%) - No distance assigned")
    
    # Show what substances are in each category
    print(f"\n{'='*60}")
    print(f"SUBSTANCES IN EACH CATEGORY: {dataset_name}")
    print(f"{'='*60}")
    
    for category in category_counts.index:
        if category == 'UNCATEGORIZED':
            continue  # Handle uncategorized separately
            
        category_substances = results_df[results_df['category'] == category]['original_substance'].unique()
        distance = COMPOUND_DISTANCE_MAPPING.get(str(category), {}).get('distance_m', 'N/A')
        
        print(f"\n--- {category} ({distance}m) ---")
        print(f"Unique substances: {len(category_substances)}")
        
        # Count frequency of each substance
        substance_counts = results_df[results_df['category'] == category]['original_substance'].value_counts()
        
        # Show top 15 most common substances in this category
        print("Top substances (with frequency):")
        for substance, freq in substance_counts.head(15).items():
            print(f"  '{substance}': {freq} occurrences")
        
        if len(substance_counts) > 15:
            print(f"  ... and {len(substance_counts) - 15} more unique substances")
    
    # Show uncategorized substances for manual review
    uncategorized = results_df[results_df['category'] == 'UNCATEGORIZED']['original_substance'].unique()
    if len(uncategorized) > 0:
        print(f"\n--- UNCATEGORIZED ---")
        print(f"Uncategorized substances ({len(uncategorized)}):")
        uncategorized_counts = results_df[results_df['category'] == 'UNCATEGORIZED']['original_substance'].value_counts()
        
        for substance, freq in uncategorized_counts.head(20).items():
            print(f"  '{substance}': {freq} occurrences")
        if len(uncategorized_counts) > 20:
            print(f"  ... and {len(uncategorized_counts) - 20} more")
    
    return results_df

def export_uncategorized_to_csv(results_df, dataset_name):
    """Export uncategorized substances to CSV for manual review."""
    uncategorized_counts = results_df[results_df['category'] == 'UNCATEGORIZED']['original_substance'].value_counts()
    
    if uncategorized_counts.empty:
        print(f"No uncategorized substances in {dataset_name}")
        return
    
    # Create DataFrame for export
    export_df = pd.DataFrame({
        'substance': uncategorized_counts.index,
        'frequency': uncategorized_counts.values,
        'suggested_category': '',
        'suggested_distance_m': '',
        'notes': ''
    })
    
    filename = f"uncategorized_{dataset_name.lower()}.csv"
    export_df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Exported {len(export_df)} uncategorized substances to {filename}")
    return filename

# Analyze both datasets
print("Analyzing contamination substance categorization...")
if not v1.empty:
    v1_categorization = analyze_contamination_categorization(v1, "V1")
    if 'v1_categorization' in locals():
        export_uncategorized_to_csv(v1_categorization, "V1")
    
if not v2.empty:
    v2_categorization = analyze_contamination_categorization(v2, "V2")
    if 'v2_categorization' in locals():
        export_uncategorized_to_csv(v2_categorization, "V2")

def examine_category_detail(results_df, category_name, dataset_name):
    """Examine all substances in a specific category in detail."""
    print(f"\n{'='*80}")
    print(f"DETAILED EXAMINATION: {category_name} in {dataset_name}")
    print(f"{'='*80}")
    
    if results_df is None or results_df.empty:
        print("No data available")
        return
    
    category_data = results_df[results_df['category'] == category_name]
    
    if category_data.empty:
        print(f"No substances found in category {category_name}")
        return
    
    # Get distance for this category
    distance = COMPOUND_DISTANCE_MAPPING.get(category_name, {}).get('distance_m', 'N/A')
    print(f"Distance threshold: {distance}m")
    print(f"Total occurrences: {len(category_data)}")
    
    # Show all unique substances with their frequencies
    substance_counts = category_data['original_substance'].value_counts()
    print(f"Unique substances: {len(substance_counts)}")
    print("\nAll substances in this category:")
    
    for i, (substance, count) in enumerate(substance_counts.items(), 1):
        pct = round(count / len(category_data) * 100, 1)
        print(f"  {i:2d}. '{substance}': {count} occurrences ({pct}%)")

# Example usage functions
def examine_btx_category():
    """Quick function to examine BTX category."""
    if 'v1_categorization' in globals():
        examine_category_detail(v1_categorization, 'BTXER', 'V1')
    if 'v2_categorization' in globals():
        examine_category_detail(v2_categorization, 'BTXER', 'V2')

def examine_oil_category():
    """Quick function to examine oil products category."""
    if 'v1_categorization' in globals():
        examine_category_detail(v1_categorization, 'OLIEPRODUKTER', 'V1')
    if 'v2_categorization' in globals():
        examine_category_detail(v2_categorization, 'OLIEPRODUKTER', 'V2')

print("\n" + "="*60)
print("EXAMINATION FUNCTIONS AVAILABLE:")
print("="*60)
print("examine_btx_category() - Examine BTX substances")
print("examine_oil_category() - Examine oil product substances")
print("examine_category_detail(results_df, 'CATEGORY_NAME', 'DATASET') - Examine any category")
print("analyze_uncategorized_substances(results_df, 'DATASET') - Show uncategorized substances")
print("Available categories:", list(COMPOUND_DISTANCE_MAPPING.keys())) 

def analyze_uncategorized_substances(results_df, dataset_name):
    """Show uncategorized substances for manual review."""
    uncategorized = results_df[results_df['category'] == 'UNCATEGORIZED']['original_substance'].unique()
    
    if len(uncategorized) == 0:
        print(f"No uncategorized substances in {dataset_name}!")
        return
    
    print(f"\n{'='*60}")
    print(f"UNCATEGORIZED SUBSTANCES: {dataset_name}")
    print(f"{'='*60}")
    print(f"Total uncategorized: {len(uncategorized)}")
    
    print(f"\nUncategorized substances (sorted):")
    for substance in sorted(uncategorized):
        print(f"  '{substance}'")
    
    # Count frequency of each uncategorized substance
    substance_counts = results_df[results_df['category'] == 'UNCATEGORIZED']['original_substance'].value_counts()
    print(f"\nFrequency of uncategorized substances:")
    for substance, count in substance_counts.head(10).items():
        print(f"  '{substance}': {count} occurrences")
    
    if len(substance_counts) > 10:
        print(f"  ... and {len(substance_counts) - 10} more substances")
    
    print(f"\nNote: These substances may need additional keywords added to COMPOUND_DISTANCE_MAPPING")
    print(f"or could be mapped to existing categories with new keyword patterns.")
    
    return uncategorized 