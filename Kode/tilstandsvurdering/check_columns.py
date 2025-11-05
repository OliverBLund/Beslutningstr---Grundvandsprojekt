"""Check what columns are present after layer_mapping merge."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import GVFK_LAYER_MAPPING_PATH, get_output_path

# Load Step 5 results
step5 = pd.read_csv(get_output_path("step5_compound_detailed_combinations"), encoding='utf-8')
print(f"Step 5 columns: {len(step5.columns)}")
print(f"Step 5 column names: {sorted(step5.columns.tolist())}\n")

# Load layer mapping
layer_mapping = pd.read_csv(GVFK_LAYER_MAPPING_PATH, sep=";", encoding="latin-1")
print(f"Layer mapping columns: {len(layer_mapping.columns)}")
print(f"Layer mapping column names (first 20): {sorted(layer_mapping.columns.tolist())[:20]}\n")

# Simulate the merge - NEW APPROACH (only select needed columns)
enriched = step5.merge(
    layer_mapping[["GVForekom", "DK-modellag"]],
    left_on="GVFK",
    right_on="GVForekom",
    how="left",
)
print(f"After merge columns: {len(enriched.columns)}")
print(f"After merge column names: {sorted(enriched.columns.tolist())}\n")

# Check which columns came from layer_mapping
step5_cols = set(step5.columns)
layer_cols = set(layer_mapping.columns)
new_cols = set(enriched.columns) - step5_cols
print(f"New columns added by merge: {len(new_cols)}")
print(f"New column names: {sorted(new_cols)}\n")

# Now drop GVForekom
enriched = enriched.drop(columns=["GVForekom"])
print(f"After dropping GVForekom: {len(enriched.columns)} columns")

# Check what's still extra
still_extra = set(enriched.columns) - step5_cols
print(f"Extra columns still present (excluding GVForekom): {len(still_extra)}")
print(f"Extra column names: {sorted(still_extra)}")
