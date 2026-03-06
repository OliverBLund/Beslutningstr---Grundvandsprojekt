"""
Verify Step 5 slide numbers by analyzing the data flow
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_output_path

print("=" * 80)
print("STEP 5 NUMBERS VERIFICATION")
print("=" * 80)

# Load Step 4 results
step4_file = get_output_path("step4_final_distances_for_risk_assessment")
df = pd.read_csv(step4_file)

print("\n1. INPUT FROM STEP 4:")
print("-" * 80)
total_combinations = len(df)
total_unique_sites = df["Lokalitet_ID"].nunique()
total_unique_gvfks = df["GVFK"].nunique()

print(f"Total combinations: {total_combinations:,}")
print(f"Total unique sites (Lokalitet_ID): {total_unique_sites:,}")
print(f"Total unique GVFKs: {total_unique_gvfks:,}")

# Calculate sites within 500m BEFORE substance filtering
print("\n2. SITES WITHIN 500M (BEFORE SUBSTANCE FILTERING):")
print("-" * 80)
within_500m = df[df["Distance_to_River_m"] <= 500]
within_500m_combinations = len(within_500m)
within_500m_sites = within_500m["Lokalitet_ID"].nunique()
within_500m_gvfks = within_500m["GVFK"].nunique()

print(f"Combinations within 500m: {within_500m_combinations:,}")
print(f"Unique sites within 500m: {within_500m_sites:,}")
print(f"Unique GVFKs within 500m: {within_500m_gvfks:,}")
print(f"Percentage of total sites: {within_500m_sites / total_unique_sites * 100:.1f}%")

# Check substance/landfill data availability
print("\n3. SUBSTANCE/LANDFILL DATA AVAILABILITY:")
print("-" * 80)


def has_substance_data(row):
    """Check if site has substance data"""
    substances_str = str(row.get("Lokalitetensstoffer", ""))
    has_substance = not (
        pd.isna(substances_str)
        or substances_str.strip() == ""
        or substances_str == "nan"
    )
    return has_substance


def has_landfill_keywords(text):
    """Check if text contains landfill keywords"""
    if pd.isna(text):
        return False
    text_lower = str(text).lower()
    landfill_keywords = [
        "losseplads",
        "affald",
        "depon",
        "deponi",
        "fyld",
        "fyldplads",
        "skraldeplads",
    ]
    return any(keyword in text_lower for keyword in landfill_keywords)


def has_qualifying_data(row):
    """Check if site has substance or landfill keywords"""
    has_substance = has_substance_data(row)

    branch_text = row.get("Lokalitetensbranche", "")
    activity_text = row.get("Lokalitetensaktivitet", "")
    has_landfill = has_landfill_keywords(branch_text) or has_landfill_keywords(
        activity_text
    )

    return has_substance or has_landfill


# Apply to full dataset
df["Has_Qualifying_Data"] = df.apply(has_qualifying_data, axis=1)
df["Has_Substance_Data"] = df.apply(has_substance_data, axis=1)

qualifying = df[df["Has_Qualifying_Data"] == True]
parked = df[df["Has_Qualifying_Data"] == False]

print(f"Qualifying (substance OR landfill keywords):")
print(f"  Combinations: {len(qualifying):,}")
print(f"  Unique sites: {qualifying['Lokalitet_ID'].nunique():,}")
print(f"  Unique GVFKs: {qualifying['GVFK'].nunique():,}")

print(f"\nParked (no qualifying data):")
print(f"  Combinations: {len(parked):,}")
print(f"  Unique sites: {parked['Lokalitet_ID'].nunique():,}")
print(f"  Unique GVFKs: {parked['GVFK'].nunique():,}")

# Within 500m breakdown by data availability
print("\n4. WITHIN 500M - BREAKDOWN BY DATA AVAILABILITY:")
print("-" * 80)

# Need to reapply the function to within_500m dataframe
within_500m["Has_Qualifying_Data"] = within_500m.apply(has_qualifying_data, axis=1)

within_500m_qualifying = within_500m[within_500m["Has_Qualifying_Data"] == True]
within_500m_parked = within_500m[within_500m["Has_Qualifying_Data"] == False]

print(f"Within 500m WITH qualifying data:")
print(f"  Combinations: {len(within_500m_qualifying):,}")
print(f"  Unique sites: {within_500m_qualifying['Lokalitet_ID'].nunique():,}")
print(f"  Unique GVFKs: {within_500m_qualifying['GVFK'].nunique():,}")

print(f"\nWithin 500m WITHOUT qualifying data (parked):")
print(f"  Combinations: {len(within_500m_parked):,}")
print(f"  Unique sites: {within_500m_parked['Lokalitet_ID'].nunique():,}")
print(f"  Unique GVFKs: {within_500m_parked['GVFK'].nunique():,}")

# Step 5b - Compound specific results
print("\n5. STEP 5B - COMPOUND-SPECIFIC ASSESSMENT:")
print("-" * 80)

step5b_file = get_output_path("step5_compound_detailed_combinations")
if os.path.exists(step5b_file):
    df_compound = pd.read_csv(step5b_file)
    compound_combinations = len(df_compound)
    compound_sites = df_compound["Lokalitet_ID"].nunique()
    compound_gvfks = df_compound["GVFK"].dropna().nunique()

    print(f"Combinations meeting compound thresholds: {compound_combinations:,}")
    print(f"Unique sites: {compound_sites:,}")
    print(f"Unique GVFKs: {compound_gvfks:,}")
    print(
        f"Percentage of total input: {compound_sites / total_unique_sites * 100:.1f}%"
    )
else:
    print("Step 5b results file not found")

# Calculate reduction
print("\n6. OVERALL REDUCTION CALCULATION:")
print("-" * 80)
if os.path.exists(step5b_file):
    reduction = total_unique_sites - compound_sites
    reduction_pct = (reduction / total_unique_sites) * 100
    print(f"Input sites: {total_unique_sites:,}")
    print(f"Final prioritized sites (Step 5b): {compound_sites:,}")
    print(f"Sites filtered out: {reduction:,}")
    print(f"Reduction percentage: {reduction_pct:.1f}%")

print("\n" + "=" * 80)
print("SLIDE NUMBERS COMPARISON:")
print("=" * 80)
print(f"\nSlide says: 'Input: 35.728 lokaliteter fra Trin 4 analysen'")
print(f"Actual:     {total_unique_sites:,} ✓")

print(f"\nSlide says: '7870 lokaliteter indenfor 500 m'")
print(f"Actual:     {within_500m_sites:,} sites within 500m (before filtering)")

print(
    f"\nSlide says: '3714 lokaliteter falder fra grundet ingen stoffer eller losseplads'"
)
print(
    f"Actual:     {within_500m_parked['Lokalitet_ID'].nunique():,} parked sites within 500m"
)

print(f"\nSlide says: 'Trin 5a: 4.156 lokaliteter (11,6%)'")
print(
    f"Actual:     {within_500m_qualifying['Lokalitet_ID'].nunique():,} qualifying sites within 500m"
)
if within_500m_qualifying["Lokalitet_ID"].nunique() > 0:
    pct_5a = within_500m_qualifying["Lokalitet_ID"].nunique() / total_unique_sites * 100
    print(f"            ({pct_5a:.1f}% of total input)")

print(f"\nSlide says: 'Trin 5b: 1.711 lokaliteter (4,8%)'")
if os.path.exists(step5b_file):
    print(f"Actual:     {compound_sites:,} sites")
    print(
        f"            ({compound_sites / total_unique_sites * 100:.1f}% of total input)"
    )

print("\n" + "=" * 80)
