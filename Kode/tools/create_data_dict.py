"""Create data dictionary with examples and ranges"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
from config import get_output_path

def get_column_info(df, col):
    """Get info about a column: type, example/range, format"""
    if df[col].dtype == 'object':
        # Check if it's a list format (contains semicolons)
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else ''
        is_list = ';' in str(sample)
        
        # Get unique count
        nunique = df[col].nunique()
        
        if is_list:
            return f"Liste (;-separeret)", f"f.eks. {str(sample)[:35]}..."
        elif nunique <= 10:
            # Categorical - show options
            options = df[col].dropna().unique()[:5]
            return "Kategorisk", ", ".join(str(o) for o in options)
        else:
            return "Tekst", f"f.eks. {str(sample)[:30]}"
    elif df[col].dtype == 'bool':
        return "Boolean", "True / False"
    elif df[col].dtype in ['int64', 'float64']:
        min_val = df[col].min()
        max_val = df[col].max()
        if df[col].dtype == 'int64':
            return "Heltal", f"{min_val:,.0f} – {max_val:,.0f}"
        else:
            if max_val > 1000:
                return "Decimaltal", f"{min_val:,.1f} – {max_val:,.1f}"
            else:
                return "Decimaltal", f"{min_val:.2f} – {max_val:.2f}"
    return str(df[col].dtype), "N/A"

# Load files
step5b = pd.read_csv(get_output_path('step5b_compound_combinations'))
step6 = pd.read_csv(get_output_path('step6_site_mkk_exceedances'))

print("="*80)
print("STEP 5b: Compound Combinations (Risikovurdering)")
print("="*80)
print(f"Rows: {len(step5b):,}")
print()

for col in step5b.columns:
    dtype, example = get_column_info(step5b, col)
    print(f"| {col} | {dtype} | {example} |")

print()
print("="*80)
print("STEP 6: Site MKK Exceedances (Tilstandsvurdering)")
print("="*80)
print(f"Rows: {len(step6):,}")
print()

for col in step6.columns:
    dtype, example = get_column_info(step6, col)
    print(f"| {col} | {dtype} | {example} |")
