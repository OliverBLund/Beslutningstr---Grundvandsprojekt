# Groundwater Contamination Risk Assessment Workflow

## Overview

This standardized workflow assesses contamination risk from contaminated sites (V1/V2) to groundwater aquifers (GVFKs) in Denmark. The methodology identifies high-risk sites based on proximity to rivers with groundwater contact and applies literature-based distance thresholds for different contamination categories.

**Version:** Standardized Core Workflow v2.0 (Steps 1-6)  
**Target Users:** Technical users with Python/GIS experience  
**Runtime:** ~15-30 minutes (full workflow including Step 6)

### Workflow Diagram

```mermaid
flowchart TD
    subgraph Step1["Step 1: Data Loading"]
        A1[("All GVFKs<br>~2,200")]
    end

    subgraph Step2["Step 2: River Contact Filter"]
        A1 --> B1{Has river<br>contact?}
        B1 -->|Yes| B2[("GVFKs with rivers<br>~1,600")]
        B1 -->|No| B3["Excluded<br>~600"]
    end

    subgraph Step3["Step 3: V1/V2 Sites"]
        B2 --> C1["Load V1/V2<br>contamination data"]
        C1 --> C2["Spatial join with<br>GVFK polygons"]
        C2 --> C3[("Site-GVFK combinations<br>~69,000 rows")]
    end

    subgraph Step4["Step 4: Distance Calculation"]
        C3 --> D1["Calculate distance<br>to nearest river"]
        D1 --> D2[("Sites with distances<br>in each GVFK")]
    end

    subgraph Step5["Step 5: Risk Assessment"]
        D2 --> E1{"Step 5a<br>≤500m?"}
        E1 -->|Yes| E2[("General risk<br>~300 GVFKs")]
        
        D2 --> E3["Step 5b: Category<br>thresholds"]
        E3 --> E4{Within category<br>threshold?}
        E4 -->|Yes| E5[("Compound risk<br>~212 GVFKs<br>~3,700 rows")]
        E4 -->|No| E6["Excluded"]

        E5 --> F1["Step 5c: Infiltration<br>filter"]
        F1 --> F2{Downward<br>flow?}
        F2 -->|Yes| F3[("Filtered sites<br>~182 GVFKs<br>~2,000 rows")]
        F2 -->|No| F4["Upward flow<br>excluded<br>~45%"]
    end

    subgraph Step6["Step 6: Tilstandsvurdering"]
        F3 --> G1["Attach infiltration<br>& calculate flux"]
        G1 --> G2["Aggregate by<br>river segment"]
        G2 --> G3["Calculate Cmix<br>per scenario"]
        G3 --> G4{"Cmix > MKK?"}
        G4 -->|Yes| G5[("MKK Exceedances<br>~101 GVFKs<br>~226 sites")]
        G4 -->|No| G6["No exceedance"]
    end

    style Step1 fill:#e1f5fe
    style Step2 fill:#b3e5fc
    style Step3 fill:#81d4fa
    style Step4 fill:#4fc3f7
    style Step5 fill:#ffcc80
    style Step6 fill:#ef9a9a
    style G5 fill:#c62828,color:#fff
```

### Key Data Files Through Workflow

```mermaid
flowchart LR
    subgraph Inputs["Input Data"]
        I1["GVFK shapefile"]
        I2["River shapefile"]
        I3["V1/V2 CSV"]
        I4["GVD rasters"]
        I5["Q-points"]
    end

    subgraph Outputs["Key Outputs"]
        O1["step5b_compound_combinations.csv"]
        O2["step5c_filtered_combinations.csv"]
        O3["step6_cmix_results.csv"]
        O4["step6_sites_mkk_exceedance.csv"]
    end

    I1 & I2 --> O1
    O1 --> O2
    I4 --> O2
    O2 & I5 --> O3
    O3 --> O4

    style O4 fill:#c62828,color:#fff
```

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Workflow Steps](#workflow-steps)
3. [Core Outputs](#core-outputs)
4. [Configuration](#configuration)
5. [Data Requirements](#data-requirements)
6. [Understanding Results](#understanding-results)
7. [Optional Analysis](#optional-analysis)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# 1. Navigate to project directory
cd "Beslutningstræ - Grundvands projekt/Kode"

# 2. Install required packages
pip install -r requirements.txt

# 3. Verify input data files exist (see Data Requirements section)
python -c "from config import validate_input_files; validate_input_files()"

# 4. Run the workflow
python main_workflow.py
```

### What Happens

The workflow runs 6 sequential steps:
1. **Step 1**: Loads all ~2,200 GVFKs in Denmark
2. **Step 2**: Filters to ~1,600 GVFKs with river contact
3. **Step 3**: Identifies contaminated sites (V1/V2) within these GVFKs
4. **Step 4**: Calculates distances from sites to rivers
5. **Step 5**: Risk assessment (three sub-steps):
   - **5a**: General assessment (universal 500m threshold)
   - **5b**: Compound-specific assessment (variable thresholds by category)
   - **5c**: Infiltration filter (removes sites in upward flow zones)
6. **Step 6**: Tilstandsvurdering (flux calculation, Cmix, MKK comparison)

Results are saved to `Resultater/` directory.

### Typical GVFK Funnel (Example Run)

| Step | Description | GVFKs | Sites | Rows |
|------|-------------|-------|-------|------|
| Step 1 | All GVFKs in Denmark | ~2,200 | — | — |
| Step 2 | River contact filter | ~1,600 | — | — |
| Step 3 | V1/V2 sites in GVFKs | ~800 | ~8,000 | ~69,000 |
| Step 5a | ≤500m threshold | ~300 | ~2,500 | — |
| Step 5b | Compound-specific thresholds | ~212 | ~1,500 | ~3,700 |
| Step 5c | Infiltration filter | ~182 | ~900 | ~2,000 |
| Step 6 | MKK exceedances | **~101** | **~226** | ~1,200 |

*Actual numbers may vary with data updates.*

---

## Workflow Steps

### Step 1: Load All Groundwater Aquifers

**Purpose:** Establish baseline count of all GVFKs in Denmark

**Input:**
- `Data/shp files/VP3Genbesøg_grundvand_geometri.shp`

**Output:**
- Console: Total GVFK count (should be ~2,044)

**What it does:**
- Reads GVFK shapefile
- Counts unique GVFKs based on 'Navn' column
- No files saved (used in memory only)

---

### Step 2: Filter to GVFKs with River Contact

**Purpose:** Identify GVFKs where groundwater interacts with surface water

**Input:**
- `Data/shp files/Rivers_gvf_rev20230825_kontakt.shp`

**Output:**
- `Resultater/step2_gvfk_with_rivers.shp` (shapefile for GIS visualization)

**What it does:**
- Filters river segments where `Kontakt = 1` (groundwater-surface water interaction)
- Extracts unique GVFK names from river contact data
- Filters GVFK shapefile to only those with river contact
- Result: ~1,600 GVFKs with river contact (~78% of total)

**Configuration:**
- `SETTINGS.yaml`: `contact_filter_value: 1` (change if using different contact criteria)

---

### Step 3: Identify Contaminated Sites in GVFKs

**Purpose:** Find V1/V2 contaminated sites within GVFKs that have river contact

**Input:**
- `Data/v1_gvfk_forurening.csv` (V1 contamination data)
- `Data/v2_gvfk_forurening.csv` (V2 contamination data)
- `Data/shp files/V1FLADER.shp` (V1 site geometries)
- `Data/shp files/V2FLADER.shp` (V2 site geometries)

**Output:**
- `Resultater/step3_v1v2_sites.shp` (contaminated sites shapefile)
- `Resultater/step3_gvfk_with_v1v2.shp` (GVFK polygons with sites)

**What it does:**
- Loads V1 and V2 contamination data (site IDs, contamination info, GVFK associations)
- Filters to sites in GVFKs with river contact (from Step 2)
- Loads site geometries and performs spatial join
- Creates site-GVFK combinations (one site can affect multiple GVFKs)
- Result: ~8,000-10,000 unique contaminated sites in ~800 GVFKs

**Important:**
- Uses spatial overlay to associate sites with GVFKs
- One site can appear in multiple GVFKs (multi-GVFK approach)
- Dissolved geometries are cached for performance

---

### Step 4: Calculate Distances to Rivers

**Purpose:** Determine how far each contaminated site is from the nearest river segment

**Input:**
- V1/V2 sites from Step 3
- River geometries (with contact data)

**Output:**
- `Resultater/step4_final_distances.csv` (clean site-GVFK-distance combinations)
- `Resultater/step4_valid_distances.csv` (all combinations before deduplication)
- `Resultater/unique_lokalitet_distances.csv` (one distance per site)
- `Resultater/unique_lokalitet_distances.shp` (site geometries with distances)

**What it does:**
- For each site-GVFK combination:
  1. Finds all river segments in that GVFK
  2. Calculates distance to nearest river segment
  3. Records distance in meters
- Handles multi-GVFK sites correctly (each site-GVFK pair gets its own distance)
- Result: ~69,000 site-GVFK combinations with distances

**File Descriptions:**
- `step4_final_distances.csv`: **Use this for risk assessment** (input to Step 5)
- `unique_lokalitet_distances.shp`: **Use this for GIS mapping** (one point per site)

---

### Step 5: Risk Assessment

**Purpose:** Identify high-risk sites using distance-based thresholds

Two parallel assessments are performed:

#### Step 5a: General Assessment (Universal 500m Threshold)

**Threshold:** All sites ≤500m from rivers are flagged as high-risk

**Output:**
- `Resultater/step5_high_risk_sites_500m.csv` (high-risk sites)
- `Resultater/step5_gvfk_high_risk_500m.shp` (affected GVFK polygons)

**What it does:**
- Applies universal 500m threshold to ALL site-GVFK combinations with qualifying data (substance or landfill keywords)
- Sites WITHOUT qualifying data are "parked" for later analysis
- Result: ~2,500 high-risk sites in ~300 GVFKs

**Use case:** Conservative approach, captures all potentially risky sites

---

#### Step 5b: Compound-Specific Assessment (Variable Thresholds)

**Thresholds:** Literature-based distances varying by contamination category

**Output:**
- `Resultater/step5_compound_detailed_combinations.csv` (all site-GVFK-substance combinations meeting thresholds)
- `Resultater/step5_compound_gvfk_high_risk.shp` (affected GVFK polygons)
- `Resultater/step5_unknown_substance_sites.csv` (parked sites without substance data)

**What it does:**
- Categorizes each contamination substance into 11 literature-based categories
- Applies category-specific distance threshold:
  - **PAH compounds:** 30m (low mobility, high sorption)
  - **BTXER (benzene, oils):** 50m
  - **Phenols:** 100m
  - **Chlorinated solvents:** 500m (high mobility)
  - **Pesticides:** 500m
  - **Landfill sites (LOSSEPLADS):** Category-specific override thresholds
  - **Others:** See `risikovurdering/refined_compound_analysis.py`
- Preserves **multi-GVFK associations** (one site can affect multiple GVFKs with different substances)
- Result: ~1,740 unique sites in ~240 GVFKs with ~4,500 site-GVFK-substance combinations

**Use case:** Risk-based approach accounting for contaminant mobility

**Category Definitions:**
See `risikovurdering/refined_compound_analysis.py` for:
- LITERATURE_COMPOUND_MAPPING: Category names, keywords, distance thresholds, literature basis
- COMPOUND_SPECIFIC_DISTANCES: Individual compound overrides (e.g., benzene: 200m)

---

#### Step 5c: Infiltration Filter (Groundwater Flow Direction)

**Purpose:** Remove sites in upward groundwater flow zones (opstrømningszoner)

**Input:**
- Step 5b output: `step5b_compound_combinations.csv`
- GVD rasters: `Data/dkm2019_vp3_GVD/` (infiltration rate grids)

**Output:**
- `Resultater/step5c_filtered_combinations.csv` (sites with downward flow only)
- `Resultater/Figures/step5c/upward_flux_sites_map.html` (interactive map)

**What it does:**
- For each site polygon, samples all pixels from the infiltration raster
- Converts pixel values to binary: **<0 = upward flow**, **≥0 = downward flow**
- Applies **pixel-level majority voting**: if >50% of pixels are upward, site is removed
- Conservatively keeps sites with `no_data` pixels
- Typical reduction: ~45% rows filtered, ~40% sites removed

**Scientific basis:**
The flux formula `J = A × C × I` assumes groundwater flows downward toward the aquifer. In upward flow zones (discharge areas), contamination does not reach the aquifer via infiltration, so these sites are excluded from risk assessment.

---

### Step 6: Tilstandsvurdering (Flux & Cmix Calculation)

**Purpose:** Calculate pollution fluxes and compare mixed concentration (Cmix) to environmental quality standards (MKK)

**Input:**
- Step 5c filtered data (via alias `step5_compound_detailed_combinations`)
- Site geometries from Step 3
- GVFK-to-modellag mapping
- GVD infiltration rasters
- River flow data (Q-points with Mean/Q90/Q95)
- MKK thresholds from `config.py`

**Output:**
| File | Description |
|------|-------------|
| `step6_flux_site_segment.csv` | Per-site flux values before segment aggregation |
| `step6_cmix_results.csv` | Segment-level Cmix with MKK exceedance flags |
| `step6_segment_summary.csv` | Per-segment summary with max Cmix and failing scenarios |
| `step6_sites_mkk_exceedance.csv` | Sites contributing to MKK exceedances |
| `step6_filtering_audit_detailed.csv` | Audit trail of filtered rows (missing data, etc.) |

**What it does:**

1. **Attach infiltration**: Sample GVD rasters for each site based on DK-modellag
2. **Calculate flux**: `J = Area × Infiltration × Concentration`
   - Scenario-based: Each category generates multiple flux rows (one per modelstof)
   - Example: BTXER → 2 scenarios (Benzen @ 400 µg/L, Olie @ 3000 µg/L)
3. **Aggregate by river segment**: Sum fluxes per scenario per segment
4. **Calculate Cmix**: `Cmix = Flux / (Q × 1000)` for each flow scenario (Mean/Q90/Q95)
5. **Apply MKK thresholds**: Compare Cmix to substance or category MKK
6. **Flag exceedances**: Identify segments and sites exceeding environmental limits

**Data filtering:**
- Sites with missing modellag mapping: removed
- Sites with negative infiltration (upward flow): quarantined
- Rows with concentration = -1 (LOSSEPLADS/ANDRE/PFAS without overrides): filtered

**Typical results:** ~100-150 GVFKs with MKK exceedances, affecting 200-300 sites

See `README_STEP6.md` for detailed examples and technical notes.

---

## Core Outputs

All results are saved to `Resultater/` directory:

### CSV Files (Data Tables)

| File | Description | Use |
|------|-------------|-----|
| `step4_final_distances.csv` | Site-GVFK combinations with distances | Input to risk assessment |
| `step5_high_risk_sites_500m.csv` | High-risk sites (general 500m threshold) | Conservative risk list |
| `step5_compound_detailed_combinations.csv` | Site-GVFK-substance combinations (compound-specific) | **Primary risk assessment output** |
| `step5_unknown_substance_sites.csv` | Sites without substance data (parked) | Requires further investigation |
| `workflow_summary.csv` | GVFK/site counts per step | Quick overview |

### Shapefiles (GIS Visualization)

| File | Description | Use |
|------|-------------|-----|
| `step2_gvfk_with_rivers.shp` | GVFKs with river contact | Workflow progression |
| `step3_v1v2_sites.shp` | Contaminated site locations | Site mapping |
| `step3_gvfk_with_v1v2.shp` | GVFKs containing sites | Workflow progression |
| `step5_gvfk_high_risk_500m.shp` | High-risk GVFKs (general assessment) | Conservative risk mapping |
| `step5_compound_gvfk_high_risk.shp` | High-risk GVFKs (compound-specific) | **Primary risk mapping** |
| `unique_lokalitet_distances.shp` | Site geometries with distances | Distance visualization |

### Verification Plots

Saved to `Resultater/Figures/step5/`:

1. **step5a_distance_distribution.png**
   - Histogram of site distances
   - Shows 500m threshold line
   - Verifies distance calculations

2. **step5b_category_breakdown.png**
   - Bar chart of contamination categories
   - Shows number of site-GVFK-substance combinations per category
   - Verifies categorization logic

3. **workflow_gvfk_progression.png**
   - GVFK count through Steps 1-5
   - Shows filtering effectiveness
   - Quick sanity check

---

## Configuration

### User Settings: SETTINGS.yaml

Edit this file to modify workflow behavior:

```yaml
# Universal distance threshold (meters)
risk_threshold_m: 500

# River contact filter value
contact_filter_value: 1

# Enable/disable sensitivity analysis
enable_multi_threshold_analysis: false
```

### Data Paths: config.py

Defines locations of all input/output files. Modify if data is in different location:

```python
# Input data
GRUNDVAND_PATH = SHAPE_DIR / "VP3Genbesøg_grundvand_geometri.shp"
RIVERS_PATH = SHAPE_DIR / "Rivers_gvf_rev20230825_kontakt.shp"
V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening.csv"
V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening.csv"

# Output files (organized by step)
CORE_OUTPUTS = {...}  # Core workflow outputs
OPTIONAL_OUTPUTS = {...}  # Extended analysis outputs
```

### Compound Thresholds: refined_compound_analysis.py

**DO NOT modify without scientific justification.**

Literature-based thresholds are documented with sources. To modify:

1. Review `LITERATURE_COMPOUND_MAPPING` dictionary
2. Document literature source for any changes
3. Update both distance_m and description fields

---

## Data Requirements

### Required Input Files

Place all data files in `Data/` directory with this structure:

```
Data/
├── shp files/
│   ├── VP3Genbesøg_grundvand_geometri.shp  (GVFK polygons)
│   ├── Rivers_gvf_rev20230825_kontakt.shp  (River segments with contact data)
│   ├── V1FLADER.shp                        (V1 site geometries)
│   └── V2FLADER.shp                        (V2 site geometries)
├── v1_gvfk_forurening.csv                  (V1 contamination data)
├── v2_gvfk_forurening.csv                  (V2 contamination data)
└── volumen areal_genbesøg.csv              (GVFK area/volume data - optional)
```

### File Validation

Before running workflow:

```python
python -c "from config import validate_input_files; validate_input_files()"
```

Missing files will be listed with expected locations.

---

## Understanding Results

### Multi-GVFK Approach (IMPORTANT!)

**Key Concept:** One contaminated site can affect multiple GVFKs.

**Why?**
- Sites near GVFK boundaries can impact multiple aquifers
- Contamination doesn't respect administrative boundaries
- Conservative approach: assess risk to ALL potentially affected GVFKs

**Example:**
- Site A is 300m from river
- Site A borders both GVFK_1 and GVFK_2
- Result: Site A creates TWO site-GVFK combinations
  - Site_A + GVFK_1 (300m to river in GVFK_1)
  - Site_A + GVFK_2 (320m to river in GVFK_2)

**Implications:**
- `step5_compound_detailed_combinations.csv` has MORE rows than unique sites
- Each row is a unique **site-GVFK-substance** combination
- When counting GVFKs, use this file (preserves all associations)
- When counting unique sites, deduplicate by Lokalitet_ID

---

### Interpreting Step 5b Results

**File:** `step5_compound_detailed_combinations.csv`

**Columns:**
- `Lokalitet_ID`: Site identifier
- `GVFK`: Groundwater aquifer name
- `Kontaminering`: Original contamination text
- `Qualifying_Category`: Assigned contamination category
- `Category_Threshold_m`: Distance threshold for this category
- `Distance_to_River_m`: Calculated distance
- `Final_Distance_m`: Distance used for assessment

**How to Use:**
1. **Count affected GVFKs:** `nunique()` on GVFK column → ~240 GVFKs
2. **Count unique sites:** `nunique()` on Lokalitet_ID → ~1,740 sites
3. **Total combinations:** `len()` → ~4,500 site-GVFK-substance triplets
4. **Filter by category:** Group by Qualifying_Category to see distribution

**Example Analysis:**

```python
import pandas as pd

# Load results
df = pd.read_csv("Resultater/step5_compound_detailed_combinations.csv")

# Summary statistics
print(f"Unique sites: {df['Lokalitet_ID'].nunique():,}")
print(f"Affected GVFKs: {df['GVFK'].nunique()}")
print(f"Total combinations: {len(df):,}")

# Category breakdown
category_counts = df.groupby('Qualifying_Category').size().sort_values(ascending=False)
print("\nTop categories:")
print(category_counts.head())

# GVFKs by category
for category in ['KLOREREDE_OPLØSNINGSMIDLER', 'LOSSEPLADS', 'BTXER']:
    gvfk_count = df[df['Qualifying_Category'] == category]['GVFK'].nunique()
    print(f"{category}: {gvfk_count} GVFKs")
```

---

## Optional Analysis

Extended analysis tools are available in `risikovurdering/optional_analysis/` but are **NOT part of the standardized workflow**.

### Available Tools

1. **step5_branch_analysis.py** (2,178 lines)
   - Analyzes sites WITHOUT substance data
   - Compares against Step 5a general assessment
   - Industry/activity frequency analysis
   - Run: `python -m risikovurdering.optional_analysis.step5_branch_analysis`

2. **step6_risikovurdering_analysis.py** (2,312 lines)
   - Final comprehensive analysis
   - Core vs expanded scenario comparison
   - 20+ visualizations (heatmaps, choropleths, etc.)
   - Run: `python -m risikovurdering.optional_analysis.step6_risikovurdering_analysis`

3. **selected_visualizations.py** (1,551 lines)
   - Publication-quality plots
   - Advanced distance histograms
   - HTML tables for PowerPoint
   - Import specific functions as needed

4. **create_interactive_map.py** (279 lines)
   - Leaflet-based interactive maps
   - Web visualization for stakeholders
   - Run: `python -m risikovurdering.optional_analysis.create_interactive_map`

See `risikovurdering/optional_analysis/README.md` for details.

---

## Troubleshooting

### Common Issues

#### "Missing required input files"

**Problem:** Workflow cannot find data files

**Solution:**
1. Check file paths in config.py
2. Ensure data is in correct directory structure
3. Run validation: `python -c "from config import validate_input_files; validate_input_files()"`

---

#### "KeyError: 'GVFK'" or column name errors

**Problem:** Expected columns not found in data

**Solution:**
- V1/V2 CSV files must have: `Lokalitetsnr`, `GVFKnavn`, `Kontaminering`
- GVFK shapefile must have: `Navn` column
- River shapefile must have: `Kontakt`, `GVForekom` columns

---

#### "Step 3 found no V1/V2 sites"

**Problem:** No sites matched with GVFKs

**Solution:**
1. Check that V1/V2 CSV files contain data
2. Verify GVFK names match between datasets
3. Ensure shapefile geometries are valid

---

#### Distance calculations seem wrong

**Problem:** Unexpected distance values

**Solution:**
1. Check coordinate systems (should be EPSG:25832 for Denmark)
2. Verify geometries are valid (no NULL geometries)
3. Review `Resultater/Figures/step5/step5a_distance_distribution.png`

---

#### Wrong number of GVFKs in Step 5b

**Problem:** GVFK count doesn't match expectations

**Solution:**
- Use `step5_compound_detailed_combinations.csv` (preserves multi-GVFK)
- Count: `df['GVFK'].nunique()` NOT `df['Lokalitet_ID'].nunique()`
- Multi-GVFK approach means more combinations than unique sites

---

### Performance

**Slow Step 3:**
- First run creates dissolved geometry cache
- Subsequent runs use cache (much faster)
- Cache location: `Resultater/cache/`

**Slow Step 4:**
- Distance calculation is computationally intensive
- ~69,000 site-GVFK combinations to process
- Expected: 5-10 minutes depending on hardware

---

### Getting Help

1. Check this README
2. Review code docstrings (all functions documented)
3. Check `risikovurdering/optional_analysis/README.md` for extended analysis
4. Review SETTINGS.yaml comments for configuration options

---

## Technical Details

### Software Requirements

- Python 3.8+
- See `requirements.txt` for package versions

### Core Dependencies

- **geopandas:** Spatial operations, shapefiles
- **pandas:** Data manipulation
- **shapely:** Geometry operations
- **matplotlib:** Visualizations
- **pyyaml:** Configuration loading

### Project Structure

```
Kode/
├── main_workflow.py                  # Main orchestrator (run this)
├── config.py                         # Configuration and paths
├── SETTINGS.yaml                     # User-editable settings
├── requirements.txt                  # Python dependencies
│
├── risikovurdering/                  # Core workflow modules
│   ├── step1_all_gvfk.py            # Load all GVFKs
│   ├── step2_river_contact.py       # Filter by river contact
│   ├── step3_v1v2_sites.py          # Identify contaminated sites
│   ├── step4_distances.py           # Calculate distances
│   ├── step5_risk_assessment.py     # Risk assessment (5a + 5b)
│   ├── step5_utils.py               # Utility functions
│   ├── step5_analysis.py            # Summary functions
│   ├── step5_visualizations.py      # Essential plots (3 charts)
│   ├── compound_matching.py         # Categorization logic
│   └── refined_compound_analysis.py # Category definitions
│
└── risikovurdering/optional_analysis/
    ├── README.md                     # Extended analysis guide
    ├── step5_branch_analysis.py     # Branch-only site analysis
    ├── step6_risikovurdering_analysis.py  # Comprehensive analysis
    ├── selected_visualizations.py   # Advanced plots
    └── create_interactive_map.py    # Interactive web maps
```

---

## Methodology References

### Distance Thresholds

Compound-specific thresholds are based on:
- Regulatory distance tables (Danish EPA)
- Scientific literature on contaminant mobility
- Groundwater transport modeling studies

See `risikovurdering/refined_compound_analysis.py` for specific citations in each category's `literature_basis` field.

### Multi-GVFK Approach

Sites near GVFK boundaries can impact multiple aquifers. This conservative approach:
- Assesses risk to ALL potentially affected GVFKs
- Preserves site-GVFK associations through workflow
- Prevents loss of data through premature deduplication

**Key Implementation:**
- Step 3 creates site-GVFK combinations (spatial overlay)
- Step 4 calculates distance for each combination separately
- Step 5b preserves combinations as site-GVFK-substance triplets
- GVFK counts must be calculated from detailed combinations, not deduplicated sites

---

## Version History

**v1.0 - Standardized Core Workflow**
- Cleaned and documented core Steps 1-5
- Separated optional analysis to dedicated folder
- Streamlined visualizations (3 essential plots)
- Added SETTINGS.yaml for user configuration
- Comprehensive README documentation

---

## License & Contact

Internal tool for groundwater risk assessment.

For questions about methodology, contact project team.
