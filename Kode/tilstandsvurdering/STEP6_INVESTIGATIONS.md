# Step 6 (Tilstandsvurdering) - Investigation Log

This document records quality control investigations and verification tests performed on the Step 6 implementation.

---

## Investigation 1: Negative Infiltration Removal Verification

**Date:** 2025-11-07  
**Issue:** 2,086 site-GVFK-substance combinations (44.9% of data) were removed due to negative infiltration values  
**Question:** Is this removal justified, or is there a bug in the infiltration sampling method?

### Background

The flux calculation uses: `Flux = Area × Infiltration × Concentration`

Infiltration is sampled from DK-model GVD rasters (one per modellag: ks1, ks2, etc.). The rasters contain **net vertical flux** where:
- **Positive values** = recharge zones (water infiltrates downward)
- **Negative values** = discharge zones (groundwater flows upward to surface)

### Sampling Methods Considered

Two potential methods for sampling infiltration from rasters:

1. **Centroid-based:** Sample raster at the site's centroid point
2. **Polygon-based:** Average raster values across the entire site polygon

### Investigation Approach

1. Generated validation dataset showing both centroid and polygon-averaged infiltration values
2. Created QGIS verification package with 30 sample sites (20 controversial + 10 clearly negative)
3. Manually verified in QGIS using Identify Features tool on rasters and site geometries

### Findings

**Data breakdown of 2,086 removed rows:**
- 196 rows (9.4%): Centroid positive, polygon negative → sites span both recharge and discharge zones
- 1,890 rows (90.6%): Both centroid and polygon negative → sites entirely in discharge zones

**QGIS Verification Result:**
The polygon-averaged approach correctly captures the **net infiltration** across the contaminated site area, which is scientifically more appropriate than point-sampling at the centroid.

### Decision

✓ **Polygon-averaged infiltration is CORRECT**  
✓ **Removal of negative infiltration sites is JUSTIFIED**

**Rationale:**
- Sites with negative net infiltration are in discharge zones
- Surface contamination cannot infiltrate downward in net discharge zones
- Setting flux to zero (via removal) is the physically correct approach
- Current implementation is correct; no changes needed

### Files Generated

- `Resultater/Figures/step6/negative_infiltration/step6_negative_infiltration_validation.csv` - Full validation dataset
- `Resultater/Figures/step6/negative_infiltration/QGIS_VERIFY_infiltration.gpkg` - QGIS verification package
- `Resultater/Figures/step6/negative_infiltration/rasters_for_qgis/` - Explicitly georeferenced rasters for QGIS

---

## Investigation 2: Unit Verification Across All Calculations

**Date:** 2025-11-07  
**Issue:** Verify that all unit conversions in flux and Cmix calculations are correct  
**Question:** Are the units correctly propagated through all calculation steps?

### Complete Unit Chain

**FLUX CALCULATION: J = A × C × I**

Inputs:
- Area (A): m²
- Infiltration (I): mm/year → converted to m/year (÷ 1000)
- Concentration (C): µg/L → converted to µg/m³ (× 1000)

Steps:
1. Convert infiltration: `I_m_yr = I_mm_yr / 1000` → m/year
2. Calculate volume: `V = A × I_m_yr` → m³/year
3. Convert concentration: `C_ug_m3 = C_ug_L × 1000` → µg/m³
4. Calculate flux: `Flux = V × C_ug_m3` → µg/year
5. Convert to kg/year: `Flux_kg = Flux_ug / 1e9` → kg/year

**CMIX CALCULATION: Cmix = Flux / Flow**

Inputs:
- Flux: kg/year → converted to µg/s
- Flow: m³/s

Steps:
1. Convert flux to µg: `Flux_ug_yr = Flux_kg_yr × 1e9` → µg/year
2. Convert to per second: `Flux_ug_s = Flux_ug_yr / 31557600` → µg/s
3. Convert flow to L/s: `Flow_L_s = Flow_m3_s × 1000` → L/s
4. Calculate Cmix: `Cmix = Flux_ug_s / Flow_L_s` → µg/L

**Code implementation:** `Cmix = Flux_ug_s / (Flow_m3_s × 1000)` ✓

### Verification Results

**Test 1: Manual calculation with example values**
- Area = 10,000 m², Infiltration = 100 mm/yr, Concentration = 1,000 µg/L, Flow = 0.5 m³/s
- Expected Flux = 1.0 kg/year
- Expected Cmix = 0.0634 µg/L
- ✓ Code produces correct results

**Test 2: Verification with actual data (Flux)**
- Site 101-00002: Area = 581,621.50 m², Infiltration = 45.23 mm/yr, Concentration = 1,800 µg/L
- Stored: 47.356553 kg/year
- Calculated: 47.356553 kg/year
- Difference: 7.11e-15 kg/year
- ✓ Perfect match

**Test 3: Verification with actual data (Cmix)**
- Segment DKRIVER1031: Flux = 0.454726 kg/yr, Flow = 0.032168 m³/s
- Stored: 0.447939 µg/L
- Calculated: 0.447939 µg/L
- Difference: 5.55e-17 µg/L
- ✓ Perfect match

### Decision

✓ **All unit conversions are CORRECT**  
✓ **No changes needed to calculation code**

The earlier concern about "1000× scaling issue" in STEP6_CALCULATION_ISSUES.md was unfounded - the units are implemented correctly.

---

## Investigation 3: Scenario-Based Concentration Assignment

**Date:** 2025-11-07  
**Issue:** Multiple substances within same category at one site created excessive flux rows  
**Example:** Site with 4 BTXER compounds generated 4 separate flux calculations with different concentrations

### Problem

**Original approach:** Each substance in a category used different concentrations
- Benzen (modelstof): 400 µg/L
- Toluen, Xylener, Olieprodukter (non-modelstoffer): 1500 µg/L (category fallback)
- Result: Site 173-00029 with 4 BTXER substances → 4 flux rows (0.61 + 2.29 + 2.29 + 2.29 kg/yr)

**Issue:** Non-modelstoffer should use modelstof concentrations, not arbitrary category defaults

### Solution: Scenario-Based Aggregation

**New approach:** All compounds in a category use modelstof concentration(s)
- Categories with multiple modelstoffer generate multiple scenarios
- ONE flux value per scenario per site (not per substance)

**Example - BTXER has 2 modelstoffer:**
- Scenario 1: BTXER__via_Benzen (400 µg/L)
- Scenario 2: BTXER__via_Olie C10-C25 (3000 µg/L)

**Site 173-00029 now generates:**
- 2 flux rows for BTXER (instead of 4)
- Each row represents a different scenario
- Both use the same site area and infiltration

### Implementation

**Category to Scenarios Mapping:**
```python
CATEGORY_SCENARIOS = {
    "BTXER": ["Benzen", "Olie C10-C25"],
    "KLOREREDE_OPLØSNINGSMIDLER": ["1,1,1-Trichlorethan", "Trichlorethylen", "Chloroform", "Chlorbenzen"],
    "UORGANISKE_FORBINDELSER": ["Arsen", "Cyanid"],
    "PESTICIDER": ["Mechlorprop", "Atrazin"],
    "POLARE_FORBINDELSER": ["MTBE", "4-Nonylphenol"],
    "PAH_FORBINDELSER": ["Fluoranthen"],
    "PHENOLER": ["Phenol"],
    "KLOREREDE_PHENOLER": ["2,6-dichlorphenol"],
}
```

**Concentration Hierarchy (preserved):**
1. Activity + Modelstof (e.g., "Servicestationer_Benzen": 8000 µg/L)
2. Losseplads + Modelstof
3. Losseplads + Category
4. Compound (modelstof)
5. Category Scenario

**Site Level:** Group substances by category → generate one flux per scenario

**Segment Level:** Sum matching scenarios across sites

### Results

**Site 173-00029:**
- Before: 14 substance rows
- After: 6 scenario rows
  - BTXER: 2 scenarios
  - UORGANISKE_FORBINDELSER: 2 scenarios  
  - PAH_FORBINDELSER: 1 scenario
  - ANDRE: 1 row (no scenarios)

**Overall:**
- Total flux rows: 2,764
- BTXER: 248 scenario rows (124 sites × 2 scenarios each)
- KLOREREDE_OPLØSNINGSMIDLER: 1,300 scenario rows (325 sites × 4 scenarios each)
- All scenarios properly aggregated at segment level

### Benefits

✓ **Scientifically sound:** All compounds use modelstof concentrations  
✓ **Simplified:** One flux per scenario per site (not per substance)  
✓ **Scenario analysis:** Shows range of possible impacts based on different modelstof assumptions  
✓ **Maintains hierarchy:** Activity/losseplads overrides still apply correctly

---

## Investigation 4: [Next investigation]

*Template for future investigations*

---
