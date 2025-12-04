## Step 6 – Tilstandsvurdering Overview

This note summarises the Step 6 workflow, the inputs it consumes, and the artefacts it produces. A single site (`Lokalitet_ID = 151-00002`, GVFK `dkms_3108_ks`, category **BTXER**) is used as a running example so you can follow one combination through every stage.

---

### 1. Required inputs

| Data source | Description / key fields | Example path |
|-------------|--------------------------|--------------|
| Step 5 detailed combinations | Output from `step5_risk_assessment.py` with site–GVFK–substance tuples and nearest river metadata. | `Resultater/step5_compound_detailed_combinations.csv` |
| Step 3 site polygons | Dissolved V1/V2 geometries used to derive areas and centroids. | `Resultater/step3_v1v2_sites.shp` |
| GVFK↔model‐layer mapping | Lookup table mapping each GVFK to one or more DKM layers for infiltration sampling. | `Data/vp3_h1_grundvandsforekomster_VP3Genbesøg.csv` |
| GVD rasters | Layered infiltration rasters (`DKM_gvd_k?.tif`). | `Data/dkm2019_vp3_GVD/` |
| River network with GVFK contact | Provides segment geometry, IDs, names, and lengths. | `Data/shp files/Rivers_gvf_rev20230825_kontakt.shp` |
| Q-point discharges | Mean/Q90/Q95 flow per river segment (`dkm_qpoints_gvf…shp`). Step 6 keeps the **maximum** Q value per segment (conservative approach). | `Data/dkm2019_vp3_qpunkter_inklq95/…shp` |

---

### 2. Workflow steps (with example)

1. **Load Step 5 combinations**
   - Example row: `151-00002`, GVFK `dkms_3108_ks`, category BTXER, nearest river `DKRIVER2955` (Søruprenden), distance 15 m.
   - Mandatory columns are validated (site ID, GVFK, category, substance, river IDs, distance, segment count).

2. **Attach geometry, modellag, and infiltration**
   - The site polygon (area 24 097 m²) is looked up in the Step 3 shapefile.
   - GVFK `dkms_3108_ks` maps to layer `ks3`, so the script samples `DKM_gvd_ks3.tif` to obtain infiltration = **307 mm/year** (polygon combined statistic).
   - Rows lacking modellag or infiltration are dropped with warnings; negative infiltration rows are quarantined for diagnostics.

3. **Compute scenario-based flux (J = A · C · I)**
   - **Step 3a - Grouping**: Sites are first grouped by (Lokalitet_ID, River segment, Category) to create one representative row per site-segment-category combination. When a site appears in multiple GVFKs affecting the same river, the minimum distance is taken.
   
   - **Step 3b - Scenario expansion**: Flux rows are generated based on category type:
     - **Categories WITH scenarios** (9 categories): Generate multiple flux rows per category, one for each modelstof:
       - BTXER: 2 scenarios → Benzen (400 µg/L), Olie C10–C25 (3000 µg/L)
       - KLOREREDE_OPLØSNINGSMIDLER / KLOREDE_KULBRINTER: 4 scenarios → 1,1,1-Trichlorethan (100), Trichlorethylen (42000), Chloroform (100), Chlorbenzen (100)
       - PESTICIDER: 2 scenarios → Mechlorprop (1000), Atrazin (12)
       - PHENOLER: 1 scenario → Phenol (1300)
       - KLOREREDE_PHENOLER: 1 scenario → 2,6-dichlorphenol (10000)
       - PAH_FORBINDELSER: 1 scenario → Fluoranthen (30)
       - POLARE_FORBINDELSER: 2 scenarios → MTBE (50000), 4-Nonylphenol (9)
       - UORGANISKE_FORBINDELSER: 2 scenarios → Arsen (100), Cyanid (3500)
     - **Categories WITHOUT scenarios** (LOSSEPLADS, ANDRE, PFAS): Use first substance as representative. However, these categories have default concentration = -1 and are **filtered out** unless specific losseplads or activity overrides exist.
   
   - **Example for site 151-00002**:
     - Step 5 input: 1 BTXER row (even if 7 different BTX compounds detected)
     - After grouping: 1 site-category row
     - After scenario expansion: **2 flux rows**
       - Benzen scenario: `Flux = 24 097 m² × 0.307 m/year × 400 µg/L ≈ 9.36 kg/year`
       - Olie scenario: `Flux = 24 097 m² × 0.307 m/year × 3000 µg/L ≈ 70.2 kg/year`
   
   - **Critical principle**: Each site contributes **ONE flux value per scenario**. Rows with concentration = -1 are filtered out before any flux calculations (code line 916).

4. **Aggregate by river segment**
   - **Grouping keys**: (River ov_id, Category, Scenario substance) — **scenarios are NEVER mixed together**.
   - All site fluxes for the **SAME scenario** are summed per river segment.
   - **Example**: River segment DKRIVER2054 receives BTXER pollution from 4 contributing sites:
     - **For Benzen scenario ONLY**:
       - Site 630-82174: 5.2 kg/year
       - Site 631-00084: 3.8 kg/year
       - Site 631-00182: 4.1 kg/year
       - Site 631-00296: 3.2 kg/year
       - **Segment total for Benzen scenario: 16.3 kg/year**
     - **For Olie C10-C25 scenario**: Summed separately with different total
     - The two scenarios remain completely independent throughout all subsequent calculations.
   - Segment metadata (name, length, GVFK, contributing site IDs, min/max distance) are appended.

5. **Join discharge scenarios & compute Cmix**
   - **Q-point selection**: For each river segment (ov_id), the **MAXIMUM** Q value across all Q-points is selected (conservative approach, ensures we don't underestimate dilution capacity).
   - **Flow scenarios**: Three flow scenarios are evaluated (Mean, Q90, Q95), with Q95 representing low-flow conditions.
   - **Cmix formula**: 
     - `Flux (µg/s) = Flux (kg/year) × 1e9 / 31 536 000`
     - `Cmix (µg/L) = Flux (µg/s) / (Q (m³/s) × 1000)`
   - **Example for DKRIVER2054, Benzen scenario @ Q95**:
     - Summed flux: 16.3 kg/year = 516.0 µg/s
     - Q95 (maximum): 2.97 m³/s
     - **Cmix = 516.0 / (2.97 × 1000) = 0.174 µg/L**
   - **Result**: ONE Cmix value per segment per scenario per flow condition.

6. **Apply MKK thresholds**
   - **Substance-specific MKK**: The 16 modelstoffer (Benzen, Olie C10-C25, Trichlorethylen, Phenol, Arsen, etc.) are checked first for substance-specific MKK values.
   - **Category fallback**: All other scenarios use the category MKK (lowest AA-EQS in that category).
   - **Special case**: "Olie C10-C25" has no EQS (MKK = None), so it falls back to category BTXER MKK (10.0 µg/L).
   - **Example**:
     - **BTXER__via_Benzen**: Extract "Benzen" → Check MODELSTOFFER → Use substance-specific MKK = 10.0 µg/L
     - **BTXER__via_Olie C10-C25**: Extract "Olie C10-C25" → Check MODELSTOFFER → MKK = None → Fall back to BTXER category MKK = 10.0 µg/L
   - **Exceedance calculation**:
     - `Exceedance_Ratio = Cmix / MKK`
     - `Exceedance_Flag = (Cmix > MKK)`
   - Rows with MKK exceedances are flagged and extracted into dedicated summary tables.

7. **Exports & reporting**
   - CSVs: site flux, Cmix results (with segment-level aggregation), per-segment summary, site exceedance table, and filtering audit trail.
   - Visuals: combined impact maps (`Resultater/Figures/step6/combined/...`), analytical plots (`…/analytical/`), and diagnostics (`…/diagnostics/`), plus console summaries.

---

### 3. Complete Workflow Example: Site 151-00002 "Cheminovagrunden, Måløv"

This example demonstrates how a single contaminated site progresses through the entire Step 6 workflow, including scenario expansion, segment aggregation, and Cmix calculation.

#### **Site Characteristics:**
- **Lokalitet_ID**: 151-00002
- **Site Type**: V2 (Kortlagt)
- **Activities**: Pesticide production + Metal surface treatment
- **Affects 2 GVFKs**: 
  - `dkms_3108_ks` (infiltration: 275.47 mm/yr, distance to nearest river: 75.7m)
  - `dkms_3646_ks` (infiltration: 311.52 mm/yr, distance to nearest river: 343.0m)
- **Affects 2 River Segments**:
  - DKRIVER2955 (Søruprenden) via dkms_3108_ks
  - DKRIVER6977 (Værebro Å) via dkms_3646_ks

#### **Step-by-Step Transformation:**

**STEP 5 INPUT**: 10 substance rows across 2 GVFKs and multiple categories

| GVFK | River | Distance (m) | Category | Substances (count) |
|------|-------|--------------|----------|--------------------|
| dkms_3108_ks | DKRIVER2955 | 75.7 | BTXER | 1 |
| dkms_3108_ks | DKRIVER2955 | 75.7 | KLOREDE_KULBRINTER | 1 |
| dkms_3108_ks | DKRIVER2955 | 75.7 | KLOREREDE_OPLØSNINGSMIDLER | 1 |
| dkms_3108_ks | DKRIVER2955 | 75.7 | KLOREREDE_PHENOLER | 1 |
| dkms_3108_ks | DKRIVER2955 | 75.7 | PESTICIDER | 1 |
| dkms_3108_ks | DKRIVER2955 | 75.7 | PHENOLER | 3 |
| dkms_3646_ks | DKRIVER6977 | 343.0 | KLOREREDE_OPLØSNINGSMIDLER | 1 |
| dkms_3646_ks | DKRIVER6977 | 343.0 | PESTICIDER | 1 |

**Total Step 5 rows: 10**

**AFTER GROUPING**: 8 site-segment-category combinations (one per unique site+river+category)

**AFTER SCENARIO EXPANSION**: 20 flux rows

| River | Category | Scenario | Concentration (µg/L) | Flux (kg/year) |
|-------|----------|----------|---------------------|----------------|
| DKRIVER2955 | BTXER | via_Benzen | 400 | 9.36 |
| DKRIVER2955 | BTXER | via_Olie C10-C25 | 3000 | 70.18 |
| DKRIVER2955 | KLOREDE_KULBRINTER | via_1,1,1-Trichlorethan | 100 | 2.34 |
| DKRIVER2955 | KLOREDE_KULBRINTER | via_Trichlorethylen | 42000 | 982.45 |
| DKRIVER2955 | KLOREDE_KULBRINTER | via_Chloroform | 100 | 2.34 |
| DKRIVER2955 | KLOREDE_KULBRINTER | via_Chlorbenzen | 100 | 2.34 |
| DKRIVER2955 | KLOREREDE_OPLØSNINGSMIDLER | via_1,1,1-Trichlorethan | 100 | 2.34 |
| DKRIVER2955 | KLOREREDE_OPLØSNINGSMIDLER | via_Trichlorethylen | 42000 | 982.45 |
| DKRIVER2955 | KLOREREDE_OPLØSNINGSMIDLER | via_Chloroform | 100 | 2.34 |
| DKRIVER2955 | KLOREREDE_OPLØSNINGSMIDLER | via_Chlorbenzen | 100 | 2.34 |
| DKRIVER2955 | KLOREREDE_PHENOLER | via_2,6-dichlorphenol | 10000 | 233.92 |
| DKRIVER2955 | PESTICIDER | via_Mechlorprop | 1000 | 23.39 |
| DKRIVER2955 | PESTICIDER | via_Atrazin | 12 | 0.28 |
| DKRIVER2955 | PHENOLER | via_Phenol | 1300 | 30.41 |
| DKRIVER6977 | KLOREREDE_OPLØSNINGSMIDLER | via_1,1,1-Trichlorethan | 100 | 2.65 |
| DKRIVER6977 | KLOREREDE_OPLØSNINGSMIDLER | via_Trichlorethylen | 42000 | 1111.04 |
| DKRIVER6977 | KLOREREDE_OPLØSNINGSMIDLER | via_Chloroform | 100 | 2.65 |
| DKRIVER6977 | KLOREREDE_OPLØSNINGSMIDLER | via_Chlorbenzen | 100 | 2.65 |
| DKRIVER6977 | PESTICIDER | via_Mechlorprop | 1000 | 26.45 |
| DKRIVER6977 | PESTICIDER | via_Atrazin | 12 | 0.32 |

**Key observation**: Higher infiltration in dkms_3646_ks (311.52 mm/yr) leads to higher flux values for the same concentrations!

**SEGMENT AGGREGATION**: Since site 151-00002 is the ONLY contributor to both segments, aggregation doesn't change the flux values. However, metadata is added (contributing sites, distance stats, etc.).

**CMIX CALCULATION** (for DKRIVER2955, Q95 scenario):

| Scenario | Flux (kg/yr) | Q95 (m³/s) | Cmix (µg/L) | MKK (µg/L) | Ratio | Exceeds? |
|----------|--------------|------------|-------------|------------|-------|----------|
| BTXER__via_Benzen | 9.36 | 0.00160 | 184.8 | 10.0 | 18.5× | YES |
| BTXER__via_Olie C10-C25 | 70.18 | 0.00160 | 1386.2 | 10.0 | 138.6× | YES |
| KLOREDE_KULBRINTER__via_Trichlorethylen | 982.45 | 0.00160 | 19407.0 | 2.5 | 7763× | YES |

**Note**: Extremely low flow (Q95 = 0.00160 m³/s) leads to very high Cmix values and extreme exceedance ratios!

---

### 4. Output cheat sheet

| File | Purpose |
|------|---------|
| `step6_flux_site_segment.csv` | One row per site/GVFK/category/scenario with area, infiltration, flux (µg/mg/g/kg per year). **This is the site-level output BEFORE segment aggregation.** |
| `step6_cmix_results.csv` | Segment-level totals (per category/substance/scenario) with contributing site lists, Q95 flow (maximum per segment), resulting Cmix, MKK thresholds, and exceedance flags. **This is the aggregated output with Cmix calculations.** |
| `step6_segment_summary.csv` | One row per segment summarising total flux across all categories, max Cmix, max exceedance ratio, failing scenarios, and contributing site IDs. **This is the highest-level summary per river segment.** |
| `step6_sites_mkk_exceedance.csv` | Only the site rows that produce MKK exceedances (used for QA and follow-up). Filtered view of sites contributing to exceedances. |
| `step6_filtering_audit_detailed.csv` | Complete audit trail of all filtered rows showing which filter stage removed each site and why (missing modellag, negative infiltration, or missing infiltration data). |
| `Resultater/Figures/step6/combined/...` | Interactive combined impact maps (overall + per category/compound). |
| `Resultater/Figures/step6/analytical/*.png` | Static dashboards: category impact, top sites/rivers, scenario sensitivity, treemap, etc. |
| `Resultater/Figures/step6/diagnostics/*` | Negative-infiltration QA and extreme exceedance diagnostics. |

---

### 5. Technical Notes

#### **5.1 Grouping Keys at Each Stage**

| Stage | Grouping Keys | Purpose |
|-------|---------------|---------|
| **Flux calculation** | (Lokalitet_ID, River ov_id, Category) | Collapse multiple substances per category into one representative row per site-segment-category. Takes minimum distance when site spans multiple GVFKs. |
| **Scenario expansion** | — | Generates multiple flux rows per grouped row based on CATEGORY_SCENARIOS mapping. |
| **Segment aggregation** | (River ov_id, Category, Scenario substance) | Sum all site fluxes for the SAME scenario. **Scenarios remain completely separated.** |
| **Cmix calculation** | — | Operates on aggregated segment fluxes, computing one Cmix per segment per scenario per flow condition. |

#### **5.2 Why Infiltration Differs Between GVFKs for Same Site**

When a site polygon intersects multiple GVFKs, each GVFK uses a different DK-modellag (aquifer layer). Different layers have different infiltration characteristics:

- **Example**: Site 151-00002
  - GVFK `dkms_3108_ks` uses layer `ks3` → Infiltration = 275.47 mm/year
  - GVFK `dkms_3646_ks` uses layer `ks4` → Infiltration = 311.52 mm/year
  
This is scientifically correct because infiltration varies by aquifer depth and geological characteristics.

#### **5.3 Concentration Lookup Hierarchy (5 Levels)**

When determining which concentration to use for a scenario, the code checks in this order:

1. **Activity + Substance**: e.g., "Servicestationer_Benzen" → 8000 µg/L
2. **Losseplads + Substance**: If site is LOSSEPLADS category, check for substance-specific landfill concentrations (e.g., "Benzen" → 17 µg/L)
3. **Losseplads + Category**: If site is LOSSEPLADS, check for category-specific landfill concentrations (e.g., "BTXER" → 3000 µg/L)
4. **Direct Compound**: Check if substance is one of the 16 modelstoffer (e.g., "Benzen" → 400 µg/L)
5. **Category Scenario**: Use scenario-specific category concentration (e.g., "BTXER__via_Benzen" → 400 µg/L)

If all lookups fail or return -1, the row is filtered out.

#### **5.4 Conservative Flow Selection (MAXIMUM Q)**

Multiple Q-points may exist per river segment. The code takes the **MAXIMUM** Q value across all points:

```python
# data_loaders.py, line 176
flow_max = flow_long.groupby(["ov_id", "Scenario"]).max()
```

This is conservative because **higher flow → lower Cmix → lower exceedance ratios**. We want to avoid underestimating the dilution capacity of the river.

#### **5.5 Scenario Independence**

**Critical principle**: Scenarios are NEVER mixed together at any stage.

- Each scenario has its own flux calculation
- Each scenario is aggregated separately per segment
- Each scenario gets its own Cmix calculation
- Each scenario is compared to its own MKK threshold

**Example**: A river with 4 sites contributing KLOREREDE_OPLØSNINGSMIDLER (4 scenarios each) will have:
- 4 × 4 = 16 site flux rows
- 4 aggregated segment flux rows (one per scenario)
- 4 Cmix values per flow condition (Mean, Q90, Q95)
- 4 MKK comparisons

The Trichlorethylen scenario is completely independent from the Chloroform scenario, even though they're in the same category.

---

### 6. Recent investigations / data caveats

- **-1 Concentration Filtering (LOSSEPLADS, ANDRE, PFAS)**
  Three categories have default concentration = -1 in `config.py`: LOSSEPLADS, ANDRE, and PFAS. These represent cases where no valid standard concentration exists from Delprojekt 3. Rows with these categories are **filtered out during flux calculation** (line 916 in `step6_tilstandsvurdering.py`) UNLESS:
  - They have specific losseplads overrides (e.g., "BTXER" → 3000 µg/L for landfills)
  - They have activity-specific overrides (e.g., "Servicestationer_Benzen" → 8000 µg/L)
  
  This filtering is scientifically correct and intentional. Sites that get filtered are documented in `step6_filtering_audit_detailed.csv`.

- **PFAS exceedances dominate the top of the ratio list.**
  PFAS sites that survive filtering (via specific overrides) currently use a category concentration of 500 µg/L and a very low MKK (0.0044 µg/L). When combined with tiny Q95/Q90 flows (e.g., 0.0003 m³/s on DKRIVER2849), the Cmix/MKK ratio exceeds 300 000×. Review whether the PFAS concentration, MKK reference, or flow inputs should be adjusted or capped.

- **Low-flow sensitivity**
  Even outside PFAS, chlorinated solvent categories can exceed 1 000× on creeks with Q95 < 0.01 m³/s. The helper script `Kode/tilstandsvurdering/analyze_extreme_exceedances.py` ranks these combinations and annotates likely causes (very low flow vs high flux). Use it after each run to triage the worst offenders.

- **Negative infiltration filtering (opstrømningszoner)**
  78% of filtered rows (1,919 out of 2,457 total filtered rows) are removed due to negative infiltration values, representing 672 unique sites out of 1,743 total input sites. These sites are located in groundwater discharge zones (opstrømningszoner) where the flux formula J = A × C × I does not apply scientifically. Many of these sites are at 0m distance from rivers. Example: Site 151-00001 with infiltration values of -75.1 and -89.2 mm/yr across different layers. This filtering is scientifically correct and necessary. The `step6_filtering_audit_detailed.csv` output provides complete transparency showing exact reasons for each filtered site across three filter stages: (1) missing modellag mapping, (2) negative infiltration, and (3) missing infiltration data.

- **BUGFIX (2025-01-03): Missing infiltration parser bug [RESOLVED]**
  **Problem:** 101 sites (10%) were incorrectly dropped for "missing infiltration" despite being inside raster extents and having valid data.
  
  **Root Cause:** Parser bug in `_parse_dk_modellag()` (line 703). The function only split on semicolons (`;`), but many GVFKs have slash-separated (`/`) layer assignments like `kvs_0200/kvs_0400`. The parser treated `"kvs_0200/kvs_0400"` as ONE invalid layer name instead of TWO separate layers, attempting to open non-existent file `dk16_gvd_kvs_0200/kvs_0400.tif`.
  
  **The Fix:** Updated parser to detect and handle both semicolon and slash separators (priority: semicolon → slash → single value). Now correctly parses `"kvs_0200/kvs_0400"` → `['kvs_0200', 'kvs_0400']`.
  
  **Results:**
  - ✅ **95 sites recovered** (94% success rate)
  - ✅ Only **6 sites** remain filtered (genuinely outside model coverage: 741-00032, 741-00033, 741-00043, 741-00070, 741-00114, 825-00401)
  - ✅ Data completeness improved from **90% to 99.4%**
  - Filter 3 now removes only 8 rows (0.4%) vs 210 rows (9.4%) before fix
  
  **Diagnostic Tools Created:**
  - `Kode/tools/diagnose_raster_nodata_holes.py` - Tests buffer sampling strategies, confirmed no small nodata gaps
  - `Kode/tools/propose_nodata_fallback_strategy.py` - Tests alternative layers, revealed parser bug
  - Output files: `nodata_buffer_recovery_analysis.csv`, `nodata_spatial_coverage_map.html`, `nodata_fallback_proposals.csv`
  
  **Validation:** Manually verified site 509-30007 (dkmj_2_ks) now correctly samples both kvs_0200 (240.39 mm/year) and kvs_0400 (240.39 mm/year), averaging to valid infiltration value.

---

Keep this sheet close when validating Step 6 outputs or explaining the workflow to collaborators. It ties each dataset and visual back to a concrete example and highlights known edge cases.
