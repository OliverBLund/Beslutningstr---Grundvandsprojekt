# How GVD Rasters Are Used in Step 6

## Simple Explanation

**Input:** GVD rasters (one per DK-modellag: ks1, ks2, ks3, ps1, etc.)
- Each raster = groundwater formation (infiltration) in mm/year for that aquifer layer

**Process:**

1. **Site location**: Site 101-00002 at coordinates (X, Y)

2. **Which aquifer?**: Step 5 determined this site is in GVFK "dkms_3307_ks" which uses layer "ks2"

3. **Sample infiltration**: 
   - Open: `DKM_gvd_ks2.tif`
   - Sample at (X, Y)
   - Result: 76.76 mm/year

4. **Calculate flux for each substance**:
   ```
   Flux = Area × Infiltration × Concentration
   Flux = 581,621 m² × 76.76 mm/year × 1,800 µg/L = 80.36 kg/year
   ```

## Key Points

- **One site location** → samples ONE raster per modellag
- **One modellag** → ONE infiltration value per site
- **Multiple substances** → multiple flux values (same infiltration, different concentrations)
- **Multiple GVFKs** → if site affects multiple GVFKs with different modellags, sample multiple rasters

## Why Negative Values Exist

GVD rasters contain **net vertical flux**:
- **Positive** = recharge zone (water infiltrates downward)
- **Negative** = discharge zone (groundwater flows upward to surface)

**Our fix**: Set negative to zero
- Rationale: Surface contamination can't infiltrate downward in discharge zones
- Impact: ~45% of rows had negative infiltration → now zero flux

## Data Flow

```
Site centroid (X,Y) 
  ↓
Step 5: Determine which GVFK → which DK-modellag (ks1, ks2, etc.)
  ↓
Step 6: Sample DKM_gvd_{modellag}.tif at (X,Y) → get infiltration
  ↓
For each substance: Flux = Area × Infiltration × Concentration
```
