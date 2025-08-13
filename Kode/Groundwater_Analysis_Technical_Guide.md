# Groundwater Contamination Analysis: Technical Step-by-Step Guide

## Data Files Used

### Primary Input Files
- **VP3Genbesøg_grundvand_geometri.shp**: Groundwater aquifer geometries (2,043 features)
- **Rivers_gvf_rev20230825_kontakt.shp**: River segments with aquifer contact flags (14,454 features, 7,496 with contact=1)
- **V1FLADER.shp**: V1 contamination site polygons (28,717 polygons, 23,209 unique sites)
- **V2FLADER.shp**: V2 contamination site polygons (33,040 polygons, 21,269 unique sites)
- **Data/v1_gvfk_forurening.csv**: V1 site attributes and contamination data (84,601 rows)
- **Data/v2_gvfk_forurening.csv**: V2 site attributes and contamination data (134,636 rows)

### Key Data Columns
- **Lokalitetensbranche**: Industry/sector classification
- **Lokalitetensaktivitet**: Activity type
- **Lokalitetensstoffer**: Contamination substances (used for active contamination filtering)

---

## Step 1: Aquifer Inventory

### Input Data
- `VP3Genbesøg_grundvand_geometri.shp`

### Technical Procedure
1. Load shapefile using GeoPandas
2. Extract unique values from "Navn" column
3. Count total unique groundwater aquifers (GVFK)
4. Export geometry to output shapefile

### Output Files
- `step1_all_gvfk.shp`

### Results
- **2,043 unique groundwater aquifers** identified

---

## Step 2: River Contact Identification

### Input Data
- `Rivers_gvf_rev20230825_kontakt.shp`
- Output from Step 1

### Technical Procedure
1. Load river segments shapefile (14,454 features)
2. Filter segments where `Kontakt = 1` (7,496 segments)
3. Extract unique GVFK names from "GVForekom" column
4. Create subset of aquifer geometries with river contact
5. Export filtered aquifer polygons

### Output Files
- `step2_gvfk_with_rivers.shp`

### Results
- **593 aquifers have river contact** (29.0% of total)
- 588 aquifer geometries saved with river contact
- 5 missing due to name mismatch between newer gvfk file (VP3Genbesøg_grundvand_geometri.shp), which have different gvfk than when Rivers_gvf_rev20230825_kontakt.shp was created.

---

## Step 3: V1/V2 Site Processing and Active Contamination Filtering

### Input Data
- `Data/v1_gvfk_forurening.csv`
- `Data/v2_gvfk_forurening.csv`
- `V1FLADER.shp`
- `V2FLADER.shp`
- Output from Step 2 (aquifers with river contact)

### Technical Procedure

#### 3.1 CSV Data Filtering
1. **Active Contamination Filter**: Remove rows where `Lokalitetensstoffer` is NaN or empty
   - V1: 84,601 → 34,232 rows (60% reduction, removed 50,369 inactive sites)
   - V2: 134,636 → 121,984 rows (9% reduction, removed 12,652 inactive sites)

2. **River Contact Filter**: Keep only sites in aquifers with river contact from Step 2

#### 3.2 Geometry Processing
1. Load V1/V2 shapefiles
2. Dissolve geometries by `Lokalitets` column to get one geometry per site
3. Join CSV data with geometries based on site numbers

#### 3.3 Deduplication
1. **Within-dataset deduplication**:
   - V1: 21,697 → 8,269 unique site-GVFK combinations
   - V2: 79,893 → 28,694 unique site-GVFK combinations

2. **Cross-dataset deduplication**: Remove 4,572 duplicate site-GVFK combinations between V1 and V2

3. **Multi-dataset classification**: Sites appearing in both V1 and V2 marked as "V1 og V2"

### Output Files
- `step3_v1v2_sites.shp`: All site-GVFK combinations with geometry
- `step3_gvfk_with_v1v2.shp`: Aquifer polygons containing V1/V2 sites
- `step3_site_gvfk_relationships.csv`: Detailed relationships with contamination data

### Results
- **16,934 unique V1/V2 sites** with active contamination
- **32,391 total site-GVFK combinations** after deduplication
- **432 aquifers contain V1/V2 sites** (21.1% of total aquifers)
- Average 1.9 aquifers per site

#### Site Distribution by Type
- **V2**: 12,663 sites (72.2%)
- **V1 og V2**: 2,398 sites (13.7%)
- **V1**: 1,873 sites (14.1%)

---

## Step 4: Distance Calculation

### Input Data
- Output from Step 3 (V1/V2 sites with contamination data)
- `Rivers_gvf_rev20230825_kontakt.shp` (filtered for `Kontakt = 1`)

### Technical Procedure

#### 4.1 Distance Calculation Method
1. **For each site-GVFK combination from Step 3**:
   - Identify river segments with `Kontakt = 1` in the same GVFK
   - Calculate minimum distance using `geometry.distance()` method
   - Preserve all contamination attributes (branch, activity, substances)

#### 4.2 Final Distance Determination
1. **For sites in multiple aquifers**: Identify shortest distance across all aquifer-river combinations
2. **Mark minimum distance**: Set `Is_Min_Distance = True` for the shortest distance per site
3. **Preserve multi-aquifer information**: Keep data on all affected aquifers

#### 4.3 Distance Calculation Formula
- **GeoPandas distance calculation**: `site_geometry.distance(river_geometry)`
- **Units**: Meters (based on coordinate reference system)
- **Scope**: Within-aquifer distances only (site to rivers in same GVFK)

### Output Files
- `step4_distance_results.csv`: All site-GVFK combinations with distances
- `step4_valid_distances.csv`: Only combinations with valid distance calculations
- `step4_final_distances_for_risk_assessment.csv`: **Final distances per site** (primary output)
- `unique_lokalitet_distances.csv`: For visualization purposes
- `v1v2_sites_with_distances.shp`: Shapefile with all distance data
- `step4_site_level_summary.csv`: Site-level summary statistics
- `interactive_distance_map.html`: Interactive map with sample data (1,000 sites)

### Key Output Columns for Step 5
- `Final_Distance_m`: Shortest distance per site
- `Lokalitetensbranche`: Industry/sector
- `Lokalitetensaktivitet`: Activity type
- `Lokalitetensstoffer`: Contamination substances
- `Total_GVFKs_Affected`: Number of aquifers affected per site

### Results
- **32,391 site-GVFK combinations** with calculated distances (100% success rate)
- **16,934 unique sites** with final distances

#### Distance Statistics
- **All combinations**: 0.0m - 81,437m (mean: 6,476m, median: 3,003m)
- **Final distances per site**: 0.0m - 47,116m (mean: 3,486m, median: 1,550m)

#### Distance Calculations by Site Type
- **V2**: 24,122 site-GVFK combinations
- **V1 og V2**: 4,572 site-GVFK combinations
- **V1**: 3,697 site-GVFK combinations

---

## Step 5 (EXPERIMENTAL; NOTHING IS DECIED YET): Risk Assessment (500m Threshold)

### Input Data
- `step4_final_distances_for_risk_assessment.csv`

### Technical Procedure

#### 5.1 Distance Filtering
- **Filter criteria**: `Final_Distance_m ≤ 500` meters
- **Risk threshold**: Sites within 500m of rivers considered high-risk

#### 5.2 Risk Analysis Categories
1. **Industry Risk** (`Lokalitetensbranche`): Analysis by industrial sector
2. **Activity Risk** (`Lokalitetensaktivitet`): Analysis by activity type
3. **Substance Risk** (`Lokalitetensstoffer`): Analysis by contamination substances
4. **Multi-Aquifer Impact** (`Total_GVFKs_Affected`): Sites affecting multiple aquifers

### Output Files
- `step5_analysis_summary_500m.csv`: Summary statistics
- `step5_contamination_breakdown_500m.csv`: Detailed contamination analysis
- `step5_high_risk_sites_500m.csv`: High-risk site list
- `step5_gvfk_high_risk_500m.shp`: Aquifers containing high-risk sites
- Visualization outputs in `Resultater/Figures/Step5_Risk_Analysis/`

### Results

#### High-Risk Site Summary
- **3,606 high-risk sites** within 500m of rivers (21.3% of all sites)
- **350 aquifers contain high-risk sites** (17.1% of all aquifers, 81.0% of V1/V2 aquifers)
- **Distance statistics for high-risk sites**: 0.0m - 500.0m (mean: 232m, median: 229m)

#### High-Risk Sites by Type
- **V2**: 2,605 sites (72.2%)
- **V1 og V2**: 560 sites (15.5%)
- **V1**: 441 sites (12.2%)

#### Top 5 Contamination Categories
**Industries (Lokalitetensbranche)**:
1. Servicestationer: 651 sites
2. Autoreparationsværksteder: 614 sites
3. Affaldsbehandling: 388 sites
4. Industri og håndværk: 313 sites
5. Anden virksomhed: 206 sites

**Activities (Lokalitetensaktivitet)**:
1. Andet: 897 sites
2. Benzin/olie salg: 661 sites
3. Benzin/olie oplag: 436 sites
4. Reparation af motorkøretøjer: 345 sites
5. Benzin/olie salg og vask: 304 sites

**Substances (Lokalitetensstoffer)**:
1. Tungmetaller: 451 sites
2. Olieprodukter: 250 sites
3. Fyringsolie: 226 sites
4. Tungmetaller, Olieprodukter: 185 sites
5. Benzin: 179 sites

#### Multi-Aquifer Impact Analysis
- **2,969 sites** (82.3%) affect multiple aquifers
- **Average 2.6 aquifers** per multi-aquifer site
- **Maximum 5 aquifers** affected by single site

---

## Technical Summary

### Data Processing Statistics
- **Starting data**: 219,237 total contamination records (V1+V2)
- **Active contamination filtering**: 156,216 records retained (71% overall retention)
- **Final analysis scope**: 16,934 unique sites with active contamination and river proximity
- **Distance calculations**: 32,391 site-aquifer combinations processed
- **Risk assessment**: 3,606 high-risk sites identified

### Quality Assurance Measures
1. **Active contamination verification**: Only sites with documented contamination substances included
2. **Geometric validation**: All site-aquifer spatial relationships verified
3. **Distance calculation validation**: 100% success rate for distance calculations
4. **Deduplication**: Systematic removal of duplicate site-aquifer combinations
5. **Data preservation**: All contamination attributes maintained through processing pipeline

### Output File Summary
- **Step 1**: 1 shapefile (aquifer inventory)
- **Step 2**: 1 shapefile (aquifers with river contact)
- **Step 3**: 3 files (sites, aquifers, relationships)
- **Step 4**: 6 files (distances, summaries, interactive map)
- **Step 5**: 4 files (risk analysis, high-risk sites)
- **Total**: 15 primary output files + visualizations 

