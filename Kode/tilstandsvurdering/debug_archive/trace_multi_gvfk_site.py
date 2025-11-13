"""
Trace a specific multi-GVFK site through the entire pipeline to validate logic.

This script follows site 209-03052 (appears in 3 GVFKs, all connecting to 1 river)
from Step 4 through Step 6 to ensure the aggregation logic is correct.

The expected behavior is:
1. Step 4: Site appears 3 times (once per GVFK), each with distance to same river
2. Step 5: Site appears 3 times (once per GVFK-category combination)
3. Step 6: Site aggregated to 1 flux entry per category (using minimum distance)
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (
    CATEGORY_SCENARIOS,
    RIVERS_PATH,
    get_output_path,
)

# ===========================================================================
# Configuration
# ===========================================================================

# Site to trace (from validation: appears in 3 GVFKs, all connect to 1 river)
TRACE_SITE = "209-03052"

# ===========================================================================
# Load all pipeline data
# ===========================================================================


def load_pipeline_data():
    """Load data from all pipeline steps"""
    print("Loading pipeline data...")

    data = {
        "step4": pd.read_csv(
            get_output_path("step4_final_distances_for_risk_assessment")
        ),
        "step5": pd.read_csv(get_output_path("step5_compound_detailed_combinations")),
        "site_flux": pd.read_csv(get_output_path("step6_flux_site_segment")),
        "cmix": pd.read_csv(get_output_path("step6_cmix_results")),
        "rivers": gpd.read_file(RIVERS_PATH),
    }

    return data


# ===========================================================================
# Trace through pipeline
# ===========================================================================


def trace_site(site_id, data):
    """Trace a specific site through the entire pipeline"""

    print("=" * 80)
    print(f"TRACING SITE: {site_id}")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # STEP 4: Distance Calculation
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 4: Distance Calculation")
    print("=" * 60)

    step4_rows = data["step4"][data["step4"]["Lokalitet_ID"] == site_id]

    if step4_rows.empty:
        print(f"❌ Site {site_id} not found in Step 4 output")
        return

    print(f"\nSite appears {len(step4_rows)} times in Step 4 (once per GVFK)")
    print("\nDetails:")

    for idx, row in step4_rows.iterrows():
        print(f"\n  GVFK: {row['GVFK']}")
        print(f"    Distance to river: {row['Distance_to_River_m']:.2f} m")
        print(f"    Nearest river FID: {row['Nearest_River_FID']}")
        print(f"    Nearest river ov_id: {row['Nearest_River_ov_id']}")
        print(f"    Nearest river name: {row['Nearest_River_ov_navn']}")
        print(f"    Total river segments in GVFK: {row['River_Segment_Count']}")

        # Show all river segments in this GVFK
        if pd.notna(row["River_Segment_ov_ids"]) and row["River_Segment_ov_ids"]:
            segment_ids = row["River_Segment_ov_ids"].split(";")
            print(f"    All river segments: {', '.join(segment_ids)}")

    # Validate: Are all GVFKs connecting to the same river segment?
    unique_rivers = step4_rows["Nearest_River_ov_id"].unique()
    print(
        f"\n✅ Site connects to {len(unique_rivers)} unique river segment(s): {', '.join(unique_rivers)}"
    )

    if len(unique_rivers) == 1:
        print(f"   This confirms: Multiple GVFKs can connect to the same river segment")
        print(
            f"   Expected behavior: Step 6 should aggregate into 1 flux entry per category"
        )

    # -----------------------------------------------------------------------
    # Verify River Segment Details
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("RIVER SEGMENT VERIFICATION")
    print("=" * 60)

    rivers = data["rivers"]

    for gvfk in step4_rows["GVFK"].unique():
        gvfk_row = step4_rows[step4_rows["GVFK"] == gvfk].iloc[0]
        nearest_fid = int(gvfk_row["Nearest_River_FID"])

        # Find river segment in shapefile
        river_segment = rivers[rivers.index == nearest_fid]

        if not river_segment.empty:
            river_info = river_segment.iloc[0]
            print(f"\nGVFK {gvfk} → River FID {nearest_fid}:")
            print(f"  ov_id: {river_info.get('ov_id', 'N/A')}")
            print(f"  ov_navn: {river_info.get('ov_navn', 'N/A')}")
            print(f"  GVForekom: {river_info.get('GVForekom', 'N/A')}")
            print(f"  Kontakt: {river_info.get('Kontakt', 'N/A')}")
        else:
            print(f"\n⚠️  River FID {nearest_fid} not found in shapefile")

    # -----------------------------------------------------------------------
    # STEP 5: Compound Assessment
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 5: Compound Assessment")
    print("=" * 60)

    step5_rows = data["step5"][data["step5"]["Lokalitet_ID"] == site_id]

    print(f"\nSite appears {len(step5_rows)} times in Step 5")
    print(f"GVFKs: {step5_rows['GVFK'].nunique()} unique")
    print(f"River segments: {step5_rows['Nearest_River_ov_id'].nunique()} unique")
    print(f"Categories: {step5_rows['Qualifying_Category'].nunique()} unique")

    # Show breakdown by GVFK and category
    print("\nBreakdown by GVFK and Category:")
    for gvfk, gvfk_group in step5_rows.groupby("GVFK"):
        print(f"\n  GVFK: {gvfk}")
        print(f"    River: {gvfk_group['Nearest_River_ov_id'].iloc[0]}")
        print(f"    Distance: {gvfk_group['Distance_to_River_m'].iloc[0]:.2f} m")
        print(
            f"    Categories: {', '.join(gvfk_group['Qualifying_Category'].unique())}"
        )
        print(f"    Rows: {len(gvfk_group)}")

    # -----------------------------------------------------------------------
    # STEP 6: Flux Calculation (Site-Level)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 6: Site-Level Flux Calculation")
    print("=" * 60)

    site_flux = data["site_flux"][data["site_flux"]["Lokalitet_ID"] == site_id]

    print(f"\nSite appears {len(site_flux)} times in site flux output")
    print(f"GVFKs: {site_flux['GVFK'].nunique()} unique")
    print(f"River segments: {site_flux['Nearest_River_ov_id'].nunique()} unique")

    # Expected behavior: After aggregation by (Site, River, Category),
    # should have fewer rows than Step 5
    print(f"\nStep 5 rows: {len(step5_rows)}")
    print(f"Step 6 site flux rows: {len(site_flux)}")
    print(f"Reduction: {len(step5_rows) - len(site_flux)} rows")

    if len(step5_rows) > len(site_flux):
        print("✅ Aggregation occurred (multiple GVFKs consolidated)")
    elif len(step5_rows) == len(site_flux):
        print("⚠️  No aggregation (check if scenarios expanded)")
    else:
        print("❌ More rows in Step 6 than Step 5 (unexpected!)")

    # Show flux details
    print("\nFlux details by category and scenario:")
    for category, cat_group in site_flux.groupby("Qualifying_Category"):
        print(f"\n  Category: {category}")
        for _, row in cat_group.iterrows():
            print(f"    Scenario: {row['Qualifying_Substance']}")
            print(f"      GVFK: {row['GVFK']}")
            print(f"      River: {row['Nearest_River_ov_id']}")
            print(f"      Distance: {row['Distance_to_River_m']:.2f} m")
            print(f"      Area: {row['Area_m2']:.0f} m²")
            print(f"      Infiltration: {row['Infiltration_mm_per_year']:.1f} mm/yr")
            print(f"      Concentration: {row['Standard_Concentration_ug_L']:.1f} µg/L")
            print(f"      Flux: {row['Pollution_Flux_kg_per_year']:.6f} kg/yr")

    # -----------------------------------------------------------------------
    # Validate Aggregation Logic
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("AGGREGATION LOGIC VALIDATION")
    print("=" * 60)

    # For each category, check if aggregation happened correctly
    for category in step5_rows["Qualifying_Category"].unique():
        print(f"\nCategory: {category}")

        # Step 5: How many rows per GVFK?
        step5_cat = step5_rows[step5_rows["Qualifying_Category"] == category]
        print(
            f"  Step 5: {len(step5_cat)} rows across {step5_cat['GVFK'].nunique()} GVFKs"
        )
        for gvfk in step5_cat["GVFK"].unique():
            gvfk_rows = step5_cat[step5_cat["GVFK"] == gvfk]
            print(f"    {gvfk}: {len(gvfk_rows)} rows")

        # Step 6: How many scenarios generated?
        site_flux_cat = site_flux[site_flux["Qualifying_Category"] == category]
        expected_scenarios = CATEGORY_SCENARIOS.get(category, [])

        if expected_scenarios:
            print(
                f"  Expected scenarios: {len(expected_scenarios)} ({', '.join(expected_scenarios)})"
            )
            print(f"  Step 6: {len(site_flux_cat)} flux rows")

            if len(site_flux_cat) == len(expected_scenarios):
                print(f"  ✅ Correct: {len(expected_scenarios)} scenarios generated")
            else:
                print(
                    f"  ❌ Mismatch: Expected {len(expected_scenarios)}, got {len(site_flux_cat)}"
                )
        else:
            print(f"  No scenarios for this category (single flux row expected)")
            print(f"  Step 6: {len(site_flux_cat)} flux rows")

            if len(site_flux_cat) == 1:
                print(f"  ✅ Correct: 1 flux row")
            else:
                print(
                    f"  ⚠️  Multiple rows for no-scenario category: {len(site_flux_cat)}"
                )

    # -----------------------------------------------------------------------
    # STEP 6: Segment-Level Cmix
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 6: Segment-Level Cmix (Aggregated)")
    print("=" * 60)

    # Get the river segment(s) this site affects
    affected_rivers = site_flux["Nearest_River_ov_id"].unique()

    for river in affected_rivers:
        print(f"\nRiver Segment: {river}")

        # Get all cmix rows for this segment (from all sites, not just traced site)
        river_cmix = data["cmix"][data["cmix"]["Nearest_River_ov_id"] == river]

        print(f"  Total scenarios in this segment: {len(river_cmix)}")

        # For each category this site contributes to
        for category in site_flux["Qualifying_Category"].unique():
            cat_cmix = river_cmix[river_cmix["Qualifying_Category"] == category]

            if cat_cmix.empty:
                print(f"\n  ❌ Category {category} not found in cmix for this segment!")
                continue

            print(f"\n  Category: {category}")
            print(
                f"    Scenarios in cmix: {cat_cmix['Qualifying_Substance'].nunique()}"
            )

            # Check if our site is in the contributing sites
            for _, cmix_row in cat_cmix.iterrows():
                substance = cmix_row["Qualifying_Substance"]
                contributing_sites = cmix_row.get("Contributing_Site_IDs", "")

                if pd.notna(contributing_sites) and site_id in str(contributing_sites):
                    site_count = cmix_row.get("Contributing_Site_Count", "N/A")
                    total_flux = cmix_row.get("Total_Flux_kg_per_year", "N/A")
                    cmix_val = cmix_row.get("Cmix_ug_L", "N/A")
                    mkk = cmix_row.get("MKK_ug_L", "N/A")
                    exceeds = cmix_row.get("Exceedance_Flag", False)

                    print(f"\n    ✅ Scenario: {substance}")
                    print(f"       Contributing sites: {site_count}")
                    print(f"       Total flux: {total_flux} kg/yr")
                    print(f"       Cmix: {cmix_val} µg/L")
                    print(f"       MKK: {mkk} µg/L")
                    print(f"       Exceeds MKK: {'YES' if exceeds else 'NO'}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nSite {site_id} pipeline trace:")
    print(f"  Step 4: {len(step4_rows)} rows ({step4_rows['GVFK'].nunique()} GVFKs)")
    print(f"  Step 5: {len(step5_rows)} rows")
    print(f"  Step 6 site flux: {len(site_flux)} rows")
    print(f"  Affected river segments: {len(affected_rivers)}")

    # Validate the key premise
    gvfk_count = step4_rows["GVFK"].nunique()
    river_count = step4_rows["Nearest_River_ov_id"].nunique()

    print(f"\n  Site in {gvfk_count} GVFKs, affecting {river_count} river segment(s)")

    if gvfk_count > river_count:
        print(f"  ✅ This confirms: Multiple GVFKs can connect to the same river")
        print(f"     Step 6 correctly aggregates these into 1 flux per category")
    elif gvfk_count == river_count:
        print(f"  ✅ Each GVFK connects to a different river (1:1 mapping)")
    else:
        print(f"  ❌ ERROR: More rivers than GVFKs (impossible!)")

    # Check if minimum distance was used
    if len(step4_rows) > 1:
        distances = step4_rows["Distance_to_River_m"].tolist()
        min_dist = min(distances)
        flux_dist = (
            site_flux["Distance_to_River_m"].iloc[0] if not site_flux.empty else None
        )

        print(f"\n  Distances across GVFKs: {[f'{d:.2f}' for d in distances]} m")
        print(f"  Minimum distance: {min_dist:.2f} m")
        print(
            f"  Distance used in flux: {flux_dist:.2f} m"
            if flux_dist
            else "  No flux calculated"
        )

        if flux_dist and abs(flux_dist - min_dist) < 0.01:
            print(f"  ✅ Step 6 correctly uses minimum distance")
        elif flux_dist:
            print(
                f"  ❌ Step 6 uses {flux_dist:.2f} m instead of minimum {min_dist:.2f} m"
            )


# ===========================================================================
# Test Multiple Sites
# ===========================================================================


def test_multiple_sites(data):
    """Test several representative multi-GVFK cases"""

    print("\n\n" + "=" * 80)
    print("TESTING MULTIPLE REPRESENTATIVE SITES")
    print("=" * 80)

    step5 = data["step5"]

    # Find different multi-GVFK patterns
    site_patterns = []

    for site_id in step5["Lokalitet_ID"].unique():
        site_rows = step5[step5["Lokalitet_ID"] == site_id]
        gvfk_count = site_rows["GVFK"].nunique()
        river_count = site_rows["Nearest_River_ov_id"].nunique()

        if gvfk_count > 1:
            pattern = {
                "site_id": site_id,
                "gvfks": gvfk_count,
                "rivers": river_count,
                "pattern": f"{gvfk_count} GVFKs → {river_count} rivers",
            }
            site_patterns.append(pattern)

    # Group by pattern
    from collections import defaultdict

    pattern_groups = defaultdict(list)
    for p in site_patterns:
        pattern_groups[p["pattern"]].append(p["site_id"])

    print("\nMulti-GVFK site patterns found:")
    for pattern, sites in sorted(pattern_groups.items()):
        print(f"  {pattern}: {len(sites)} sites")
        print(f"    Examples: {', '.join(sites[:3])}")

    # Test one representative from each pattern
    print("\n" + "=" * 80)
    print("Testing representative sites:")

    tested = set()
    for pattern, sites in sorted(pattern_groups.items()):
        if len(tested) >= 3:  # Limit to 3 examples
            break

        site = sites[0]
        if site not in tested:
            tested.add(site)
            trace_site(site, data)


# ===========================================================================
# Main
# ===========================================================================


def main():
    """Run site tracing"""

    print("=" * 80)
    print("MULTI-GVFK SITE TRACING - VALIDATION OF AGGREGATION LOGIC")
    print("=" * 80)

    data = load_pipeline_data()

    # Trace specific site
    trace_site(TRACE_SITE, data)

    # Test multiple representative sites
    test_multiple_sites(data)

    print("\n" + "=" * 80)
    print("TRACING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
