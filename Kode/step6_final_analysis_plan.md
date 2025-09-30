# Step 6: Final Comprehensive Analysis Plan

## Overview
Compare **Core scenario** (214 GVFKs with 1,711 substance sites) vs **Expanded scenario** (258 GVFKs with 1,711 substance sites + 3,600 branch-only sites).

**Key insight:** The 258 GVFKs consist of:
- **170 "Shared" GVFKs**: Contain BOTH substance sites AND branch-only sites
- **44 "New" GVFKs**: Contain ONLY branch-only sites (no substance sites)
- **44 "Substance-only" GVFKs**: Contain ONLY substance sites (no branch-only sites ≤500m)

---

## Data Sources

### Input Files
1. **GVFK Area/Volume Data:**
   - `Data\volumen areal_genbesøg.csv`
   - Columns: `GVFK`, `Areal [km2]`, `Volumen`

2. **Substance Sites (Core - 1,711 sites, 214 GVFKs):**
   - `Resultater\step5_compound_specific_sites.csv`
   - Columns: `Lokalitet_ID`, `Closest_GVFK`, `Lokalitetensbranche`, `Lokalitetensaktivitet`, etc.

3. **Branch-only Sites (3,600 sites, 258 GVFKs total with 44 "new"):**
   - `Resultater\step5_unknown_substance_sites.csv`
   - Filter: `Final_Distance_m <= 500` AND NOT losseplads
   - Columns: `Lokalitet_ID`, `Closest_GVFK`, `Lokalitetensbranche`, `Lokalitetensaktivitet`

4. **GVFK Shapefiles (for geographic analysis):**
   - All Denmark: `Data\Grundvandsforekomster\DK_GVFK.shp` (2,043 GVFKs)
   - Step 2: `Resultater\step2_river_gvfk.gpkg` (593 GVFKs)
   - Step 3: `Resultater\step3_gvfk_polygons.gpkg` (491 GVFKs)
   - Step 5b: Filter to 214 GVFKs from substance sites
   - Step 5b+: Filter to 258 GVFKs from substance + branch sites

### Output Structure
```
Resultater/
  Step6_Final_Analysis/
    Figures/
      01_gvfk_progression_count.png
      02_gvfk_progression_area_volume.png
      03_industry_comparison_3way.png
      04_activity_comparison_3way.png
      05_overlap_analysis.png
      06_hexagonal_heatmap_comparison.png
      07_gvfk_choropleth_comparison.png
      08_geographic_distribution.png
    Tables/
      gvfk_progression_metrics.csv
      industry_comparison_table.csv
      activity_comparison_table.csv
      new_44_gvfk_characteristics.csv
```

---

## PHASE 1: Data Preparation & Loading

### 1.1 Load GVFK Area/Volume Data
- Load `volumen areal_genbesøg.csv`
- Note: Decimal separator is comma (`,`) - convert to float
- Parse columns: `GVFK`, `Areal [km2]`, `Volumen`
- Create lookup dictionary: `{gvfk_name: {'area': X, 'volume': Y}}`

### 1.2 Load Substance Sites (Core scenario)
- Load `step5_compound_specific_sites.csv`
- Count: Should be ~1,711 unique sites
- Extract unique GVFKs: Should be ~214 GVFKs
- Store as `substance_sites_df`

### 1.3 Load and Filter Branch-only Sites
- Load `step5_unknown_substance_sites.csv`
- Apply filters:
  - `Final_Distance_m <= 500`
  - Exclude losseplads: `Lokalitetensbranche` NOT containing "Losseplads" OR "losseplads"
- Count: Should be ~3,600 sites
- Extract unique GVFKs: Should be ~258 GVFKs total
- Store as `branch_only_sites_df`

### 1.4 Categorize GVFKs
```python
substance_gvfks = set(substance_sites_df['Closest_GVFK'].unique())  # 214
branch_gvfks = set(branch_only_sites_df['Closest_GVFK'].unique())   # 258

# Categorize
shared_gvfks = substance_gvfks & branch_gvfks  # 170 GVFKs with both
new_44_gvfks = branch_gvfks - substance_gvfks  # 44 GVFKs with only branch-only
substance_only_gvfks = substance_gvfks - branch_gvfks  # 44 GVFKs with only substance

# Verify: 170 + 44 = 214 (substance total)
#         170 + 44 = 214 + 44 = 258 (expanded total)
```

### 1.5 Filter Sites by GVFK Category
```python
# Sites in the 44 "new" GVFKs only
sites_in_new_44_gvfks = branch_only_sites_df[
    branch_only_sites_df['Closest_GVFK'].isin(new_44_gvfks)
]

# Sites in the 170 "shared" GVFKs only
branch_sites_in_shared = branch_only_sites_df[
    branch_only_sites_df['Closest_GVFK'].isin(shared_gvfks)
]
substance_sites_in_shared = substance_sites_df[
    substance_sites_df['Closest_GVFK'].isin(shared_gvfks)
]
```

### 1.6 Load GVFK Shapefiles for Geographic Analysis
- Load all Denmark GVFKs
- Load Step 2, 3 GVFKs for progression
- Filter to 214, 258 GVFKs for final analysis

---

## PHASE 2: GVFK Progression Metrics (Count, Area, Volume)

### 2.1 Calculate Metrics for Each Step

For each workflow step, calculate:
- **Count**: Number of unique GVFKs
- **Total Area (km²)**: Sum of GVFK areas (overlaps counted)
- **Total Volume (m³)**: Sum of GVFK volumes (overlaps counted)

**Steps to analyze:**
1. **Step 1**: All Denmark (2,043 GVFKs)
2. **Step 2**: River contact (593 GVFKs)
3. **Step 3**: V1/V2 sites (491 GVFKs)
4. **Step 5a**: General assessment ≤500m (load `step5_high_risk_sites.csv` if available)
5. **Step 5b (Core)**: Substance sites only (214 GVFKs)
6. **Step 5b+ (Expanded)**: Substance + Branch-only (258 GVFKs)

### 2.2 Breakdown for Step 5b+
Show contribution of the 44 "new" GVFKs:
- Area contributed by 44 new GVFKs
- Volume contributed by 44 new GVFKs
- Sites in 44 new GVFKs vs 170 shared GVFKs

### 2.3 Visualizations

**Chart 1: GVFK Count Progression**
- X-axis: Workflow steps (Step 1 → Step 5b+)
- Y-axis: GVFK count
- Bar chart with values labeled
- Special treatment for Step 5:
  - Step 5b (Core): 214 GVFKs (solid blue)
  - Step 5b+ (Expanded): 214 + 44 = 258 GVFKs
    - Stacked bar: 214 blue + 44 orange

**Chart 2: Area & Volume Progression**
- Dual-axis chart:
  - Left Y-axis: Total Area (km²)
  - Right Y-axis: Total Volume (m³)
- X-axis: Workflow steps
- Two line plots or grouped bars
- Highlight contribution of +44 GVFKs at Step 5b+

**Table 1: Detailed Progression Metrics**
```
Step   | Description                  | GVFKs | Area (km²) | Volume (m³) | % of DK
-------|------------------------------|-------|------------|-------------|--------
Step 1 | All Denmark                  | 2,043 | X          | Y           | 100%
Step 2 | River contact                | 593   | X₂         | Y₂          | Z%
Step 3 | V1/V2 sites                  | 491   | X₃         | Y₃          | Z%
Step 5a| General ≤500m                | ???   | X₄         | Y₄          | Z%
Step 5b| Substance sites (Core)       | 214   | X₅         | Y₅          | Z%
+44    | Additional from branch-only  | 44    | ΔX         | ΔY          | Δ%
Step 5b+| Expanded (Substance+Branch) | 258   | X₅+ΔX      | Y₅+ΔY       | Z%
```

**Table 2: Contribution Analysis**
```
Metric                          | Core (214) | +44 New  | Expanded (258) | % Change
--------------------------------|------------|----------|----------------|----------
GVFK Count                      | 214        | +44      | 258            | +20.6%
Total Area (km²)                | X          | +Z       | X+Z            | +??%
Total Volume (m³)               | Y          | +W       | Y+W            | +??%
Sites                           | 1,711      | +X sites | 1,711+X        | +??%
Sites in new 44 GVFKs           | 0          | X        | X              | -
Sites in shared 170 GVFKs       | 1,711      | (3,600-X)| 1,711+(3,600-X)| +??%
Avg sites per GVFK              | 8.0        | X/44     | Total/258      | +??%
```

---

## PHASE 3: Branch/Activity Comparison Analysis

**Important:** Both `Lokalitetensbranche` and `Lokalitetensaktivitet` contain semicolon-separated values (e.g., "Auto;Gas;Repair").
- Split by `;` and count **occurrences** (not unique sites)
- A site with "Auto;Gas" contributes 1 occurrence to Auto AND 1 to Gas

### 3.1 Define Three Comparison Groups

**Group A: Substance Sites (1,711 sites across 214 GVFKs)**
- All 1,711 substance sites
- Extract branches and activities

**Group B: All Branch-only Sites (3,600 sites across 258 GVFKs)**
- All 3,600 branch-only sites (≤500m, no losseplads)
- Extract branches and activities

**Group C: Branch-only Sites in "New 44" GVFKs ONLY**
- Filter `branch_only_sites_df` to sites where `Closest_GVFK` in `new_44_gvfks`
- This is a **subset** of Group B
- Extract branches and activities

### 3.2 Extract and Count Branches/Activities

For each group, count occurrences:

```python
def count_occurrences(df, column_name):
    """Count occurrences from semicolon-separated column."""
    all_items = []
    for value in df[column_name].dropna():
        items = [item.strip() for item in str(value).split(';') if item.strip()]
        all_items.extend(items)

    return pd.Series(all_items).value_counts()

# For each group
branches_A = count_occurrences(substance_sites_df, 'Lokalitetensbranche')
activities_A = count_occurrences(substance_sites_df, 'Lokalitetensaktivitet')

branches_B = count_occurrences(branch_only_sites_df, 'Lokalitetensbranche')
activities_B = count_occurrences(branch_only_sites_df, 'Lokalitetensaktivitet')

branches_C = count_occurrences(sites_in_new_44_gvfks, 'Lokalitetensbranche')
activities_C = count_occurrences(sites_in_new_44_gvfks, 'Lokalitetensaktivitet')
```

### 3.3 Overlap Analysis

**For Branches:**
- Total unique branches in each group
- Common branches across all groups
- Unique to Group A (substance only)
- Unique to Group C (new 44 GVFKs only)
- Overlap percentage

**For Activities:**
- Same analysis as branches

### 3.4 Visualizations

**Chart 3: Three-way Industry Comparison (Horizontal Bar Chart)**
```
                        Group A (1,711)  |  Group B (3,600)  |  Group C (X in new 44)
Industry 1              ████████████     |  ██████████       |  ████
                        (N occurrences)  |  (M occurrences)  |  (P occurrences)
Industry 2              ██████           |  ████████         |  ██████
...
Top 10 industries
```
- Show top 10 industries by total occurrences across all groups
- Side-by-side bars for comparison
- Color coding: Blue (Substance), Orange (All Branch), Red (New 44 only)

**Chart 4: Three-way Activity Comparison (Horizontal Bar Chart)**
- Same format as Chart 3, but for activities

**Chart 5: Overlap Analysis (Venn-style visualization or table)**
```
Branch/Activity Overlap Analysis

                                    | Branches | Activities
------------------------------------|----------|------------
Total unique in Group A (Substance) | N        | M
Total unique in Group B (All Branch)| P        | Q
Total unique in Group C (New 44)    | R        | S
Common to A & C                     | X        | Y
Unique to C only                    | Z        | W
Overlap % (C with A)                | ??%      | ??%
```

**Table 3: Group Characteristics Summary**
```
Metric                          | Group A (Substance) | Group B (All Branch) | Group C (New 44 only)
--------------------------------|---------------------|----------------------|----------------------
Total sites                     | 1,711               | 3,600                | X
GVFKs                           | 214                 | 258                  | 44
Unique branches                 | N                   | M                    | P
Unique activities               | N                   | M                    | P
Total branch occurrences        | X                   | Y                    | Z
Total activity occurrences      | X                   | Y                    | Z
Top branch                      | [name] (X occ.)     | [name] (Y occ.)      | [name] (Z occ.)
Top activity                    | [name] (X occ.)     | [name] (Y occ.)      | [name] (Z occ.)
High-risk industries (estimate) | X%                  | Y%                   | Z%
```

**Table 4: Top 10 Branches - Three-way Comparison**
```
Rank | Branch Name                  | Group A (occ.) | Group B (occ.) | Group C (occ.)
-----|------------------------------|----------------|----------------|----------------
1    | Servicestationer             | X              | Y              | Z
2    | Autoreparation               | X              | Y              | Z
...
```

**Table 5: Top 10 Activities - Three-way Comparison**
- Same format as Table 4

---

## PHASE 4: Geographic Distribution Analysis

### 4.1 Hexagonal Heatmap - Site Density

**Purpose:** Show spatial distribution and density of contamination sites

**Method:**
- Create hexagonal grid over Denmark
- Count sites falling within each hexagon
- Color hexagons by site count (darker = more sites)

**Two side-by-side maps:**

**Map 1: Core Scenario (1,711 substance sites)**
- Only substance sites
- Shows current "confirmed contamination" hotspots

**Map 2: Expanded Scenario (5,311 total sites)**
- 1,711 substance + 3,600 branch-only
- Shows potential risk if branch-only sites included

**Parameters:**
- Hexagon size: ~5-10 km diameter (adjust based on Denmark size)
- Color scale: Sequential (light blue → dark blue)
- Include base map of Denmark outline
- Add GVFK boundaries (light gray)

### 4.2 GVFK Choropleth Maps - Color by Site Count

**Purpose:** Show which GVFKs are affected and their site density

**Map 3: Core Scenario (214 GVFKs)**
- Color GVFKs by number of substance sites
- Color scale: White (1 site) → Dark Blue (max sites)
- Overlay site locations as points

**Map 4: Expanded Scenario (258 GVFKs)**
- Color GVFKs by total site count (substance + branch-only)
- **Key visual distinction:**
  - **170 "Shared" GVFKs**: Solid fill, color by site count
  - **44 "New" GVFKs**: Hatched/striped pattern + distinct border (thick red/orange)
  - **44 "Substance-only" GVFKs**: (not shown in this map, only in Core map)
- Legend:
  - Color gradient for site count
  - Pattern explanation: "New GVFKs from branch-only sites"

**Side-by-side comparison:**
```
    CORE (214 GVFKs)              |        EXPANDED (258 GVFKs)
    1,711 substance sites          |    5,311 total sites
    [Blue gradient by count]       |    [Blue solid for 170 shared]
                                   |    [Orange hatched for 44 new]
```

### 4.3 Geographic Distribution Tables

**Table 6: Regional Distribution**
```
Region                  | Core (214)     | Expanded (258)  | Change
                        | GVFKs | Sites | GVFKs | Sites   | GVFKs | Sites
------------------------|-------|-------|-------|---------|-------|-------
Region Hovedstaden      | X     | Y     | X+?   | Y+?     | +?    | +?
Region Sjælland         | X     | Y     | X+?   | Y+?     | +?    | +?
Region Syddanmark       | X     | Y     | X+?   | Y+?     | +?    | +?
Region Midtjylland      | X     | Y     | X+?   | Y+?     | +?    | +?
Region Nordjylland      | X     | Y     | X+?   | Y+?     | +?    | +?
------------------------|-------|-------|-------|---------|-------|-------
TOTAL                   | 214   | 1,711 | 258   | 5,311   | +44   | +3,600
```

**Table 7: Top Municipalities by Site Count**
```
Municipality        | Core Sites | Expanded Sites | Change | New GVFKs in Municipality
--------------------|------------|----------------|--------|---------------------------
København           | X          | Y              | +Z     | N
Aarhus              | X          | Y              | +Z     | N
...
```

**Table 8: Characteristics of the 44 "New" GVFKs**
```
GVFK Name   | Area (km²) | Volume (m³) | Sites | Top Branch        | Top Activity
------------|------------|-------------|-------|-------------------|------------------
dkm_xxxx_ks | X.XX       | Y           | N     | [branch name]     | [activity name]
...
```
- List all 44 new GVFKs
- Show their physical characteristics
- Show what sites they contain

---

## PHASE 5: Summary & Exports (OPTIONAL - SKIPPED FOR NOW)

Keep this placeholder for potential future dashboard/executive summary.

---

## Implementation Notes

### Code Structure
Create `step6_final_analysis.py` with modular functions:

```python
# Phase 1: Data Loading
def load_gvfk_area_volume():
    """Load and parse GVFK area/volume data."""
    pass

def load_substance_sites():
    """Load Step 5b substance sites."""
    pass

def load_and_filter_branch_sites():
    """Load and filter branch-only sites (≤500m, no losseplads)."""
    pass

def categorize_gvfks(substance_gvfks, branch_gvfks):
    """Categorize into shared, new, substance-only."""
    pass

# Phase 2: GVFK Progression
def calculate_gvfk_metrics(gvfk_list, gvfk_area_volume_dict):
    """Calculate count, total area, total volume for a list of GVFKs."""
    pass

def create_progression_visualizations():
    """Create count, area/volume progression charts."""
    pass

# Phase 3: Branch/Activity Analysis
def count_occurrences(df, column_name):
    """Count occurrences from semicolon-separated values."""
    pass

def analyze_three_groups(substance_df, all_branch_df, new_44_branch_df):
    """Compare branches/activities across three groups."""
    pass

def create_comparison_visualizations():
    """Create 3-way comparison charts."""
    pass

# Phase 4: Geographic Analysis
def create_hexagonal_heatmap(sites_df, title):
    """Create hexagonal heatmap for site density."""
    pass

def create_gvfk_choropleth(gvfk_gdf, site_counts, new_44_gvfks):
    """Create choropleth map with special highlighting for new 44."""
    pass

# Main execution
def run_step6_analysis():
    """Run all phases sequentially."""
    # Phase 1: Load data
    # Phase 2: GVFK progression
    # Phase 3: Branch/activity comparison
    # Phase 4: Geographic analysis
    # Save all outputs
    pass

if __name__ == "__main__":
    run_step6_analysis()
```

### Key Technical Details

**Decimal parsing for Danish CSV:**
```python
# Area/volume file uses comma as decimal separator
df = pd.read_csv(filepath, sep=';', decimal=',')
df['Areal [km2]'] = df['Areal [km2]'].astype(float)
df['Volumen'] = df['Volumen'].astype(float)
```

**Semicolon-separated parsing:**
```python
# Split and flatten
all_items = []
for value in df['Lokalitetensbranche'].dropna():
    items = [item.strip() for item in str(value).split(';') if item.strip()]
    all_items.extend(items)

occurrence_counts = pd.Series(all_items).value_counts()
```

**GVFK map styling:**
```python
# For the 44 new GVFKs - hatched pattern
from matplotlib.patches import Patch
import matplotlib.patches as mpatches

# Apply hatching to new 44 GVFKs
for idx, row in gvfk_gdf.iterrows():
    if row['GVFK'] in new_44_gvfks:
        # Hatched fill
        ax.add_patch(mpatches.Polygon(
            row.geometry.exterior.coords,
            facecolor='orange',
            hatch='///',  # Diagonal lines
            edgecolor='red',
            linewidth=2,
            alpha=0.6
        ))
```

---

## Quality Checks & Validation

Before finalizing results, verify:

1. **Data counts match expectations:**
   - Substance sites: ~1,711
   - Branch-only sites (filtered): ~3,600
   - Core GVFKs: ~214
   - Expanded GVFKs: ~258
   - New GVFKs: ~44

2. **GVFK categorization is correct:**
   - 170 shared + 44 new = 214 (should equal substance GVFK count)
   - 170 shared + 44 substance-only = 214
   - 170 shared + 44 new = 214... wait, that doesn't add up!

   **CORRECTION:**
   - 214 substance GVFKs = 170 shared + 44 substance-only
   - 258 expanded GVFKs = 170 shared + 44 new + 44 substance-only
   - So: 170 + 44 + 44 = 258 ✓

3. **Area/volume calculations:**
   - Sum should increase monotonically through workflow steps
   - No negative changes
   - Reasonable magnitudes (compare to total Denmark)

4. **Geographic overlaps:**
   - GVFKs may overlap spatially
   - Count overlapping area/volume multiple times (as specified)

5. **Branch/activity data:**
   - Check for empty/null values
   - Verify semicolon splitting works correctly
   - Top 10 lists should be meaningful (known high-risk industries)

---

## Expected Outputs Summary

### Figures (8 total)
1. GVFK count progression bar chart
2. Area & volume dual-axis progression chart
3. Three-way industry comparison (horizontal bars)
4. Three-way activity comparison (horizontal bars)
5. Overlap analysis visualization
6. Hexagonal heatmap comparison (2 side-by-side maps)
7. GVFK choropleth comparison (2 side-by-side maps)
8. (Optional) Geographic distribution by region

### Tables (8 total)
1. Detailed progression metrics (Step 1 → 5b+)
2. Contribution analysis (+44 GVFKs impact)
3. Group characteristics summary (3 groups)
4. Top 10 branches - 3-way comparison
5. Top 10 activities - 3-way comparison
6. Regional distribution comparison
7. Top municipalities comparison
8. Characteristics of 44 new GVFKs

### Data Files
- `gvfk_progression_metrics.csv`
- `industry_comparison_table.csv`
- `activity_comparison_table.csv`
- `new_44_gvfk_characteristics.csv`
- `three_group_summary.csv`

---

## Timeline & Execution

**Estimated implementation time:** 4-6 hours
- Phase 1: 30-60 min (data loading & filtering)
- Phase 2: 60-90 min (metrics calculation & charts)
- Phase 3: 90-120 min (branch/activity analysis & visualizations)
- Phase 4: 90-120 min (geographic maps)
- Testing & refinement: 30-60 min

**Execution order:**
1. Implement Phase 1 data loading first
2. Validate counts and categories
3. Proceed with Phase 2 (easier, fewer dependencies)
4. Then Phase 3 (more complex analysis)
5. Finally Phase 4 (most complex - geographic)

**Dependencies:**
- `pandas`, `numpy` - data manipulation
- `matplotlib`, `seaborn` - visualizations
- `geopandas` - geographic data
- `shapely` - spatial operations
- `h3-py` or custom hexagon generation for heatmaps

---

## Questions & Considerations

1. **Hexagon size for heatmap:** What resolution is appropriate? (5km, 10km, or adaptive?)

2. **High-risk industry definition:** Should we define specific keywords to identify high-risk industries/activities automatically?

3. **Map projections:** Use EPSG:25832 (ETRS89 / UTM zone 32N) for Denmark?

4. **Losseplads filtering:** Exact string matching or case-insensitive partial match?

5. **Missing GVFK names:** What if some sites have missing `Closest_GVFK`? Drop them or investigate?

6. **Overlapping GVFKs in volume/area:** Confirmed we COUNT overlaps (don't subtract)

---

## End of Plan

**File:** `step6_final_analysis.py` (to be created)

**Expected completion:** All 4 phases with 8 figures, 8 tables, comprehensive analysis comparing Core (214 GVFKs, 1,711 sites) vs Expanded (258 GVFKs, 5,311 sites) scenarios.