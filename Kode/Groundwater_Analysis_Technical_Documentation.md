# Groundwater Contamination Analysis: Technical Documentation

**Version:** Current (Updated with actual workflow results)  
**Date:** December 2024  
**Analysis:** V1/V2 Contamination Sites Distance to Rivers in Danish Groundwater Aquifers (GVFK)

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Data Sources & Requirements](#data-sources--requirements)
3. [Technical Methodology](#technical-methodology)
4. [Implementation Details](#implementation-details)
5. [Results & Statistics](#results--statistics)
6. [Output Files](#output-files)
7. [Quality Assurance](#quality-assurance)
8. [Visualizations](#visualizations)

---

## Executive Summary

This workflow analyzes contamination sites (V1/V2) in Danish groundwater aquifers to identify high-risk locations based on proximity to rivers. The analysis processes **2,043 groundwater aquifers (GVFK)**, filtering through river contact and active contamination criteria to identify **3,606 high-risk sites** within 500m of rivers.

### Key Findings
- **29.0%** of Danish GVFKs have river contact (593/2,043)
- **21.1%** of GVFKs contain V1/V2 contamination sites (432/2,043)
- **21.3%** of contamination sites pose high risk (≤500m from rivers)
- **81.0%** of contamination-affected GVFKs contain high-risk sites

---

## Data Sources & Requirements

### Primary Input Files

#### Shape Files
| File | Description | Features | Purpose |
|------|-------------|----------|---------|
| `VP3Genbesøg_grundvand_geometri.shp` | Groundwater aquifer boundaries | 2,043 GVFK | Base geometry for spatial analysis |
| `Rivers_gvf_rev20230825_kontakt.shp` | River segments with GVFK contact flags | 14,454 segments (7,496 with contact) | Distance calculation targets |
| `V1FLADER.shp` | V1 contamination site polygons | 28,717 polygons → 23,209 unique sites | Spatial geometry for V1 sites |
| `V2FLADER.shp` | V2 contamination site polygons | 33,040 polygons → 21,269 unique sites | Spatial geometry for V2 sites |

#### CSV Files (Attribute Data)
| File | Description | Records | Key Columns |
|------|-------------|---------|-------------|
| `v1_gvfk_forurening.csv` | V1 site-GVFK relationships with contamination data | 84,601 | `Lokalitetensstoffer`, `Lokalitetensbranche`, `Lokalitetensaktivitet` |
| `v2_gvfk_forurening.csv` | V2 site-GVFK relationships with contamination data | 134,636 | Same as above |

### System Requirements
- **Python Environment**: GeoPandas, Pandas, NumPy, Shapely
- **Storage**: ~2GB for data files, ~500MB for results
- **Processing Time**: ~10-15 minutes for complete workflow
- **Memory**: 8GB+ recommended for large dataset operations

---

## Technical Methodology

### Step 1: Groundwater Aquifer Inventory
**File:** `step1_all_gvfk.py`  
**Function:** `run_step1()`

**Objective:** Establish baseline count of unique groundwater aquifers.

**Process:**
1. Load base GVFK shapefile
2. Count unique values in `Navn` column
3. Save complete GVFK dataset for subsequent steps

**Code Implementation:**
```python
gvf = gpd.read_file(GRUNDVAND_PATH)
unique_gvfk = gvf["Navn"].nunique()
gvf.to_file(get_output_path('step1_gvfk'))
```

**Results:**
- **2,043 unique groundwater aquifers** identified
- Complete spatial coverage of Danish groundwater system

### Step 2: River Contact Identification
**File:** `step2_river_contact.py`  
**Function:** `run_step2()`

**Objective:** Identify GVFKs with direct river contact for contamination pathway analysis.

**Process:**
1. Load rivers shapefile (14,454 segments)
2. Filter to segments with `Kontakt = 1` (7,496 segments)
3. Extract unique GVFK names from river data
4. Create spatial subset of GVFKs with river contact

**Quality Control:**
- Validates river-GVFK naming consistency
- Handles CRS alignment between datasets

**Results:**
- **593 GVFKs have river contact** (29.0% of total)
- 588 GVFK geometries successfully matched and saved

### Step 3: Contamination Site Integration
**File:** `step3_v1v2_sites.py`  
**Function:** `run_step3(rivers_gvfk)`

**Objective:** Identify contamination sites with active contamination in river-connected GVFKs.

**Hybrid CSV+Shapefile Approach:**
- **CSV files**: Preserve complete site-GVFK relationships (many-to-many)
- **Shapefiles**: Provide accurate dissolved geometries per site

**Active Contamination Filter:**
```python
# Only sites with documented contamination substances
v1_csv = v1_csv.dropna(subset=['Lokalitetensstoffer'])
v1_csv = v1_csv[v1_csv['Lokalitetensstoffer'].str.strip() != '']
```

**Deduplication Process:**
1. **Within-dataset deduplication**: Remove duplicate lokalitet-GVFK combinations
2. **Cross-dataset deduplication**: Handle sites appearing in both V1 and V2
3. **Geometry assignment**: Match CSV relationships with dissolved shapefile geometries

**Data Flow:**
```
V1: 84,601 → 34,232 (active contamination) → 21,697 (river GVFKs) → 8,269 (deduplicated)
V2: 134,636 → 121,984 (active contamination) → 79,893 (river GVFKs) → 28,694 (deduplicated)
Combined: 36,963 → 32,391 (final deduplication, 4,572 overlaps removed)
```

**Results:**
- **16,934 unique contamination sites** with active contamination
- **32,391 site-GVFK combinations** (average 1.9 GVFKs per site)
- **432 GVFKs contain contamination sites** (21.1% of total)

**Site Type Distribution:**
- V2 only: 12,663 sites (74.8%)
- V1+V2 overlap: 2,398 sites (14.2%)
- V1 only: 1,873 sites (11.1%)

### Step 4: Distance Calculation
**File:** `step4_distances.py`  
**Function:** `run_step4(v1v2_combined)`

**Objective:** Calculate precise distances between contamination sites and nearest rivers within same GVFK.

**Distance Calculation Algorithm:**
1. **Site-GVFK iteration**: Process each of 32,391 combinations individually
2. **River matching**: Find rivers with `Kontakt = 1` in same GVFK
3. **Distance computation**: Calculate minimum distance using PostGIS-style operations
4. **Final distance identification**: Select shortest distance per site across all GVFKs

**Performance Optimization:**
- Progress tracking every 10% (3,239 combinations)
- Vectorized distance calculations where possible
- Memory-efficient processing of large datasets

**Quality Assurance:**
- 100% success rate: All 32,391 combinations matched with rivers
- No orphaned sites (sites without corresponding rivers)
- Duplicate correction: 17,139 → 16,934 unique final distances

**Distance Statistics:**

| Metric | All Combinations | Final Per Site |
|--------|------------------|----------------|
| **Range** | 0.0m - 81,437m | 0.0m - 47,116m |
| **Mean** | 6,476m | 3,486m |
| **Median** | 3,003m | 1,550m |

**Results by Site Type:**
- V2: 24,122 combinations
- V1+V2: 4,572 combinations  
- V1: 3,697 combinations

---

## Implementation Details

### Code Structure
```
Kode/
├── main_workflow.py          # Orchestrator script
├── config.py                 # Configuration and paths
├── step1_all_gvfk.py        # Step 1 implementation
├── step2_river_contact.py    # Step 2 implementation
├── step3_v1v2_sites.py      # Step 3 implementation
├── step4_distances.py       # Step 4 implementation
├── step5_risk_assessment.py # Risk analysis
└── metode_beskrivelse.md    # Updated methodology (Danish)
```

### Configuration Management
**File:** `config.py`

Key configurations:
```python
# Analysis settings
DISTANCE_CALCULATION_SETTINGS = {
    'progress_interval_percent': 10,
    'contact_filter_value': 1,
    'max_visualization_sites': 1000
}

# Risk thresholds
RISK_THRESHOLD_M = 500  # High-risk distance threshold
```

### Error Handling
- **File validation**: All input files checked before processing
- **CRS alignment**: Automatic coordinate system harmonization
- **Geometry validation**: Invalid geometries flagged and handled
- **Memory management**: Large datasets processed in chunks

---

## Results & Statistics

### Workflow Progression
| Step | Description | Count | % of Total GVFKs | % of Previous Step |
|------|-------------|-------|------------------|-------------------|
| 1 | All GVFKs | 2,043 | 100.0% | - |
| 2 | GVFKs with river contact | 593 | 29.0% | 29.0% |
| 3 | GVFKs with contamination sites | 432 | 21.1% | 72.8% |
| **Final** | **GVFKs with high-risk sites (≤500m)** | **350** | **17.1%** | **81.0%** |

### Site-Level Analysis
| Metric | Value | Percentage |
|--------|-------|------------|
| **Total unique contamination sites** | 16,934 | 100.0% |
| **High-risk sites (≤500m)** | 3,606 | 21.3% |
| **Multi-GVFK sites** | 2,969 | 17.5% |

### Risk Assessment Results (≤500m threshold)

**High-Risk Site Characteristics:**
- **Distance statistics**: 0-500m range, 232m mean, 229m median
- **Multi-GVFK impact**: 82.3% affect multiple aquifers (avg. 2.6 GVFKs each)
- **Maximum impact**: Single site affects up to 5 GVFKs

**Top Contamination Sources:**
1. **Branches**: Servicestationer (651), Autoreparationsværksteder (614), Affaldsbehandling (388)
2. **Activities**: Andet (897), Benzin/olie salg (661), Benzin/olie oplag (436)  
3. **Substances**: Tungmetaller (451), Olieprodukter (250), Fyringsolie (226)

---

## Output Files

### Primary Results
| File | Type | Content | Size |
|------|------|---------|------|
| `step1_all_gvfk.shp` | Shapefile | All GVFK boundaries | ~50MB |
| `step2_gvfk_with_rivers.shp` | Shapefile | River-connected GVFKs | ~15MB |
| `step3_v1v2_sites.shp` | Shapefile | Site-GVFK combinations | ~25MB |
| `step4_final_distances_for_risk_assessment.csv` | CSV | Final distances per site ⭐ | ~2MB |
| `step5_high_risk_sites_500m.csv` | CSV | High-risk sites analysis | ~500KB |

### Visualization Outputs
| File | Type | Purpose |
|------|------|---------|
| `interactive_distance_map.html` | HTML | Interactive exploration (1,000 sample sites) |
| `gvfk_progression.png` | PNG | Workflow progression visualization |
| `distance_histogram_thresholds.png` | PNG | Distance distribution analysis |

### Analysis Summaries
| File | Content |
|------|---------|
| `workflow_summary.csv` | Complete workflow statistics |
| `step4_site_level_summary.csv` | Site-level distance summary |
| `step5_analysis_summary_500m.csv` | Risk assessment summary |
| `step5_contamination_breakdown_500m.csv` | Contamination type analysis |

---

## Quality Assurance

### Data Validation
✅ **Input file validation**: All required files checked before processing  
✅ **Geometry validation**: Invalid geometries identified and corrected  
✅ **CRS consistency**: All datasets aligned to common coordinate system  
✅ **Attribute completeness**: Missing critical attributes flagged  

### Processing Validation
✅ **Deduplication verification**: No duplicate site-GVFK combinations in final dataset  
✅ **Distance calculation accuracy**: 100% success rate for distance computations  
✅ **Site-GVFK relationship integrity**: All sites matched to appropriate GVFKs  
✅ **Count reconciliation**: Site counts verified across all steps  

### Result Validation
✅ **Statistical consistency**: Distance ranges and distributions validated  
✅ **Spatial coherence**: Geographic patterns verified through visualization  
✅ **Risk threshold validation**: 500m threshold appropriately applied  
✅ **Multi-GVFK analysis**: Complex site-aquifer relationships correctly handled  

---

## Visualizations

### Interactive Elements
- **Distance exploration map**: 1,000 sample sites with river connections
- **Risk dashboard**: Comprehensive analysis of high-risk characteristics
- **Progression plots**: Visual workflow step progression

### Statistical Plots
- **Distance histograms**: Distribution analysis with risk thresholds
- **CDF plots**: Cumulative distribution functions for risk assessment
- **Contamination analysis**: Source, activity, and substance breakdowns

### Geographic Visualizations
- **Heatmaps**: Site density across Denmark  
- **Progression maps**: GVFK filtering through workflow steps
- **Risk zones**: High-risk areas within 500m of rivers

---

## Technical Notes

### Performance Characteristics
- **Processing time**: ~10-15 minutes for complete workflow
- **Memory usage**: Peak ~4-6GB during distance calculations  
- **Scalability**: Linear scaling with number of site-GVFK combinations

### Known Limitations
- **Shapefile field length**: Long field names truncated (warning issued)
- **Interactive map sampling**: Limited to 1,000 sites for performance
- **Distance precision**: Limited by input geometry resolution

### Future Enhancements
- **Parallel processing**: Distance calculations could be parallelized
- **Advanced risk modeling**: Additional contamination severity weighting
- **Real-time updates**: Automated processing of new contamination data

---

**Document Version:** Technical Reference v1.0  
**Last Updated:** December 2024  
**Maintainer:** Oliver Lund  
**For questions or updates, refer to the main workflow scripts in the `Kode/` directory.** 