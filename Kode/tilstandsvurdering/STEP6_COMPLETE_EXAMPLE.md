# Step 6: Complete Calculation Example

**River Segment:** DKRIVER1234  
**Contributing Sites:** 5 sites (4 with chlorinated solvents, 1 with polar compounds)  
**Categories:** 4 (KLOREREDE_OPLØSNINGSMIDLER, KLOREDE_KULBRINTER, POLARE_FORBINDELSER, UORGANISKE_FORBINDELSER)

---

## STEP 1: SITE-LEVEL FLUX CALCULATIONS

Each site generates **multiple scenario rows** based on the modelstoffer in each category.

### Site 461-00119
- **Area:** 468.3 m²
- **Infiltration:** 141.4 mm/yr
- **Distance to river:** 84.9 m
- **Categories detected:** KLOREDE_KULBRINTER, KLOREREDE_OPLØSNINGSMIDLER, UORGANISKE_FORBINDELSER

**Scenarios generated (10 rows):**

| Scenario | Concentration (µg/L) | Flux (kg/yr) |
|----------|---------------------|--------------|
| KLOREDE_KULBRINTER__via_1,1,1-Trichlorethan | 100.0 | 0.006623 |
| KLOREDE_KULBRINTER__via_Trichlorethylen | 42,000.0 | 2.781793 |
| KLOREDE_KULBRINTER__via_Chloroform | 100.0 | 0.006623 |
| KLOREDE_KULBRINTER__via_Chlorbenzen | 100.0 | 0.006623 |
| KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan | 100.0 | 0.006623 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen | 42,000.0 | 2.781793 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform | 100.0 | 0.006623 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen | 100.0 | 0.006623 |
| UORGANISKE_FORBINDELSER__via_Arsen | 100.0 | 0.006623 |
| UORGANISKE_FORBINDELSER__via_Cyanid | 3,500.0 | 0.231816 |

**Key point:** Same site produces different flux values for each scenario because concentrations vary (100 vs 42,000 µg/L for TCE).

---

### Site 461-00126
- **Area:** 404.7 m²
- **Infiltration:** 141.4 mm/yr
- **Distance:** 143.5 m
- **Category:** KLOREREDE_OPLØSNINGSMIDLER only

**Scenarios (4 rows):**

| Scenario | Concentration | Flux (kg/yr) |
|----------|--------------|--------------|
| KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan | 100.0 | 0.005724 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen | 42,000.0 | 2.403875 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform | 100.0 | 0.005724 |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen | 100.0 | 0.005724 |

---

### Site 461-00132, 461-56015
Similar to above - each generates 4 scenarios for KLOREREDE_OPLØSNINGSMIDLER.

---

### Site 461-04075
- **Area:** 876.7 m²
- **Infiltration:** 9.4 mm/yr (very low!)
- **Distance:** 87.7 m
- **Category:** POLARE_FORBINDELSER

**Scenarios (2 rows):**

| Scenario | Concentration | Flux (kg/yr) |
|----------|--------------|--------------|
| POLARE_FORBINDELSER__via_MTBE | 50,000.0 | 0.412056 |
| POLARE_FORBINDELSER__via_4-Nonylphenol | 9.0 | 0.000074 |

**Note:** Even with high concentration (50,000 µg/L), low infiltration keeps flux moderate.

---

## STEP 2: SEGMENT-LEVEL FLUX AGGREGATION

**Sum flux across all sites by matching scenario name.**

Example: **KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen**

```
Site 461-00119:  2.781793 kg/yr
Site 461-00126:  2.403875 kg/yr
Site 461-00132:  1.386777 kg/yr
Site 461-56015: 11.498449 kg/yr
                ─────────────────
TOTAL:          18.070893 kg/yr  ← This goes to the river segment
```

**All scenarios for this segment:**

| Scenario | Total Flux (kg/yr) | Contributing Sites |
|----------|-------------------|-------------------|
| KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen | 18.070893 | 4 sites |
| KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan | 0.043026 | 4 sites |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform | 0.043026 | 4 sites |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen | 0.043026 | 4 sites |
| KLOREDE_KULBRINTER__via_Trichlorethylen | 2.781793 | 1 site |
| POLARE_FORBINDELSER__via_MTBE | 0.412056 | 1 site |
| (+ 6 more scenarios) | ... | ... |

**Total: 12 scenario rows for this segment**

---

## STEP 3: CMIX CALCULATION (Mixing Concentration)

**River flow data:**
- **Mean flow:** 4.221 m³/s = 4,221 L/s
- **Q90 flow:** 1.243 m³/s = 1,243 L/s (dry conditions)
- **Q95 flow:** 1.126 m³/s = 1,126 L/s (very dry)

### Example: KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen (Mean flow)

**Step-by-step calculation:**

1. **Total flux:** 18.070893 kg/yr = 1.807 × 10¹⁰ µg/yr

2. **Flux per second:**
   ```
   Flux_ug_s = 1.807 × 10¹⁰ µg/yr ÷ 31,557,600 s/yr
             = 572.632 µg/s
   ```

3. **Flow in liters:**
   ```
   Flow = 4.221 m³/s × 1000 L/m³ = 4,221 L/s
   ```

4. **Cmix (mixing concentration):**
   ```
   Cmix = 572.632 µg/s ÷ 4,221 L/s
        = 0.1357 µg/L
   ```

**Same calculation for all 3 flow scenarios:**

| Flow Scenario | Flow (L/s) | Cmix (µg/L) |
|--------------|-----------|-------------|
| Mean | 4,221 | 0.1357 |
| Q90 (dry) | 1,243 | 0.4608 |
| Q95 (very dry) | 1,126 | 0.5085 |

**Key insight:** Lower flow → higher concentration (less dilution)

---

## STEP 4: MKK COMPARISON & EXCEEDANCE CALCULATION

**MKK (Environmental Quality Standard) for KLOREREDE_OPLØSNINGSMIDLER category:** 2.5 µg/L

(This is the strictest MKK among the 4 modelstoffer in this category: Chloroform = 2.5 µg/L)

**Exceedance ratio:**
```
Ratio = Cmix ÷ MKK
```

### Results for KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen:

| Flow Scenario | Cmix (µg/L) | MKK (µg/L) | Ratio | Exceeds? |
|--------------|-------------|------------|-------|----------|
| Mean | 0.1357 | 2.5 | 0.05× | ✓ NO |
| Q90 | 0.4608 | 2.5 | 0.18× | ✓ NO |
| Q95 | 0.5085 | 2.5 | 0.20× | ✓ NO |

**Conclusion:** Even with 18 kg/yr of contamination and low flow (Q95), the mixing concentration is only 20% of the MKK threshold. **No exceedance.**

---

## COMPLETE RESULTS FOR ALL SCENARIOS AT DKRIVER1234

### Summary Table (Mean Flow)

| Scenario | Total Flux (kg/yr) | Cmix (µg/L) | MKK (µg/L) | Ratio | Status |
|----------|-------------------|-------------|------------|-------|--------|
| **KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen** | 18.071 | 0.1357 | 2.5 | 0.05× | ✓ OK |
| KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan | 0.043 | 0.0003 | 2.5 | 0.00× | ✓ OK |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform | 0.043 | 0.0003 | 2.5 | 0.00× | ✓ OK |
| KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen | 0.043 | 0.0003 | 2.5 | 0.00× | ✓ OK |
| **KLOREDE_KULBRINTER__via_Trichlorethylen** | 2.782 | 0.0209 | 2.5 | 0.01× | ✓ OK |
| POLARE_FORBINDELSER__via_MTBE | 0.412 | 0.0031 | 10.0 | 0.00× | ✓ OK |
| POLARE_FORBINDELSER__via_4-Nonylphenol | 0.000074 | 0.0000 | 10.0 | 0.00× | ✓ OK |
| UORGANISKE_FORBINDELSER__via_Cyanid | 0.232 | 0.0017 | 4.3 | 0.00× | ✓ OK |
| (+ 4 more low-flux scenarios) | ... | ... | ... | ... | ✓ OK |

**All scenarios pass MKK thresholds** - River segment DKRIVER1234 is within environmental quality standards.

---

## KEY TAKEAWAYS

1. **Scenario-based approach works correctly:**
   - 5 sites generate 30+ scenario rows
   - Each scenario aggregates properly at segment level
   - Same area/infiltration produces different flux for each modelstof concentration

2. **Multiple flow scenarios capture uncertainty:**
   - Mean flow: "Normal" conditions
   - Q90/Q95: Dry conditions with less dilution
   - Cmix can be 3-4× higher in dry conditions

3. **MKK comparison is scenario-specific:**
   - Each scenario uses the category's MKK threshold
   - Categories with multiple modelstoffer: Use strictest MKK among them
   - Exceedance ratio shows "safety margin"

4. **This segment is low risk:**
   - Despite 18 kg/yr TCE flux from 4 sites
   - High river flow (4.2 m³/s) provides good dilution
   - Even in Q95 conditions, only 20% of MKK threshold

---

**Files:**
- Site-level: `step6_flux_site_segment.csv`
- Segment-level: `step6_flux_by_segment.csv`
- Cmix results: `step6_cmix_results.csv`
