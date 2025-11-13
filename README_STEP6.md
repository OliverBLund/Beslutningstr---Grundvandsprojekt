## Step 6 – Tilstandsvurdering Overview

This note summarises the Step 6 workflow, the inputs it consumes, and the artefacts it produces. A single site (`Lokalitet_ID = 151-00002`, GVFK `dkms_3108_ks`, category **BTXER**) is used as a running example so you can follow one combination through every stage.

---

### 1. Required inputs

| Data source | Description / key fields | Example path |
|-------------|--------------------------|--------------|
| Step 5 detailed combinations | Output from `step5_risk_assessment.py` with site–GVFK–substance tuples and nearest river metadata. | `Resultater/step5_compound_detailed_combinations.csv` |
| Step 3 site polygons | Dissolved V1/V2 geometries used to derive areas and centroids. | `Resultater/step3_v1v2_sites.shp` |
| GVFK↔model‐layer mapping | Lookup table mapping each GVFK to one or more DKM layers for infiltration sampling. | `Data/vp3_h1_grundvandsforekomster_VP3Genbesøg.csv` |
| GVD rasters | Layered infiltration rasters (`DKM_gvd_k?.tif`). | `Data/dkm2019_vp3_GVD/` |
| River network with GVFK contact | Provides segment geometry, IDs, names, and lengths. | `Data/shp files/Rivers_gvf_rev20230825_kontakt.shp` |
| Q-point discharges | Mean/Q90/Q95 flow per river segment (`dkm_qpoints_gvf…shp`). Step 6 keeps the **maximum** value per segment to be conservative. | `Data/dkm2019_vp3_qpunkter_inklq95/…shp` |

---

### 2. Workflow steps (with example)

1. **Load Step 5 combinations**
   - Example row: `151-00002`, GVFK `dkms_3108_ks`, category BTXER, nearest river `DKRIVER2955` (Søruprenden), distance 15 m.
   - Mandatory columns are validated (site ID, GVFK, category, substance, river IDs, distance, segment count).

2. **Attach geometry, modellag, and infiltration**
   - The site polygon (area 24 097 m²) is looked up in the Step 3 shapefile.
   - GVFK `dkms_3108_ks` maps to layer `ks3`, so the script samples `DKM_gvd_ks3.tif` to obtain infiltration = **307 mm/year** (polygon combined statistic).
   - Rows lacking modellag or infiltration are dropped with warnings; negative infiltration rows are quarantined for diagnostics.

3. **Compute scenario-based flux (J = A · C · I)**
   - BTXER uses two modelstoffer: Benzen (400 µg/L) and Olie C10–C25 (3 000 µg/L).
   - For Benzen: `Flux = 24 097 m² × 0.307 m/year × 400 µg/L ≈ 9.36 kg/year`.
   - For Olie C10–C25: `Flux ≈ 70.2 kg/year`.
   - Each category/scenario pair yields one flux row per site; LOSSEPLADS/PFAS use a single fallback concentration.

4. **Aggregate by river segment**
   - All site fluxes targeting `DKRIVER2955` are summed per category/substance.
   - Segment metadata (name, length, GVFK and contributing site IDs) are appended.

5. **Join discharge scenarios & compute Cmix**
   - The three flow scenarios (Mean = 0.162 m³/s, Q90 = 0.168, Q95 = 0.163 for Søruprenden) are merged.
   - `Flux (µg/s) = Flux (kg/year) · 1e9 / seconds_per_year`.
   - `Cmix (µg/L) = Flux (µg/s) / (Flow m³/s · 1000)`.
   - Example (Olie scenario @ Q95): `Cmix ≈ 13.9 µg/L`.

6. **Apply MKK thresholds**
   - BTXER uses the Benzen AA-EQS (10 µg/L).
   - Exceedance ratios in Søruprenden: from **3.3× (Mean, Benzen)** up to **139× (Q95, Olie scenario)**.
   - Rows with `Cmix > MKK` are flagged and collapsed into site-level and GVFK-level exceedance tables.

7. **Exports & reporting**
   - CSVs: site flux, segment flux, Cmix, per-segment summary, legacy flux, and the new exceedance-only tables (`step6_sites_mkk_exceedance.csv`, `step6_gvfk_mkk_exceedance.csv`).
   - Visuals: combined impact maps (`Resultater/Figures/step6/combined/...`), analytical plots (`…/analytical/`), and diagnostics (`…/diagnostics/`), plus console summaries.

---

### 3. Output cheat sheet

| File | Purpose |
|------|---------|
| `step6_flux_site_segment.csv` | One row per site/GVFK/category/scenario with area, infiltration, flux (µg/mg/g/kg per year). |
| `step6_flux_by_segment.csv` | Segment-level totals (per category/substance) with contributing site lists and distance stats. |
| `step6_cmix_results.csv` | Segment totals + Mean/Q90/Q95 flows, resulting Cmix, ratios, flags. |
| `step6_segment_summary.csv` | One row per segment summarising total flux, max ratio, failing scenarios, and site IDs. |
| `step6_sites_mkk_exceedance.csv` | Only the site rows that produce MKK exceedances (used for QA and follow-up). |
| `step6_gvfk_mkk_exceedance.csv` | GVFK-centric roll-up of exceedances (segment, sites, categories, scenario list). |
| `Resultater/Figures/step6/combined/...` | Interactive combined impact maps (overall + per category/compound). |
| `Resultater/Figures/step6/analytical/*.png` | Static dashboards: category impact, top sites/rivers, scenario sensitivity, treemap, etc. |
| `Resultater/Figures/step6/diagnostics/*` | Negative-infiltration QA and extreme exceedance diagnostics. |

---

### 4. Recent investigations / data caveats

- **PFAS exceedances dominate the top of the ratio list.**
  PFAS currently uses a category concentration of 500 µg/L and a very low MKK (0.0044 µg/L). When combined with tiny Q95/Q90 flows (e.g., 0.0003 m³/s on DKRIVER2849), the Cmix/MKK ratio exceeds 300 000×. Review whether the PFAS concentration, MKK reference, or flow inputs should be adjusted or capped.

- **Low-flow sensitivity**
  Even outside PFAS, chlorinated solvent categories can exceed 1 000× on creeks with Q95 < 0.01 m³/s. The new helper script `Kode/tilstandsvurdering/analyze_extreme_exceedances.py` ranks these combinations and annotates likely causes (very low flow vs high flux). Use it after each run to triage the worst offenders.

- **Negative infiltration filtering (opstrømningszoner)**
  78% of filtered rows (1,919 out of 2,457 total filtered rows) are removed due to negative infiltration values, representing 672 unique sites out of 1,743 total input sites. These sites are located in groundwater discharge zones (opstrømningszoner) where the flux formula J = A × C × I does not apply scientifically. Many of these sites are at 0m distance from rivers. Example: Site 151-00001 with infiltration values of -75.1 and -89.2 mm/yr across different layers. This filtering is scientifically correct and necessary. The `step6_filtering_audit_detailed.csv` output provides complete transparency showing exact reasons for each filtered site across three filter stages: (1) missing modellag mapping, (2) negative infiltration, and (3) missing infiltration data.

Keep this sheet close when validating Step 6 outputs or explaining the workflow to collaborators. It ties each dataset and visual back to a concrete example and highlights known edge cases.
