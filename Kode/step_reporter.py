"""
Standardized reporting utilities for all workflow steps.

Provides consistent, clean console output across all steps while preserving
essential information for understanding data transformations and filtering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd


# ============================================================================
# SECTION 1: BASIC FORMATTING UTILITIES
# ============================================================================

def report_step_header(step_num: int | str, step_name: str, width: int = 60):
    """Print standardized step header."""
    print("\n" + "=" * width)
    print(f"STEP {step_num}: {step_name}")
    print("=" * width)


def report_subsection(title: str, width: int = 60, char: str = "─"):
    """Print subsection divider."""
    print("\n" + char * width)
    print(title)
    print(char * width)


def report_counts(label: str, sites: int = None, gvfks: int = None, 
                  combinations: int = None, segments: int = None, indent: int = 0):
    """Print standardized counts with optional indent."""
    prefix = "  " * indent
    parts = []
    if combinations is not None:
        parts.append(f"{combinations:,} combinations")
    if sites is not None:
        parts.append(f"{sites:,} sites")
    if gvfks is not None:
        parts.append(f"{gvfks:,} GVFKs")
    if segments is not None:
        parts.append(f"{segments:,} segments")

    if parts:
        print(f"{prefix}{label}: {', '.join(parts)}")


def report_filtering(filtered_count: int, total_count: int, reason: str, indent: int = 0):
    """Report filtering with reason."""
    prefix = "  " * indent
    if total_count > 0:
        pct = (filtered_count / total_count) * 100
        print(f"{prefix}FILTERED: {filtered_count:,} / {total_count:,} ({pct:.1f}%) - {reason}")
    else:
        print(f"{prefix}FILTERED: {filtered_count:,} - {reason}")


def report_breakdown(title: str, items: dict, indent: int = 0):
    """Report categorical breakdown."""
    prefix = "  " * indent
    print(f"{prefix}{title}:")
    for category, count in items.items():
        if isinstance(count, tuple):
            print(f"{prefix}  ├─ {category}: {count[0]:,} ({count[1]:.1f}%)")
        else:
            print(f"{prefix}  ├─ {category}: {count:,}")


def report_statistics(stats: dict, indent: int = 0):
    """Report key statistics in clean format."""
    prefix = "  " * indent
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{prefix}{key}: {value:,.1f}")
        elif isinstance(value, int):
            print(f"{prefix}{key}: {value:,}")
        else:
            print(f"{prefix}{key}: {value}")


def report_completion(step_num: int | str):
    """Print step completion marker."""
    print(f"\nStep {step_num} complete")


# ============================================================================
# SECTION 1B: RISIKOVURDERING SUMMARY (STEPS 1-5)
# ============================================================================

def report_risikovurdering_summary(results: Dict[str, Any]):
    """
    Print consolidated Risikovurdering (Steps 1-5) summary.
    """
    print("\n" + "=" * 60)
    print("RISIKOVURDERING SUMMARY (Steps 1-5)")
    print("=" * 60)
    
    # Extract key metrics
    total_gvfk = results.get("step1", {}).get("total_gvfk", 0)
    river_contact = results.get("step2", {}).get("river_contact_count", 0)
    
    step3 = results.get("step3", {})
    gvfk_with_sites = len(step3.get("gvfk_with_v1v2_names", []))
    v1v2_sites_df = step3.get("v1v2_sites")
    unique_sites = v1v2_sites_df["Lokalitet_ID"].nunique() if v1v2_sites_df is not None and not v1v2_sites_df.empty else 0
    
    step5 = results.get("step5", {})
    general_risk = step5.get("general_high_risk_sites")
    compound_risk = step5.get("compound_high_risk_sites")
    
    high_risk_sites = general_risk["Lokalitet_ID"].nunique() if general_risk is not None and not general_risk.empty else 0
    compound_sites = compound_risk["Lokalitet_ID"].nunique() if compound_risk is not None and not compound_risk.empty else 0
    high_risk_gvfk = len(step5.get("high_risk_gvfk", []))
    
    print(f"\nData Filtering:")
    print(f"  Total GVFKs in Denmark: {total_gvfk:,}")
    if total_gvfk > 0:
        print(f"  GVFKs with river contact: {river_contact:,} ({river_contact/total_gvfk*100:.1f}%)")
        print(f"  GVFKs with contaminated sites: {gvfk_with_sites:,} ({gvfk_with_sites/total_gvfk*100:.1f}%)")
    else:
        print(f"  GVFKs with river contact: {river_contact:,}")
        print(f"  GVFKs with contaminated sites: {gvfk_with_sites:,}")
    
    print(f"\nRisk Assessment Results:")
    print(f"  Unique contaminated sites: {unique_sites:,}")
    if unique_sites > 0:
        print(f"  High-risk sites (≤500m): {high_risk_sites:,} ({high_risk_sites/unique_sites*100:.1f}% of sites)")
        print(f"  Compound-specific risk sites: {compound_sites:,} ({compound_sites/unique_sites*100:.1f}% of sites)")
    else:
        print(f"  High-risk sites (≤500m): {high_risk_sites:,}")
        print(f"  Compound-specific risk sites: {compound_sites:,}")
    
    if total_gvfk > 0:
        print(f"  High-risk GVFKs: {high_risk_gvfk:,} ({high_risk_gvfk/total_gvfk*100:.1f}% of all GVFKs)")
    else:
        print(f"  High-risk GVFKs: {high_risk_gvfk:,}")
    
    print("=" * 60)
    
    print(f"\nRisk Assessment Results:")
    print(f"  Unique contaminated sites: {unique_sites:,}")
    if unique_sites > 0:
        print(f"  High-risk sites (≤500m): {high_risk_sites:,} ({high_risk_sites/unique_sites*100:.1f}% of sites)")
        print(f"  Compound-specific risk sites: {compound_sites:,} ({compound_sites/unique_sites*100:.1f}% of sites)")
    else:
        print(f"  High-risk sites (≤500m): {high_risk_sites:,}")
        print(f"  Compound-specific risk sites: {compound_sites:,}")
    
    if total_gvfk > 0:
        print(f"  High-risk GVFKs: {high_risk_gvfk:,} ({high_risk_gvfk/total_gvfk*100:.1f}% of all GVFKs)")
    else:
        print(f"  High-risk GVFKs: {high_risk_gvfk:,}")
    
    print("=" * 60)


# ============================================================================
# SECTION 2: STEP 6 SPECIFIC REPORTING
# ============================================================================

def report_step6_filtering(audit_df: pd.DataFrame, initial_count: int):
    """
    Report results of filtering audit.
    """
    report_subsection("FILTERING CASCADE")
    print(f"  Input rows: {initial_count:,}")
    
    if audit_df.empty:
        print("  No rows filtered (all data valid)")
        return

    # Count filtered by reason
    reasons = audit_df['Filter_Reason'].value_counts()
    
    print(f"\n  Filtered total: {len(audit_df):,} rows ({len(audit_df)/initial_count*100:.1f}%)")
    report_breakdown("Reasons", reasons.to_dict(), indent=1)


def report_step6_flux_stats(input_rows: int, scenario_rows: int, dropped_summary: Dict[str, int]):
    """
    Report flux calculation statistics including scenario expansion and dropped rows.
    """
    print(f"\nFlux Calculation Statistics:")
    print(f"  Input rows (substance/category pairs): {input_rows:,}")
    print(f"  Output rows (expanded scenarios): {scenario_rows:,}")
    
    total_dropped = sum(dropped_summary.values())
    if total_dropped > 0:
        print(f"\n  Dropped rows (no concentration defined): {total_dropped:,}")
        report_breakdown("Dropped by Category", dropped_summary, indent=2)


def report_step6_summary(
    site_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
    site_exceedances: pd.DataFrame,
    gvfk_exceedances: Optional[pd.DataFrame] = None,
    flux_input_count: int = 0,
    flux_output_count: int = 0,
    dropped_concentration_summary: Optional[Dict[str, int]] = None,
):
    """
    Print consolidated Step 6 summary in clean, focused format.
    """
    report_subsection("RESULTS")
    
    # Flux calculation summary
    if flux_input_count > 0 and flux_output_count > 0:
        print(f"\nFlux Calculation:")
        print(f"  Input: {flux_input_count:,} substance/site combinations")
        print(f"  Output: {flux_output_count:,} scenario-based flux calculations")
    
    # Data quality warning
    if dropped_concentration_summary and sum(dropped_concentration_summary.values()) > 0:
        total_dropped = sum(dropped_concentration_summary.values())
        print(f"\n  ⚠️  Data Quality: {total_dropped:,} rows excluded (no concentration data)")
        for category, count in sorted(dropped_concentration_summary.items(), key=lambda x: -x[1]):
            print(f"      • {category}: {count:,} rows")
    
    # Processing results
    sites_processed = site_flux['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in site_flux.columns else 0
    segments_affected = site_flux['Nearest_River_FID'].nunique() if 'Nearest_River_FID' in site_flux.columns else 0
    
    print(f"\nProcessing Results:")
    print(f"  Sites processed: {sites_processed:,}")
    print(f"  Segments affected: {segments_affected:,}")
    
    if 'Flux_kg_yr' in site_flux.columns:
        total_flux = site_flux['Flux_kg_yr'].sum()
        print(f"  Total flux: {total_flux:,.1f} kg/year")
    
    # MKK Exceedances (THE CRITICAL RESULT)
    print(f"\nMKK EXCEEDANCES (CRITICAL):")
    if not site_exceedances.empty:
        exc_sites = site_exceedances['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in site_exceedances.columns else len(site_exceedances)
        exc_segments = segment_summary[segment_summary['Max_Exceedance_Factor'] > 1]['River_FID'].nunique() if 'Max_Exceedance_Factor' in segment_summary.columns else 0
        
        print(f"  Sites causing exceedance: {exc_sites:,}")
        print(f"  Segments with exceedance: {exc_segments:,}")
        
        if gvfk_exceedances is not None and not gvfk_exceedances.empty:
            exc_gvfk = gvfk_exceedances['GVFK'].nunique() if 'GVFK' in gvfk_exceedances.columns else len(gvfk_exceedances)
            print(f"  GVFKs affected: {exc_gvfk:,}")
        
        # Top 5 worst exceedances
        if 'Max_Exceedance_Factor' in segment_summary.columns:
            top_exceedances = segment_summary[segment_summary['Max_Exceedance_Factor'] > 1].nlargest(5, 'Max_Exceedance_Factor')
            if not top_exceedances.empty:
                print(f"\n  Top 5 worst exceedances:")
                for _, row in top_exceedances.iterrows():
                    river_id = row.get('River_FID', 'Unknown')
                    river_name = row.get('River_Segment_Name', '')
                    factor = row.get('Max_Exceedance_Factor', 0)
                    name_str = f" ({river_name})" if river_name else ""
                    print(f"    • {river_id}{name_str}: {factor:,.0f}x MKK")
    else:
        print(f"  No MKK exceedances found.")


# ============================================================================
# SECTION 3: WORKFLOW SUMMARY GENERATION
# ============================================================================

def generate_workflow_summary(results: Dict[str, Any], save_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Generate a consolidated workflow summary DataFrame.
    
    Args:
        results: Dictionary containing results from all steps
        save_path: Optional path to save CSV
        
    Returns:
        DataFrame with workflow statistics
    """
    summary_rows = []
    
    # Step 2: River contact
    if "step2" in results and results["step2"].get("gvfk_with_rivers"):
        summary_rows.append({
            "Step": "Step 2",
            "Metric": "GVFKs with river contact",
            "Count": len(results["step2"]["gvfk_with_rivers"])
        })
    
    # Step 3: V1/V2 sites
    if "step3" in results:
        step3 = results["step3"]
        if step3.get("gvfk_with_v1v2"):
            summary_rows.append({
                "Step": "Step 3",
                "Metric": "GVFKs with contaminated sites",
                "Count": len(step3["gvfk_with_v1v2"])
            })
        if step3.get("v1v2_combined") is not None:
            summary_rows.append({
                "Step": "Step 3",
                "Metric": "Site-GVFK combinations",
                "Count": len(step3["v1v2_combined"])
            })
    
    # Step 4: Distances
    if "step4" in results and results["step4"].get("distance_results") is not None:
        dist = results["step4"]["distance_results"]
        summary_rows.append({
            "Step": "Step 4",
            "Metric": "Combinations with distances",
            "Count": len(dist)
        })
    
    # Step 5: Risk assessment
    if "step5" in results:
        step5 = results["step5"]
        if step5.get("general_high_risk_sites") is not None:
            summary_rows.append({
                "Step": "Step 5a",
                "Metric": "General high-risk sites (≤500m)",
                "Count": step5["general_high_risk_sites"]["Lokalitet_ID"].nunique()
            })
        if step5.get("compound_high_risk_sites") is not None:
            summary_rows.append({
                "Step": "Step 5b",
                "Metric": "Compound-specific sites",
                "Count": step5["compound_high_risk_sites"]["Lokalitet_ID"].nunique()
            })
    
    # Step 6: Tilstandsvurdering
    if "step6" in results:
        step6 = results["step6"]
        if step6.get("site_flux") is not None:
            summary_rows.append({
                "Step": "Step 6",
                "Metric": "Sites in flux calculations",
                "Count": step6["site_flux"]["Lokalitet_ID"].nunique()
            })
        if step6.get("site_exceedances") is not None:
            summary_rows.append({
                "Step": "Step 6",
                "Metric": "Sites exceeding MKK",
                "Count": step6["site_exceedances"]["Lokalitet_ID"].nunique() if "Lokalitet_ID" in step6["site_exceedances"].columns else len(step6["site_exceedances"])
            })
    
    summary_df = pd.DataFrame(summary_rows)
    
    if save_path:
        summary_df.to_csv(save_path, index=False)
        print(f"\nWorkflow summary saved: {save_path.name}")
    
    return summary_df


def print_workflow_completion(results_dir: Path):
    """Print final workflow completion message."""
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETED")
    print("=" * 60)
    print(f"\nResults: {results_dir}/")
