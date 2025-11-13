"""
Debug script to check the flow_scenarios data structure
"""
import pandas as pd
import sys
sys.path.append(r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Kode")

from data_loaders import load_flow_scenarios

print("Loading flow scenarios...")
flow_scenarios = load_flow_scenarios()

print(f"\nShape: {flow_scenarios.shape}")
print(f"\nColumns: {list(flow_scenarios.columns)}")
print(f"\nFirst 10 rows:")
print(flow_scenarios.head(10))

print(f"\n\nChecking for duplicate ov_ids:")
ov_id_counts = flow_scenarios['ov_id'].value_counts()
duplicates = ov_id_counts[ov_id_counts > 3]  # Should be exactly 3 per ov_id (Mean, Q90, Q95)

if len(duplicates) > 0:
    print(f"Found {len(duplicates)} ov_ids with more than 3 rows:")
    print(duplicates.head(10))
else:
    print("No duplicates found (all ov_ids have exactly 3 rows or fewer)")

# Check if all ov_ids have exactly 3 scenarios
print(f"\n\nOv_id scenario counts:")
print(ov_id_counts.value_counts().sort_index())

# Check unique scenarios
print(f"\n\nUnique scenarios: {flow_scenarios['Scenario'].unique()}")

# Check for NaN values
print(f"\n\nNaN values:")
print(flow_scenarios.isna().sum())

# Check example DKRIVER115
print(f"\n\nExample: DKRIVER115")
dkriver115 = flow_scenarios[flow_scenarios['ov_id'] == 'DKRIVER115']
print(dkriver115)
