"""
Step 6 Filtering Audit Trail

This module tracks all sites that are filtered out during Step 6 processing
and exports a comprehensive CSV with the filtering reason.

Usage:
    Can be run standalone to audit existing Step 6 run, or integrated into step6_tilstandsvurdering.py
"""

import sys
from pathlib import Path

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_output_path


def create_filtering_audit():
    """
    Compare Step 5 input with Step 6 output to identify all filtered sites.

    Returns:
        DataFrame with columns: Lokalitet_ID, GVFK, Category, Filter_Stage, Filter_Reason, Additional_Info
    """

    print("=" * 80)
    print("STEP 6 FILTERING AUDIT")
    print("=" * 80)

    # Load Step 5 input (what went into Step 6)
    step5 = pd.read_csv(get_output_path("step5_compound_detailed_combinations"))
    print(f"\nStep 5 input: {len(step5)} rows, {step5['Lokalitet_ID'].nunique()} sites")

    # Load Step 6 output (what came out)
    site_flux = pd.read_csv(get_output_path("step6_flux_site_segment"))
    print(
        f"Step 6 output: {len(site_flux)} rows, {site_flux['Lokalitet_ID'].nunique()} sites"
    )

    # Find sites that disappeared
    step5_sites = set(step5["Lokalitet_ID"].unique())
    step6_sites = set(site_flux["Lokalitet_ID"].unique())
    filtered_sites = step5_sites - step6_sites

    print(f"\nSites filtered out: {len(filtered_sites)}")
    print(f"Sites retained: {len(step6_sites)}")
    print(f"Filtering rate: {len(filtered_sites) / len(step5_sites) * 100:.1f}%")

    # Create audit records for filtered sites
    audit_records = []

    for site_id in filtered_sites:
        site_rows = step5[step5["Lokalitet_ID"] == site_id]

        # Create one audit record per (site, GVFK, category) combination
        for (gvfk, category), group in site_rows.groupby(
            ["GVFK", "Qualifying_Category"]
        ):
            record = {
                "Lokalitet_ID": site_id,
                "Lokalitetsnavn": group.iloc[0].get("Lokalitetsnavn", "N/A"),
                "GVFK": gvfk,
                "Qualifying_Category": category,
                "Nearest_River_ov_id": group.iloc[0].get("Nearest_River_ov_id", "N/A"),
                "Distance_to_River_m": group.iloc[0].get("Distance_to_River_m", None),
                "Regionsnavn": group.iloc[0].get("Regionsnavn", "N/A"),
                "Kommunenavn": group.iloc[0].get("Kommunenavn", "N/A"),
                "Filter_Stage": "Unknown",
                "Filter_Reason": "Site disappeared between Step 5 and Step 6",
                "Additional_Info": f"{len(group)} substances in this category",
            }
            audit_records.append(record)

    # Also track sites that made it through but lost some GVFKs/categories
    for site_id in step6_sites:
        step5_combos = step5[step5["Lokalitet_ID"] == site_id][
            ["GVFK", "Qualifying_Category"]
        ].drop_duplicates()
        step6_combos = site_flux[site_flux["Lokalitet_ID"] == site_id][
            ["GVFK", "Qualifying_Category"]
        ].drop_duplicates()

        # Find combinations that were in Step 5 but not in Step 6
        step5_keys = set(zip(step5_combos["GVFK"], step5_combos["Qualifying_Category"]))
        step6_keys = set(zip(step6_combos["GVFK"], step6_combos["Qualifying_Category"]))
        filtered_combos = step5_keys - step6_keys

        for gvfk, category in filtered_combos:
            combo_rows = step5[
                (step5["Lokalitet_ID"] == site_id)
                & (step5["GVFK"] == gvfk)
                & (step5["Qualifying_Category"] == category)
            ]

            record = {
                "Lokalitet_ID": site_id,
                "Lokalitetsnavn": combo_rows.iloc[0].get("Lokalitetsnavn", "N/A"),
                "GVFK": gvfk,
                "Qualifying_Category": category,
                "Nearest_River_ov_id": combo_rows.iloc[0].get(
                    "Nearest_River_ov_id", "N/A"
                ),
                "Distance_to_River_m": combo_rows.iloc[0].get(
                    "Distance_to_River_m", None
                ),
                "Regionsnavn": combo_rows.iloc[0].get("Regionsnavn", "N/A"),
                "Kommunenavn": combo_rows.iloc[0].get("Kommunenavn", "N/A"),
                "Filter_Stage": "Partial",
                "Filter_Reason": "Site retained but this GVFK-category combination filtered",
                "Additional_Info": f"Site made it through with {len(step6_combos)} other combinations",
            }
            audit_records.append(record)

    audit_df = pd.DataFrame(audit_records)

    # Export
    output_path = (
        get_output_path("step6_flux_site_segment").parent
        / "step6_filtered_sites_audit.csv"
    )
    audit_df.to_csv(output_path, index=False)

    print(f"\nAudit trail exported: {output_path}")
    print(f"Total filtered entries: {len(audit_df)}")

    # Summary by filter stage
    if not audit_df.empty:
        print("\nFiltering summary:")
        print(
            f"  Completely filtered sites: {(audit_df['Filter_Stage'] == 'Unknown').sum()}"
        )
        print(
            f"  Partially filtered combinations: {(audit_df['Filter_Stage'] == 'Partial').sum()}"
        )

    return audit_df


def integrate_with_step6_pipeline():
    """
    This function should be called from step6_tilstandsvurdering.py at each filtering stage
    to build the audit trail in real-time.

    Usage in step6_tilstandsvurdering.py:

    # At start of run_step6():
    filtering_audit = []

    # After each filter:
    filtered_rows = original_df[~original_df.index.isin(kept_df.index)]
    for _, row in filtered_rows.iterrows():
        filtering_audit.append({
            'Lokalitet_ID': row['Lokalitet_ID'],
            'GVFK': row['GVFK'],
            'Category': row.get('Qualifying_Category', 'N/A'),
            'Filter_Stage': 'Stage_Name',
            'Filter_Reason': 'Specific reason',
            'Additional_Info': 'Any relevant details'
        })

    # At end, export:
    pd.DataFrame(filtering_audit).to_csv(...)
    """
    pass


if __name__ == "__main__":
    audit_df = create_filtering_audit()

    # Show examples
    if not audit_df.empty:
        print("\n" + "=" * 80)
        print("EXAMPLE FILTERED SITES")
        print("=" * 80)

        # Show first 10 completely filtered sites
        complete = audit_df[audit_df["Filter_Stage"] == "Unknown"]
        if not complete.empty:
            print("\nCompletely filtered sites (first 10):")
            print(
                complete[
                    [
                        "Lokalitet_ID",
                        "Lokalitetsnavn",
                        "GVFK",
                        "Qualifying_Category",
                        "Filter_Reason",
                    ]
                ]
                .head(10)
                .to_string(index=False)
            )

        # Show first 10 partially filtered combinations
        partial = audit_df[audit_df["Filter_Stage"] == "Partial"]
        if not partial.empty:
            print("\nPartially filtered combinations (first 10):")
            print(
                partial[
                    ["Lokalitet_ID", "GVFK", "Qualifying_Category", "Additional_Info"]
                ]
                .head(10)
                .to_string(index=False)
            )
