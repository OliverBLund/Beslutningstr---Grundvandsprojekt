# GVFK Data Version Comparison Report

**Date:** 2025-12-10  
**Author:** Generated via compare_gvfk_versions.py  
**Purpose:** Assess the impact of switching from legacy GVFK shapefile to new Grunddata GVFK layer

---

## Background

The workflow uses GVFK (Grundvandsfølsomme Kildezoner / groundwater sensitive source zones) polygons to determine which contaminated sites are connected to which aquifers. The site-GVFK mappings in the V1/V2 CSV input files were originally created using a **legacy GVFK shapefile** (`VP3Genbesøg_grundvand_geometri.shp`).

A newer GVFK dataset is now available from **Grunddata** (`Grunddata_results.gdb`, layer `dkm_gvf_vp3genbesog_kontakt`). This analysis compares the two datasets and quantifies the impact on workflow results.

---

## Methodology

1. **Loaded both GVFK datasets** and compared the set of GVFK names
2. **Performed fresh spatial overlay** between V1/V2 site polygons and the new GVFK polygons
3. **Generated new V1/V2 CSV files** with GVFK mappings from the new Grunddata layer
4. **Ran the full workflow** with both old and new CSV files
5. **Compared output files** from Steps 4, 5, and 6

---

## GVFK Name Comparison

| Metric | Count |
|--------|-------|
| Legacy shapefile GVFK count | 2,043 |
| New Grunddata GVFK count | 2,049 |
| Shared | 2,042 |
| Legacy-only | 1 (`dkmj_5009_ks`) |
| New-only | 7 |

**Conclusion:** The GVFK names are nearly identical between versions.

---

## Site-GVFK Pair Comparison

| Dataset | Pair Match Rate | Sites with Same GVFK Count |
|---------|-----------------|---------------------------|
| V1 | 93.8% | 96% of sites |
| V2 | 90.3% | 96% of sites |

- Average GVFKs per site: ~2.6 (same in both versions)
- Sites gaining GVFKs in new data: 25
- Sites losing GVFKs in new data: 830
- Sites with same GVFK count: 22,354

---

## Input File Comparison

| File | Old Rows | New Rows | Change |
|------|----------|----------|--------|
| `v1_gvfk_forurening.csv` | 84,601 | 83,655 | -1.1% |
| `v2_gvfk_forurening.csv` | 134,636 | 133,273 | -1.0% |

---

## Workflow Output Comparison

### Step-by-Step Row Counts

| Step | OLD | NEW | Change |
|------|-----|-----|--------|
| Step 4: Distance calculations | 49,138 | 49,741 | +1.2% |
| Step 5: High risk sites | 2,929 | 3,030 | +3.4% |
| Step 5b: Compound combinations | 2,060 | 2,095 | +1.7% |
| Step 6: MKK exceedance rows | 1,496 | 1,530 | +2.3% |
| Step 6: Segment summary | 428 | 440 | +2.8% |

### Key Results

| Metric | OLD | NEW | Difference |
|--------|-----|-----|------------|
| **Unique sites with MKK exceedance** | 285 | 289 | **+4 sites** |
| **River segments with exceedance** | 217 | 222 | **+5 segments** |

### New Sites with MKK Exceedance

The following 4 sites now trigger MKK exceedances with the new GVFK data (not flagged with old data):

- `733-00028`
- `833-00594`
- `735-00051`
- `721-00023`

---

## Conclusion

**Impact Assessment:** The new Grunddata GVFK layer has a **small but measurable impact** on workflow results:

- ~1% fewer rows in input CSV files
- ~1-3% more rows in output files
- **4 additional sites** flagged with MKK exceedances
- **5 additional river segments** with exceedances

**Recommendation:** The new GVFK data has been adopted. The differences are relatively minor and the new Grunddata layer is considered more up-to-date and authoritative.

---

## Files Changed

- **Config updated:** `config.py` now points to new CSV files:
  - `v1_gvfk_forurening_NEW.csv`
  - `v2_gvfk_forurening_NEW.csv`

- **Backup created:** Old results preserved in `Resultater/backup4_before_newV1V2/`

- **Comparison script:** `compare_gvfk_versions.py` can be re-run to regenerate this analysis

---

## How to Revert

To switch back to the legacy GVFK data, edit `config.py` lines 237-241:

```python
# Current (new GVFK):
V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening_NEW.csv"
V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening_NEW.csv"

# To revert (old GVFK):
V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening.csv"
V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening.csv"
```
