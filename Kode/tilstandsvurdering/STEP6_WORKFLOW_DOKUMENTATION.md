# Step 6: Tilstandsvurdering - Komplet Workflow Dokumentation

## Formål

Step 6 beregner forureningsflux fra forurenede lokaliteter til vandløbssegmenter gennem grundvandspathways, og vurderer påvirkningen på overfladevandskvalitet ved at sammenligne beregnede koncentrationer med miljøkvalitetskriterier (MKK).

---

## Overordnet Dataflow

```
Input: Step 5 resultater
  ↓
  Én række per: Lokalitet × GVFK × Stof × Vandløb
  ↓
Sample GVD-rastere (infiltration pr. akvifer-lag)
  ↓
  Samme lokalitet kan sample FORSKELLIGE rastere for forskellige GVFK/lag
  ↓
Beregn lag- og lokalitetsspecifik infiltration som gennemsnit af rasterværdier inden for lokalitetspolygonen (falder tilbage til centroid-sampling hvis polygonen ligger i no-data)
  ↓
Filtrer negative infiltrationsværdier (opstrømningszoner fjernes)
  ↓
Beregn flux (J = A × C × I)
  ↓
  Output: Én flux-værdi per: Lokalitet × GVFK × Stof × Vandløb
  STOFFER HOLDES ADSKILTE
  ↓
Aggregér flux til vandløbssegmenter
  ↓
  Gruppér efter: Vandløb × GVFK × Stof (← Stof er IKKE summeret!)
  Summer flux fra MULTIPLE lokaliteter for SAMME stof
  ↓
  Output: Én total flux per: Vandløb × GVFK × Stof
  ↓
Beregn Cmix (fortynding med vandløbsflow)
  ↓
  3 scenarier (Mean, Q90, Q95) × Per stof separat
  Cmix_stofX = Flux_stofX / Flow
  ALDRIG: Cmix = (Flux_stofA + Flux_stofB) / Flow  ❌
  ↓
  Output: Én Cmix per: Vandløb × GVFK × Stof × Flow-scenarie
  ↓
Sammenlign med MKK-tærskler
  ↓
  MKK-sammenligning: Per stof individuelt
  Exceedance_stofX = Cmix_stofX / MKK_stofX
  ↓
Output: Flux, koncentrationer, overskridelser (ALT per stof separat)
```

**NØGLEPRINCIP:** 
Stoffer holdes ALTID adskilte gennem hele pipelinen. Der sker ALDRIG summering på tværs af forskellige stoffer. Hver stof evalueres individuelt mod sin egen MKK-tærskel.

---

## Input Data

### 1. Step 5 Resultater
**Fil:** `Resultater/step5_compound_detailed_combinations.csv`

**Indhold:**
- Lokalitet_ID, navn, areal, koordinater
- GVFK (grundvandsforekomst)
- Stoffer og kategorier
- Afstand til nærmeste vandløb
- Branche/aktivitet information

**Struktur:** Én række per lokalitet-GVFK-stof-vandløb kombination

### 2. GVD Rastere (Grundvandsdannelse)
**Placering:** `GVD_RASTER_DIR/DKM_gvd_{lag}.tif`

**Filer:** 
- `DKM_gvd_ks1.tif`, `DKM_gvd_ks2.tif`, `DKM_gvd_ks3.tif`, osv.
- `DKM_gvd_ps1.tif`, `DKM_gvd_ps2.tif`, osv.
- `DKM_gvd_kalk.tif`, `DKM_gvd_lag12.tif`

**Værdier:**
- Enhed: mm/år
- Positiv: Infiltrationszone (vand siver nedad)
- Negativ: Opstrømningszone (grundvand strømmer opad)

### 3. GVFK-Lag Mapping
**Fil:** `Data/vp3_h1_grundvandsforekomster_VP3Genbesøg.csv`

**Indhold:** Mapping fra GVFK til DK-modellag
```
GVForekom        DK-modellag
dkms_3307_ks  →  ks2
dkmj_1010_ks  →  ks4
dkmj_16_ks    →  ks1 - ks2
```

### 4. Vandløb Shapefile
**Fil:** `Shapes/Rivers_gvf_rev20230825_kontakt.shp`

**Relevante felter:**
- `ov_id`, `ov_navn`: Vandløbs-ID og navn
- `GVForekom`: GVFK som vandløbet er i
- `Kontakt`: Binær flag (1 = har grundvandskontakt)
- `Flux_mag`: Opadgående flux fra akvifer til vandløb (mm/år)

### 5. Vandløbsflow Data
**Fil:** `Data/dkm2019_vp3_qpunkter_inklq95/dkm_qpoints_gvf_rev20230825_kontakt_inklQ95.shp`

**Felter:**
- `Mean`: Gennemsnitsflow (m³/s)
- `Q90`: Flow overskredet 90% af tiden (m³/s)
- `Q95`: Flow overskredet 95% af tiden (m³/s)

### 6. Standardkoncentrationer (Hardcoded i Koden)
**Placering:** `step6_tilstandsvurdering.py` - `STANDARD_CONCENTRATIONS` dictionary

**Kilder:**
- **Delprojekt 3 (D3) Modelstoffer:** 90% fraktil-værdier fra Tabel 3-18
- **Branche/aktivitet-specifikke:** Servicestationer (8000 µg/L Benzen), Villaolietanke (6000 µg/L Olie), Renserier (42000 µg/L TCE)
- **Losseplads-specifikke:** Lavere værdier pga. fortynding (17 µg/L Benzen, 2500 µg/L Olie)
- **Kategori-fallbacks:** Konservative worst-case værdier (BTXER: 1500 µg/L, PFAS: 500 µg/L)

**Hierarki (4 niveauer):**
1. Branche/Aktivitet + Stof (mest specifik) - f.eks. "Servicestationer_Benzen"
2. Losseplads + Stof/Kategori - f.eks. "Benzen" i losseplads-kontekst
3. Specifikt stofnavn - f.eks. "Benzen" generelt
4. Kategori - f.eks. "BTXER"

**Stof-til-kategori-forhold:**
- Hver compound i data tilhører én kategori (f.eks. Benzen → BTXER, Arsen → UORGANISKE_FORBINDELSER)
- Koden har BÅDE compound-specifikke OG kategori-værdier
- Opslag: Compound-navn FØRST, derefter kategori som FALLBACK
- Eksempel: Benzen (400 µg/L specifik) foretrækkes over BTXER (1500 µg/L kategori)
- Eksempel: Toluen (ingen specifik værdi) bruger BTXER (1500 µg/L kategori)

### 7. MKK-Tærskler (Hardcoded i Koden)
**Placering:** `step6_tilstandsvurdering.py` - `MKK_THRESHOLDS` dictionary

**Kilder:**
- **BEK nr. 1022 af 25/08/2010 - Bilag 3:** EU Environmental Quality Standards (EQS)
  - Benzen: 10 µg/L
  - Trichlorethylen: 10 µg/L
  - Fluoranthen: 0.1 µg/L
  - Atrazin: 0.6 µg/L
  - Nonylphenol: 0.3 µg/L
  - m.fl.

- **BEK nr. 1022 af 25/08/2010 - Bilag 2:** Nationale EQS værdier
  - 1,1,1-Trichlorethan: 21 µg/L
  - Phenol: 7.7 µg/L
  - MTBE: 10 µg/L
  - Arsen: 4.3 µg/L
  - Mechlorprop: 18 µg/L
  - 2,6-dichlorphenol: 3.4 µg/L
  - Dichlormethan: 20 µg/L

- **BEK 796/2023 (Miljøstyrelsen nov 2024):** PFAS-specifikke tærskler
  - PFOS: 0.00065 µg/L (ferskvand)
  - TFA: 560 µg/L (ferskvand)
  - PFOA: 0.0044 µg/L (PFAS_24 gruppe-EQS)
  - Øvrige PFAS: 0.0044 µg/L (anvendes som generel PFAS-EQS)

- **Kategori-tærskler:** Afledt som LAVESTE (strammeste) EQS blandt kategoriens modelstoffer
  - BTXER: 10 µg/L (fra Benzen)
  - PAH_FORBINDELSER: 0.1 µg/L (fra Fluoranthen)
  - PHENOLER: 0.3 µg/L (fra Nonylphenol)
  - KLOREREDE_OPLØSNINGSMIDLER: 2.5 µg/L (fra Chloroform)
  - PESTICIDER: 0.6 µg/L (fra Atrazin)
  - UORGANISKE_FORBINDELSER: 4.3 µg/L (fra Arsen)
  - PFAS: 0.0044 µg/L (PFAS_24 gruppe)

- **Konservative værdier:** For stoffer uden specifik EQS
  - Lossepladsperkolat: 10 µg/L
  - COD: 1000 µg/L
  - Cyanid: 10 µg/L

**MKK-dækning:** 100% - Alle stoffer har enten stof-specifik eller kategori-baseret tærskel

**Stof-til-kategori-forhold (samme som koncentrationer):**
- Data tildeler: Benzen → BTXER, Fluoranthen → PAH_FORBINDELSER, Nikkel → UORGANISKE_FORBINDELSER
- Koden har BÅDE stof-specifikke OG kategori-tærskler
- Opslag: Stofnavn FØRST, derefter kategori som FALLBACK
- Kategori-tærskel = MEST STRINGENT (laveste) blandt medlemmerne
- Eksempel 1: Benzen (10 µg/L specifik) = BTXER (10 µg/L, afledt fra Benzen)
- Eksempel 2: Naphtalen (ingen specifik) bruger PAH_FORBINDELSER (0.1 µg/L fra Fluoranthen)
- Eksempel 3: Nikkel (ingen specifik) bruger UORGANISKE_FORBINDELSER (4.3 µg/L fra Arsen)

---

## Beregningsprocessen - Trin for Trin

### Trin 1: Forberedelse af Input Data

**Funktion:** `_prepare_flux_inputs()`

**Proces:**
1. Indlæs Step 5 resultater
2. Merge med GVFK-lag mapping
3. Hent lokalitet-geometrier (centroids)
4. Tilknyt vandløbsmetadata

**Output:** Én række per lokalitet-GVFK-stof-vandløb kombination

**Eksempel:**
```
Lokalitet_ID: 101-00002
GVFK: dkms_3307_ks
DK-modellag: ks2
Stof: Landfill Override: UORGANISKE_FORBINDELSER
Vandløb: Harrestrup Å
```

---

### Trin 2: Beregning af Infiltration

**Funktion:** `_calculate_infiltration()`

**Proces:**
1. Parse DK-modellag (f.eks. "ks1 - ks2" → ["ks1", "ks2"])
2. For hvert lag:
   - Åbn `DKM_gvd_{lag}.tif`
   - Maskér rasteren med hele lokalitetspolygonen og beregn gennemsnit/min/max af alle gyldige pixels (antal pixler logges)
   - Sample altid et centroidpunkt (bruges både som fallback og til QA)
   - Hvis polygonen falder udenfor rasteren → centroidværdi anvendes som fallback for dette lag
3. Hvis multiple lag: Tag gennemsnit af lag-værdier (separat for kombineret/polygon/centroid)

**Specialtilfælde:**
- Negative værdier: Rækker fjernes helt (opstrømningszoner)
- Manglende data (polygon + centroid uden værdi): Række fjernes fra analyse
- QA-data: Hver række gemmer både polygon-gennemsnit, polygon-min/max, pixel-antal og centroid-sample, + differencer i eksportfilen

**Eksempel:**
```
Lokalitetspolygon: 351,933 m² (Sørup Losseplads)
DK-modellag: ks2
Polygon-gennemsnit af DKM_gvd_ks2.tif → 76.8 mm/år
```

---

### Trin 3: Opslag af Standardkoncentrationer

**Funktion:** `_lookup_standard_concentration()`

**Hierarki (4 niveauer):**

1. **Branche/Aktivitet + Stof** (mest specifik)
   ```python
   "Servicestationer_Benzen": 8000 µg/L
   ```

2. **Losseplads + Stof** 
   ```python
   "Benzen": 17 µg/L  # for lossepladser
   ```

3. **Stofnavn** (fra Delprojekt 3)
   ```python
   "Benzen": 400 µg/L  # generel
   ```

4. **Kategori** (fallback)
   ```python
   "BTXER": 1500 µg/L
   ```

**Eksempel opslag:**
```
Lokalitet: Servicestationer
Stof: Benzen
→ Niveau 1 match: "Servicestationer_Benzen" = 8000 µg/L
```

---

### Trin 4: Beregning af Flux

**Funktion:** `_calculate_flux()`

**Formel:**
```
Flux (kg/år) = Areal (m²) × Infiltration (mm/år) × Koncentration (µg/L) / 10⁹
```

**Eksempel:**
```
Areal: 581,621 m²
Infiltration: 76.76 mm/år
Koncentration: 1,800 µg/L

Flux = 581,621 × 76.76 × 1,800 / 10⁹
     = 80.36 kg/år
```

**Output fil:** `step6_flux_site_segment.csv`
- Én række per lokalitet-GVFK-stof-vandløb
- Inkluderer: Flux, infiltration, koncentration, afstand til vandløb

---

### Trin 5: Aggregering til Vandløbssegmenter

**Funktion:** `_aggregate_flux_by_segment()`

**Gruppering:**
```python
group_by = [
    "Nearest_River_FID",      # Vandløbssegment
    "River_Segment_GVFK",     # GVFK
    "Qualifying_Category",    # Kategori
    "Qualifying_Substance"    # Stof (IKKE summeret på tværs!)
]
```

**Hvad sker der ved aggregering:**
- Summer flux fra MULTIPLE lokaliteter for SAMME stof til SAMME vandløb
- Tæl bidragende lokaliteter
- Gem lokalitet-IDer (kommasepareret)
- **KRITISK:** Hver stof får sin EGEN række - stoffer summeres ALDRIG sammen

**Detaljeret eksempel:**

**Input (step6_flux_site_segment.csv):**
```
Lokalitet_ID    Vandløb          GVFK         Stof                           Flux_kg_yr
101-00001       Værebro Å        dkms_3098    UORGANISKE_FORBINDELSER        56.5
101-00002       Værebro Å        dkms_3098    UORGANISKE_FORBINDELSER        12.3
101-00003       Værebro Å        dkms_3098    Benzen                          0.8
101-00004       Værebro Å        dkms_3098    Benzen                          1.2
101-00005       Værebro Å        dkms_3098    PFAS                            0.05
```

**Output efter aggregering (step6_flux_by_segment.csv):**
```
Vandløb          GVFK         Stof                           Total_Flux_kg_yr  Site_Count  Site_IDs
Værebro Å        dkms_3098    UORGANISKE_FORBINDELSER        68.8              2           101-00001, 101-00002
Værebro Å        dkms_3098    Benzen                          2.0              2           101-00003, 101-00004
Værebro Å        dkms_3098    PFAS                            0.05             1           101-00005
```

**Bemærk:**
- UORGANISKE_FORBINDELSER: 56.5 + 12.3 = 68.8 kg/år (2 lokaliteter summeret)
- Benzen: 0.8 + 1.2 = 2.0 kg/år (2 lokaliteter summeret)
- PFAS: 0.05 kg/år (1 lokalitet)
- **De 3 stoffer er i SEPARATE rækker - INGEN summering på tværs**
- Total flux i vandløbet er 68.8 + 2.0 + 0.05 = 70.85 kg/år, men dette tal bruges KUN til oversigter
- Ved Cmix-beregning bruges ALTID stof-specifikke flux-værdier

---

### Trin 6: Beregning af Cmix (Fortynding)

**Funktion:** `_calculate_cmix()`

**Formel:**
```
Flux (µg/s) = Flux (µg/år) / (365.25 × 24 × 3600)
Cmix (µg/L) = Flux (µg/s) / (Flow (m³/s) × 1000)
```

**KRITISK:** Cmix beregnes ALTID individuelt per stof med kun det pågældende stofs flux.

**Tre flow-scenarier:**
- **Mean:** Gennemsnitsflow (typiske forhold)
- **Q90:** Lavvande (overskredet 90% af tiden)
- **Q95:** Meget lavvande (overskredet 95% af tiden)

Lavere flow → Højere Cmix → Højere overskridelse

**Komplet eksempel (fortsættelse af Værebro Å):**

**Input fra aggregering:**
```
Vandløb: Værebro Å
Flow_Mean: 0.0072 m³/s
Flow_Q90: 0.0034 m³/s

Stof                           Flux_kg_yr    Flux_µg_s
UORGANISKE_FORBINDELSER        68.8          2.181×10⁶
Benzen                         2.0           6.342×10⁴
PFAS                           0.05          1.586×10³
```

**Cmix-beregninger (HVER stof separat):**

**Stof 1: UORGANISKE_FORBINDELSER**
```
Mean: Cmix = 2.181×10⁶ / (0.0072 × 1000) = 303 µg/L
Q90:  Cmix = 2.181×10⁶ / (0.0034 × 1000) = 641 µg/L
```

**Stof 2: Benzen**
```
Mean: Cmix = 6.342×10⁴ / (0.0072 × 1000) = 8.8 µg/L
Q90:  Cmix = 6.342×10⁴ / (0.0034 × 1000) = 18.7 µg/L
```

**Stof 3: PFAS**
```
Mean: Cmix = 1.586×10³ / (0.0072 × 1000) = 0.22 µg/L
Q90:  Cmix = 1.586×10³ / (0.0034 × 1000) = 0.47 µg/L
```

**Output fil: step6_cmix_results.csv**
```
Vandløb      Stof                           Scenario  Flow_m3_s  Flux_kg_yr  Cmix_µg_L
Værebro Å    UORGANISKE_FORBINDELSER        Mean      0.0072     68.8        303
Værebro Å    UORGANISKE_FORBINDELSER        Q90       0.0034     68.8        641
Værebro Å    UORGANISKE_FORBINDELSER        Q95       0.0021     68.8        1038
Værebro Å    Benzen                         Mean      0.0072     2.0         8.8
Værebro Å    Benzen                         Q90       0.0034     2.0         18.7
Værebro Å    Benzen                         Q95       0.0021     2.0         30.2
Værebro Å    PFAS                           Mean      0.0072     0.05        0.22
Værebro Å    PFAS                           Q90       0.0034     0.05        0.47
Værebro Å    PFAS                           Q95       0.0021     0.05        0.76
```

**Bemærk:**
- 9 rækker total (3 stoffer × 3 scenarier)
- Hver Cmix bruger KUN sit eget stofs flux
- **ALDRIG:** Cmix_total = (68.8 + 2.0 + 0.05) / Flow ❌

---

### Trin 7: MKK Sammenligning

**Funktion:** `_apply_mkk_thresholds()`

**MKK kilder:**
- BEK nr. 1022 (2010): 16 modelstoffer
- BEK 796/2023: PFAS
- Stof-specifikke værdier (f.eks. Benzen: 10 µg/L)
- Kategori fallbacks (f.eks. BTXER: 10 µg/L)

**Beregninger:**
```
Exceedance_Ratio = Cmix / MKK
Exceedance_Flag = (Ratio > 1)
```

**KRITISK:** Hver stof sammenlignes med SIN EGEN MKK-værdi. Stoffer vurderes individuelt.

**Komplet eksempel (fortsættelse af Værebro Å):**

**MKK-værdier for vores stoffer:**
```
Stof                           MKK (µg/L)
UORGANISKE_FORBINDELSER        4.3
Benzen                         10.0
PFAS                           0.1
```

**MKK-vurdering:**

**Stof 1: UORGANISKE_FORBINDELSER**
```
Scenarie    Cmix      MKK     Ratio    Overskrider?
Mean        303       4.3     70×      JA
Q90         641       4.3     149×     JA
Q95         1038      4.3     241×     JA
```

**Stof 2: Benzen**
```
Scenarie    Cmix      MKK     Ratio    Overskrider?
Mean        8.8       10.0    0.88×    NEJ
Q90         18.7      10.0    1.87×    JA
Q95         30.2      10.0    3.02×    JA
```

**Stof 3: PFAS**
```
Scenarie    Cmix      MKK     Ratio    Overskrider?
Mean        0.22      0.1     2.2×     JA
Q90         0.47      0.1     4.7×     JA
Q95         0.76      0.1     7.6×     JA
```

**Endelig output fil: step6_cmix_results.csv**
```
Vandløb      Stof                     Scenario  Cmix_µg_L  MKK_µg_L  Ratio  Exceeds
Værebro Å    UORGANISKE_FORBINDELSER  Mean      303        4.3       70×    TRUE
Værebro Å    UORGANISKE_FORBINDELSER  Q90       641        4.3       149×   TRUE
Værebro Å    UORGANISKE_FORBINDELSER  Q95       1038       4.3       241×   TRUE
Værebro Å    Benzen                   Mean      8.8        10.0      0.88×  FALSE
Værebro Å    Benzen                   Q90       18.7       10.0      1.87×  TRUE
Værebro Å    Benzen                   Q95       30.2       10.0      3.02×  TRUE
Værebro Å    PFAS                     Mean      0.22       0.1       2.2×   TRUE
Værebro Å    PFAS                     Q90       0.47       0.1       4.7×   TRUE
Værebro Å    PFAS                     Q95       0.76       0.1       7.6×   TRUE
```

**Konklusion for Værebro Å:**
- UORGANISKE_FORBINDELSER: Overskrider i alle scenarier (alvorligt)
- Benzen: Overskrider kun ved lavvande (Q90, Q95)
- PFAS: Overskrider i alle scenarier

**MKK dækning:** 100% (alle 9,529 rækker har tærskelværdier)

---

## Specialtilfælde og Nuancer

### 1. Lokaliteter med Multiple GVFKer

**Scenarie:** Én lokalitet påvirker flere grundvandsforekomster i forskellige akvifer-lag

**Eksempel:**
```
Lokalitet: 151-00001 (Sørup Losseplads)
Areal: 351,933 m²

GVFK 1: dkms_3098_ks (lag ks1)
  → Sample DKM_gvd_ks1.tif → 89.22 mm/år
  → Flux = 351,933 × 89.22 × 1,800 / 10⁹ = 56.5 kg/år
  
GVFK 2: dkms_3646_ks (lag ks2)
  → Sample DKM_gvd_ks2.tif → 87.45 mm/år
  → Flux = 351,933 × 87.45 × 1,800 / 10⁹ = 55.4 kg/år

Total flux: 56.5 + 55.4 = 111.9 kg/år
```

**⚠️ KRITISK USIKKERHED:**

**Problemstilling:**
- Samme areal (351,933 m²) bruges i BEGGE beregninger
- Repræsenterer GVD-rastere:
  - **A) Lag-specifik netto infiltration?** → Summering korrekt
  - **B) Total overflade-infiltration?** → Summering FORKERT (dobbelt-optælling ~100%)

**Antal berørte lokaliteter:** 199 med multiple GVFKer

**Status:** 🔴 KRÆVER AFKLARING - Kontakt GEUS eller tjek DK-model dokumentation

**Midlertidige løsninger:**
1. Behold nuværende (summering) - Konservativ, kan overestimere
2. Brug MAX infiltration - Kun én dominerende pathway
3. Vægt efter lagtykkelse - Mere kompleks men realistisk

---

### 2. Negative Infiltrationsværdier

**Årsag:** GVD-raster indeholder negative værdier (opstrømningszoner)

**Fysisk betydning:**
- Negativ GVD = Grundvand strømmer OPAD til overfladen
- Forekommer ved vandløb (gaining streams), vådområder, kildevæld
- Overfladeforurening kan IKKE sive nedad i disse zoner

**Håndtering:**
```python
if infiltration < 0:
    drop_row()  # rækker fjernes helt fra analysen
```

Scriptet logger hvor mange rækker, lokaliteter og GVFKer der fjernes, så effekten kan spores efter hvert run.

For visuel QA gemmes følgende i `Resultater/Figures/step6/negative_infiltration/`:
- `step6_negative_infiltration_map.html` – Folium-kort med lokalitetspolygoner (farvet efter |infiltration|), reference-GVFK fra kilde-data, og overlay af de relevante GVD-rastere (én lag-knap pr. modellag).
- `step6_negative_infiltration_sites.geojson` – Geodata til QGIS/ArcGIS med alle fjernede kombinationer.
- `step6_negative_infiltration_gvfk_counts.csv` – Tabel over antal lokaliteter per GVFK med negativ infiltration.
- `step6_negative_infiltration_validation.csv` – Taloversigt (polygon vs. centroid, min/max, pixeltal, differencer).
- `gvd_overlay_{lag}.png` – PNG-udsnit af de anvendte GVD-rastere som map overlay, så CRS og værdier kan kontrolleres manuelt.

**Status:** ✅ LØST - Negative værdier fjernes fra videre beregninger

---

### 3. Aggregering og Summering

**HVAD SUMMERES:**

✅ **Multiple lokaliteter med SAMME stof til SAMME vandløb**
```
Lokalitet A Benzen: 10 kg/år  ┐
Lokalitet B Benzen: 5 kg/år   ├─→ Total Benzen: 15 kg/år
Lokalitet C Benzen: 2 kg/år   ┘
```

✅ **Multiple GVFKer fra SAMME lokalitet** (⚠️ mulig dobbelt-optælling)
```
Lokalitet via ks1: 56.5 kg/år  ┐
Lokalitet via ks2: 55.4 kg/år  ├─→ Total: 111.9 kg/år
```

**HVAD SUMMERES IKKE:**

✗ **Forskellige stoffer** (holdes adskilte)
```
Benzen: 15 kg/år  → Separat række
Toluen: 8 kg/år   → Separat række
```

✗ **Forskellige vandløbssegmenter** (holdes adskilte)

✗ **Forskellige flow-scenarier** (holdes adskilte: Mean, Q90, Q95)

**Cmix beregnes ALTID per stof:**
- Benzen: Flux_benzen / Flow → Cmix_benzen
- Toluen: Flux_toluen / Flow → Cmix_toluen
- **ALDRIG:** (Flux_benzen + Flux_toluen) / Flow ❌

---

### 4. Vandløbssegmenter og Grundvandskontakt

**Relevante felter i vandløb shapefile:**
- `Kontakt = 1`: 7,496 segmenter (markeret med kontakt)
- `Flux_mag > 0`: 6,946 segmenter (faktisk opadgående flux)
- Forskel: 550 segmenter har kontaktflag men nul flux

**Nuværende filtrering:** Step 4 bruger `Kontakt == 1`

**Overvejelse:** Skulle vi kun bruge `Flux_mag > 0`?
- Kun segmenter med faktisk grundvandsudstrømning kan modtage forurening
- 550 segmenter har kontakt men ingen flux

**Status:** ℹ️ FUNGERER - Men kunne optimeres

---

### 5. Individuelle Stoffer vs Stofgrupper

**Baggrund:**
I Step 5 data kan `Qualifying_Substance` indeholde forskellige typer af "stoffer":
- **Individuelle stoffer:** "Benzen", "Perfluoroctansyre", "Arsen"
- **Sumgrupper:** "PFAS, sum af 22 stoffer", "PAH sum af 9 PAH"
- **Kategori-overrides:** "Landfill Override: BTXER"
- **Generiske kategorier:** "Chlorerede opl.midl.", "Pesticider, sum"

**Nuværende behandling:**
Alle behandles som **separate, uafhængige "stoffer"** gennem hele pipelinen:
- Hver får sin egen flux-beregning
- Hver aggregeres separat til vandløbssegmenter
- Hver får sin egen Cmix-beregning
- Hver sammenlignes med sin egen MKK-tærskel
- **INGEN summering på tværs**

**Muligt overlap-scenarie:**
En lokalitet kan have BÅDE:
- Individuelle PFAS-forbindelser: "Perfluoroctansyre", "PFOS", "PFOA" (9 forbindelser)
- Sumgruppe: "PFAS, sum af 22 stoffer"
- Resultat: 10 separate vurderinger for samme lokalitet
- **Fysisk virkelighed:** Sumgruppen INKLUDERER allerede de individuelle forbindelser

**Datastruktur-statistik:**
- Total rækker i Step 5: 4,513
- Individuelle stoffer: 3,296 (73%)
- Losseplads-kategori overrides: 780 (17%)
- Sumgrupper (PFAS sum, PAH sum, etc.): 221 (5%)
- Generiske kategorinavne: 239 (5%)

**Eksempel:**
```
Lokalitet 101-30075 har 11 PFAS-relaterede rækker:
  - Perfluoroctansyre           → Flux: 0.195 kg/år → Cmix → MKK
  - Perfluorbutansyre           → Flux: 0.195 kg/år → Cmix → MKK
  - ... (7 andre individuelle)  → Flux: 0.195 kg/år → Cmix → MKK
  - PFAS, sum af 22 stoffer     → Flux: 0.195 kg/år → Cmix → MKK
  - PFAS, sum af 4 (PFOA...)    → Flux: 0.195 kg/år → Cmix → MKK

Alle bruger SAMME areal (389.8 m²) og samme infiltration
```

**Fortolkning:**
- ✓ **Korrekt:** Ingen cross-compound summering (Benzen + Toluen adderes ikke)
- ⚠️ **Overlap:** Individuelle forbindelser og deres sum vurderes begge
- ℹ️ **Nuværende valg:** Rapportér alle - lad bruger/myndigheder vælge mest relevant

**Potentielle alternativer:**
1. **Prioritér hierarkisk:** Hvis sumgruppe findes, ekskludér individuelle
2. **Flag overlap:** Marker rækker hvor individuelle eksisterer sammen med sum
3. **Aggregér ved kategori:** Gruppér alle PFAS sammen på segment-niveau
4. **Behold nuværende:** Alle separate (nuværende valg)

**Status:** ✅ BEVIDST VALG - Alle vurderinger bevares; overlap dokumenteret men ikke fjernet

---

## Output Filer

### 1. step6_flux_site_segment.csv (4,393 rækker)
**Struktur:** Én række per Lokalitet × GVFK × Stof × Vandløb

**Nøglekolonner:**
- `Lokalitet_ID`, `Lokalitetsnavn`
- `GVFK`, `DK-modellag`
- `Area_m2`
- `Infiltration_mm_per_year`
- `Standard_Concentration_ug_L`
- `Pollution_Flux_kg_per_year`
- `Nearest_River_ov_id`, `Nearest_River_ov_navn`

---

### 2. step6_flux_by_segment.csv (3,207 rækker)
**Struktur:** Én række per Vandløb × GVFK × Stof × Kategori

**Nøglekolonner:**
- `Nearest_River_FID`, `River_Segment_Name`
- `River_Segment_GVFK`
- `Qualifying_Category`, `Qualifying_Substance`
- `Total_Flux_kg_per_year`
- `Contributing_Site_Count`
- `Contributing_Site_IDs` (kommasepareret)

---

### 3. step6_cmix_results.csv (9,529 rækker)
**Struktur:** Én række per Vandløb × GVFK × Stof × Flow-scenarie

**Nøglekolonner:**
- `River_Segment_Name`
- `Qualifying_Substance`, `Qualifying_Category`
- `Flow_Scenario` (Mean / Q90 / Q95)
- `Flow_m3_s`
- `Total_Flux_kg_per_year`
- `Cmix_ug_L`
- `MKK_ug_L`
- `Exceedance_Ratio`
- `Exceedance_Flag`

---

### 4. step6_segment_summary.csv (802 rækker)
**Struktur:** Sammenfatning per vandløbssegment

**Nøglekolonner:**
- `River_Segment_Name`
- `Total_Flux_kg_per_year` (sum over alle stoffer)
- `Substances` (liste af stoffer)
- `Categories` (liste af kategorier)
- `Contributing_Site_Count`
- `Max_Exceedance_Ratio`
- `Failing_Scenarios` (hvilke flow-scenarier overskrider)

---

## Visualiseringer

**Placering:** `Resultater/Figures/step6/`

### Interaktive kort:
- `step6_combined_map.html` - Lokaliteter, vandløb, GVFK

### Analytiske plots:
- `category_impact_overview.png` - Kategori-påvirkning
- `top_polluting_sites.png` - Top 20 forurenende lokaliteter
- `top_affected_rivers.png` - Top 20 påvirkede vandløb
- `exceedance_analysis.png` - MKK-overskridelser
- `gvfk_summary.png` - GVFK-oversigt
- `flow_scenario_sensitivity.png` - Flow-scenarie følsomhed

---

## Vigtige Antagelser

### ✅ Verificerede Antagelser:
1. Flux-formel korrekt implementeret
2. Cmix-formel korrekt (med /1000 konvertering)
3. MKK dækning 100%
4. Stoffer holdes adskilte gennem hele pipelinen
5. Bidragende lokaliteter kan spores

### ⚠️ Uafklarede Antagelser:
1. **GVD-raster fortolkning** (KRITISK)
   - Repræsenterer lag-specifik infiltration? → Summering OK
   - Repræsenterer total overflade-infiltration? → Summering FORKERT

2. **Multiple GVFK-summering**
   - Nuværende: Summerer flux fra samme lokalitet gennem forskellige lag
   - Usikkerhed: Dobbelt-optælling af samme vand?
   - Påvirkning: ~100% flux-forøgelse for 199 lokaliteter

---

## Kvalitetskontrol

### Verificeret:
- ✅ Ingen cross-compound summering
- ✅ Flux-beregninger matematisk korrekte
- ✅ Aggregeringer konsistente (site → segment)
- ✅ Negative infiltration håndteret
- ✅ MKK-tærskler for alle stoffer

### Kræver Verifikation:
- 🔴 GVD-raster fysisk betydning (HØJESTE PRIORITET)
- 🟡 Ekstreme PFAS-overskridelser (1.5M× MKK)
- 🟡 Vandløbsfiltrering (Kontakt vs Flux_mag)

---

## Konklusion

Step 6 beregner forureningspåvirkning fra lokaliteter til vandløb gennem en veldefineret pipeline. 

**Hovedstyrker:**
- Transparent beregningsmetodik
- Sporingof bidragende lokaliteter
- Multiple flow-scenarier
- Fuld MKK-dækning

**Kritisk usikkerhed:**
- GVD-raster fortolkning for multi-GVFK lokaliteter kræver afklaring

**Anbefaling:**
Afklar GVD-raster betydning med GEUS før endelig rapport.
