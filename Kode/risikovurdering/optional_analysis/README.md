# Optional Analysis Tools

This folder contains extended analysis and visualization tools that are **NOT part of the core standardized workflow**.

## Purpose

These modules provide in-depth exploratory analysis and comprehensive visualizations for research and presentation purposes. They are useful for:
- Detailed investigation of specific scenarios
- Creating publication-quality figures
- Comprehensive reporting for stakeholders
- Exploratory data analysis

However, they are **not required** for the standard risk assessment workflow (Steps 1-5).

## Files

### `step5_branch_analysis.py` (2,178 lines)
Comprehensive analysis of sites without substance data ("branch-only" sites).

**Features:**
- Compares branch-only sites against Step 5a general assessment
- Distance distributions and geographic patterns
- Industry/activity frequency analysis
- GVFK impact analysis
- Extensive visualizations

**When to use:** Research projects investigating sites lacking contamination data

**Run independently:** `python -m risikovurdering.optional_analysis.step5_branch_analysis`

---

### `step6_risikovurdering_analysis.py` (2,312 lines)
Final comprehensive analysis comparing core (Step 5b compound-specific) vs expanded scenarios.

**Features:**
- 4 analysis phases with 20+ visualizations
- Hexagonal heatmaps and choropleth maps
- GVFK progression metrics
- Branch/activity three-way comparisons
- Regional distribution analysis

**When to use:** Final decision-support analysis, comprehensive reporting

**Run independently:** `python -m risikovurdering.optional_analysis.step6_risikovurdering_analysis`

---

### `selected_visualizations.py` (1,551 lines)
Extended visualization suite with publication-quality plots.

**Features:**
- Advanced distance histograms with thresholds
- GVFK progression plots
- HTML tables for PowerPoint
- Custom styling and formatting

**When to use:** Creating figures for publications or presentations

**Usage:** Import specific functions or run standalone

---

### `create_interactive_map.py` (279 lines)
Interactive HTML maps for web-based exploration.

**Features:**
- Leaflet-based interactive maps
- Site clustering and tooltips
- GVFK boundary visualization
- Distance-based coloring

**When to use:** Creating interactive web-based visualizations for stakeholders

---

## Core Workflow

For the **standard risk assessment workflow**, use only:

```
main_workflow.py (orchestrator)
  ├── step1_all_gvfk.py
  ├── step2_river_contact.py
  ├── step3_v1v2_sites.py
  ├── step4_distances.py
  └── step5_risk_assessment.py
```

The core workflow produces:
- CSV tables with risk assessment results
- Shapefiles for GIS analysis
- Essential verification plots (3-4 charts)

---

## Notes

These optional tools are maintained but not part of the standardized methodology. Use them for research and exploration, but rely on the core workflow for reproducible, standardized risk assessments.
