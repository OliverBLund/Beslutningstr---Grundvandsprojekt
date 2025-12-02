# Mødenoter: GVD Filer og 2023 Opdatering

## Baggrund
Diskussion om anvendelse af GVD (grundvandsdannelse) raster filer i projektet. Nuværende system anvender 2019 versionen, men skal opdateres til 2023 versionen af DK-modellen.

**Vigtig note om gradient retning:**
- **Negative GVD værdier** = opadrettet gradient (grundvand strømmer opad - discharge zone)
- **Positive GVD værdier** = nedadrettet gradient (infiltration - vand strømmer ned gennem kontamineret jord)

---

## 1. Er der tilsvarende raster filer for ks1, ks2 etc. i 2023 versionen på 100x100 m resolution?

### Svar: ✅ MODTAGET (11/26/2025)

### ⚠️ KRITISK ÆNDRING: Nyt lagnavne system

**GAMLE (2019) lagnavne:**
- `ks1`, `ks2`, `ks3`, `ks4`, `ks5`, `ks6`
- `ps1`, `ps2`, `ps3`, `ps4`, `ps5`, `ps6`
- `kalk`
- `lag1`, `lag2`, `lag3`, `lag4`, `lag5`, `lag6` (Bornholm)

**NYE (2023) lagnavne - 20 unikke lag:**

**dk16 model (2185 GVFK):**
- `kvs_0200`, `kvs_0400`, `kvs_1200`, `kvs_1400`, `kvs_2100`, `kvs_2300`, `kvs` (7 varianter)
- `ods_5254`
- `bas_5658`, `bas_6000`, `bas_6266`
- `bds_6800`, `bds_7078`
- `kak_8190`

**dk7 model (74 GVFK - Bornholm):**
- `lag1`, `lag2`, `lag3`, `lag4`, `lag5`, `lag6`

**⭐ VIGTIGT: dk7 og dk16 bruges samtidig!**
- dk16 filer for fastlands-Danmark (2185 GVFK)
- dk7 filer for Bornholm (74 GVFK)

---

### GVD raster filer (mappe: `dkmtif/`)

**Per-lag GVD filer:**
- dk16: `dk16_gvd_kvs_0400.tif`, `dk16_gvd_ods_5254.tif`, etc. (13 unikke lag)
- dk7: `dk7_gvd_lag1.tif` til `dk7_gvd_lag6.tif` (6 lag)

**Gradient retnings filer (⭐ LØSER TRIN 1 PROBLEM!):**
- `dk16_downwardflux_lay12.tif` - nedadrettet flux gennem lag 1-2 (Danmark)
- `dk16_upwardflux_lay12.tif` - opadrettet flux gennem lag 1-2 (Danmark)
- `dk7_downwardflux_lay12.tif` - nedadrettet flux (Bornholm)
- `dk7_upwardflux_lay12.tif` - opadrettet flux (Bornholm)

**Topmag filer (forenklet alternativ til per-lag sampling):**
- `dk16_gvd_topmag.tif` - GVD for øverste magasin (Danmark)
- `dk7_gvd_topmag.tif` - GVD for øverste magasin (Bornholm)

**Travel time filer:**
- `dk16_tr2sz.tif` og `dk7_tr2sz.tif`

---

### GVFK data (geodatabase: `Grunddata_results.gdb`)

**Layer: `dkm_gvf_vp3genbesog_kontakt`**
- **2259 grundvandsforekomster** (stigning fra 2044 i 2019)
- Kolonne `GVForekom`: GVFK navne (f.eks. "dkmj_16_ks", "dkms_3645_ks")
- Kolonne `dkmlag`: **NYE lagnavne** (f.eks. "kvs_0400", "lag2")
- Kolonne `mag_no`: Kobling til oplands raster filer
- **✅ GVForekom navne er 100% kompatible med gamle system!**
  - 2042 ud af 2043 gamle GVFK navne findes stadig
  - V1/V2 kobling via `GVForekom` vil fortsætte med at virke

**Rivers layer: `Rivers_gvf_vp3genbesog_kontakt`**
- Erstatter gamle `Rivers_gvf_rev20230825_kontakt.shp`
- Kolonner: `GVForekom`, `Kontakt`, `ov_id`, `ov_navn`

**Q-punkter layer: `dkm_qpoints_gvf_vp3genbesog_kontakt`**
- **84,295 Q-punkter** (op fra ~60k i 2019)
- Kolonner: `Q90`, `Q95`, `deltaQ90`, `ov_id`, `gvf_no`, `mag_no`
- **Ny kolonne `deltaQ90`**: Difference mellem indvinding og ingen indvinding

**Andre layers:**
- `Lakes_gvf_vp3genbesog_kontakt`
- `Sea_gvf_vp3genbesog_kontakt`
- `TerrEcoSys_gvf_vp3genbesog_kontakt`
- `dkm_gvf_top_magasin`

---

## 2. Kan disse infiltrations-/GVD-rastere overhovedet anvendes på V1/V2 lokalitetsniveau?

### Kontekst:
- V1/V2 lokaliteter er ofte små (~10-20 pixels i det gamle 500x500m eller 100x100m format fra 2019)
- Vigtigt at udpensle størrelsen af lokaliteterne i dokumentationen

### Svar:
**Ja, det er nok det bedste bud.**

Der er diverse strategier som GEUS gør brug af når de skal anvende blandt andet GVD filer på et "mindre" område såsom en V1/V2 lokalitet. 

**Nuværende tilgang i koden:**
- Kombineret polygon mean + centroid sampling approach
- Foretrækker polygon mean når tilgængelig
- Falder tilbage på centroid for små lokaliteter
- Gemmer begge værdier til diagnostik

---

## 3. Hvordan påvirker de nye lagnavne vores workflow?

### SIMPLE LØSNING: Samme mapping, ny kilde

**GAMLE SYSTEM (2019):**
1. CSV fil: `vp3_h1_grundvandsforekomster_VP3Genbesøg.csv`
2. Kolonner: `GVForekom` → `DK-modellag`
3. Eksempel: "dkmj_16_ks" → "ks1 - ks2"
4. Funktion: `load_gvfk_layer_mapping()` loader CSV
5. Raster filer: `DKM_gvd_ks1.tif`, `DKM_gvd_ks2.tif`

**NYE SYSTEM (2023):**
1. Geodatabase: `Grunddata_results.gdb` / layer: `dkm_gvf_vp3genbesog_kontakt`
2. Kolonner: `GVForekom` → `dkmlag` (⚠️ kolonne navn ændret!)
3. Eksempel: "dkmj_16_ks" → "kvs_0400"
4. Funktion: `load_gvfk_layer_mapping()` skal opdateres til at loade fra geodatabase
5. Raster filer: `dk16_gvd_kvs_0400.tif`, `dk7_gvd_lag2.tif` (⚠️ fil naming ændret!)

**Data verificeret:**
- **2259 rækker** i geodatabase (op fra 2044 i CSV)
- **2049 unikke GVForekom navne**
- **20 unikke dkmlag værdier**
- Mapping struktur er **identisk** - kun kilde og navne er ændret

---

### ✅ GODT NYS: GVForekom Navne Kompatibilitet

**Verificeret gennem data analyse:**
- **2042 ud af 2043** (99.95%) gamle GVForekom navne eksisterer stadig i ny geodatabase
- **7 nye GVFK** tilføjet i 2023 systemet
- **1 GVFK** fjernet fra 2019 systemet

**Konsekvens:**
- ✅ V1/V2 → GVFK kobling via `GVForekom` vil **fortsætte med at virke**
- ✅ **Ingen re-mapping af V1/V2 lokaliteter nødvendig**
- ⚠️ Kun den ene fjernede GVFK skal tjekkes (sandsynligvis ikke i V1/V2 data)

---

### ⭐ NYE GRADIENT RETNINGS FILER (Løser Trin 1 Problem!)

**Separate upward/downward flux filer:**
- `dk16_downwardflux_lay12.tif` (Danmark) + `dk7_downwardflux_lay12.tif` (Bornholm)
- `dk16_upwardflux_lay12.tif` (Danmark) + `dk7_upwardflux_lay12.tif` (Bornholm)

**Fordel:**
- **Trin 1 filtrering bliver meget simplere!**
- I stedet for at sample rå GVD og beregne flertalsprincip (>50% positive pixels):
  - Sample `downward_flux` raster for hver lokalitet
  - Hvis `mean(downward_flux) > threshold` → Behold lokalitet
  - Hvis `mean(downward_flux) ≈ 0` → Fjern lokalitet (opadrettet gradient)

**Trin 2 GVD filer til flux beregning:**
- dk16: `dk16_gvd_kvs_0400.tif`, `dk16_gvd_ods_5254.tif`, etc. (13 lag-typer)
- dk7: `dk7_gvd_lag1.tif` til `dk7_gvd_lag6.tif`
- **ALTERNATIV**: `dk16_gvd_topmag.tif` / `dk7_gvd_topmag.tif` (øverste magasin - simplere!)

**Infiltrations oplands (mappe: `magopl/`):**
- Raster filer: `gwbcatchment_magno_kvs_0400.tif`, `gwbcatchment_magno_lag1.tif`, etc.
- Kobles via `mag_no` kolonne i GVFK
- Optional til validering af oplands baseret analyse

---

## 4. Hvordan håndteres ekstreme værdier og pludselige ændringer mellem nabopixels?

### Kontekst:
Eksempel fra data: En pixel med **-6743 mm/år** og en nabopixel med **+1340 mm/år** blev observeret på en V1/V2 lokalitet.

**Reference fra litteraturen:**
GrundRisk projektet har fastsat en værdi på **750 mm/år** som grænseværdi:
- MST (2016). GrundRisk. Metode til at estimere lertykkelse under jordforureninger, der er kortlagt på V1 og V2. Miljøstyrelsen. Miljøprojekt nr. 1888.

### Svar:

**Diskuterede tilgange:**
- ❌ **Alle negative nulstilles til 0**: Fungerer ikke i vores scenarie da vi skal vide om det er opadrettet eller nedadrettet gradient
- **Normalt regner de opadrettet og nedadrettet separat**: (Dårligt noteret...)
- ✅ **To-trins tilgang** (Lars' forslag):
  - Køre et 0-1 scenario hvor man bestemmer gradient retning
  - Men vi skal stadig kunne få en flux værdi vi kan arbejde med

---

## 5. FINALISERET TILGANG: To-Trins GVD Håndtering

### Trin 1: Lokalitets Filtrering (Gradient Retnings Vurdering)

**Formål:** Identificere hvilke lokaliteter der bidrager til forurening af vandløb

**Metode:**
1. Sample GVD værdier på tværs af lokalitets polygon
2. Anvend **flertalsprincip (majority rule)**:
   - Hvis **>50% af pixels er positive** (nedadrettet gradient) → **Behold lokalitet**
   - Hvis **≤50% af pixels er positive** (opadrettet gradient) → **Fjern lokalitet**

**Rationale:** 
- Lokaliteter med opadrettet gradient transporterer ikke forurening nedefter til vandløb
- Grundvand strømmer opad gennem området (discharge zone)
- Disse lokaliteter udgør ikke en risiko for overfladevand via grundvandsstrømning

**Output:**
- Binær flag (0/1) for hver lokalitet
- Filtreret datasæt med kun nedadrettede gradient lokaliteter

---

### Trin 2: Flux Beregning (Kun for Bevarede Lokaliteter)

**Formål:** Beregne realistiske infiltrations værdier til flux beregning

**Metode:**
1. For lokaliteter der bestod Trin 1 (nedadrettet gradient)
2. Sample GVD værdier på tværs af lokalitets polygon
3. **Nulstil negative pixels til 0**:
   - Rationale: Da vi ved lokaliteten overordnet har nedadrettet gradient, er negative pixels sandsynligvis støj/artefakter
   - Dette er en rimelig approksimation
4. **Cap positive værdier ved 750 mm/år**:
   - Rationale: GrundRisk projekt standard (MST 2016)
   - Håndterer ekstreme værdier (f.eks. +1340 mm/år)
5. Beregn gennemsnits GVD for flux beregning

**Flux formel:**
```
Flux (µg/s) = Areal (m²) × Koncentration (µg/L) × Infiltration_GVD (mm/år)
```

---

### Trin 3: Dokumentation og Logging

**Krav:** Al filtrering og håndtering skal være **ekstremt tydelig** i outputs

**Log følgende:**
1. **Trin 1 statistik:**
   - Antal lokaliteter fjernet grundet opadrettet gradient
   - Procent af total
   - Liste over fjernede lokalitet ID'er

2. **Trin 2 statistik:**
   - Antal pixels nulstillet (negative → 0)
   - Antal pixels capped ved 750 mm/år
   - Distribution af GVD værdier før/efter behandling

3. **Diagnostik output:**
   - Histogram af GVD værdier (før og efter)
   - Spatial plot af fjernede vs. bevarede lokaliteter
   - Sammenligning med nuværende tilgang

4. **Tilføj til eksisterende filtering audit:**
   - Udvid `step6_filtering_audit_detailed.csv`
   - Ny sektion: "GVD Gradient Direction Filtering"

---

## NØDVENDIGE KODE ÆNDRINGER

### Oversigt over Ændringer

| Komponent | 2019 System | 2023 System | Ændring Nødvendig |
|-----------|-------------|-------------|-------------------|
| **GVFK navne** | `GVForekom` | `GVForekom` | ✅ Ingen - 100% kompatibel |
| **Layer mapping kilde** | CSV fil | Geodatabase layer | 🟡 Simpel - opdater load funktion |
| **Layer mapping kolonne** | `DK-modellag` | `dkmlag` | 🟡 Simpel - find/replace kolonne navn |
| **Lagnavne værdier** | `ks1, ks2` | `kvs_0400, lag2` | ⚠️ Informativ - påvirker raster fil navne |
| **GVD raster fil navne** | `DKM_gvd_ks2.tif` | `dk16_gvd_kvs_0400.tif` | 🔴 Kritisk - ny fil naming logik |
| **Rivers/Q-punkter** | Shapefile | Geodatabase layer | 🟡 Simpel - opdater load funktion |

---

### 1. config.py - Nye fil stier (PRIORITET 1)

```python
# === 2023 DK-MODEL FILER (VP3 Genbesøg) ===
DK_MODEL_VERSION = "VP3_2023"  # Eller "2019" for backward compatibility

# Geodatabase sti
GRUNDDATA_RESULTS_GDB = DATA_DIR / "Ny_data_Lars_11_26_2025" / "Grunddata_results.gdb"
DKMTIF_DIR_2023 = DATA_DIR / "Ny_data_Lars_11_26_2025" / "dkmtif"

# Gradient retnings filer (Trin 1 filtrering)
DOWNWARD_FLUX_DK16 = DKMTIF_DIR_2023 / "dk16_downwardflux_lay12.tif"  # Danmark
DOWNWARD_FLUX_DK7 = DKMTIF_DIR_2023 / "dk7_downwardflux_lay12.tif"   # Bornholm
UPWARD_FLUX_DK16 = DKMTIF_DIR_2023 / "dk16_upwardflux_lay12.tif"     # Optional
UPWARD_FLUX_DK7 = DKMTIF_DIR_2023 / "dk7_upwardflux_lay12.tif"       # Optional

# Topmag GVD (Trin 2 - forenklet flux beregning)
TOPMAG_GVD_DK16 = DKMTIF_DIR_2023 / "dk16_gvd_topmag.tif"            # Danmark
TOPMAG_GVD_DK7 = DKMTIF_DIR_2023 / "dk7_gvd_topmag.tif"              # Bornholm

# ALTERNATIVT: Per-lag GVD rastere (mere præcist men komplekst)
# Format: dk16_gvd_{lagnavne}.tif (f.eks. dk16_gvd_kvs_0400.tif)
# Format: dk7_gvd_{lagnavne}.tif (f.eks. dk7_gvd_lag2.tif)
```

**Bemærkning:** dk7 og dk16 skal **begge** bruges - dk16 for Danmark, dk7 for Bornholm.

---

### 2. data_loaders.py - Opdater load_gvfk_layer_mapping() (PRIORITET 1)

**NUVÆRENDE funktion (loads CSV):**
```python
def load_gvfk_layer_mapping() -> pd.DataFrame:
    """Load GVFK to DK-model layer mapping."""
    df = pd.read_csv(GVFK_LAYER_MAPPING_PATH, encoding=encoding, sep=';')
    # Returns: GVForekom, DK-modellag
    return df
```

**OPDATERET funktion (loads geodatabase):**
```python
def load_gvfk_layer_mapping() -> pd.DataFrame:
    """Load GVFK to DK-model layer mapping from 2023 geodatabase."""
    gdb_path = GRUNDDATA_RESULTS_GDB
    layer = 'dkm_gvf_vp3genbesog_kontakt'
    gdf = gpd.read_file(gdb_path, layer=layer)

    # Extract only mapping columns (drop geometry for performance)
    df = pd.DataFrame({
        'GVForekom': gdf['GVForekom'],
        'dkmlag': gdf['dkmlag']  # ⚠️ Kolonne navn ændret fra 'DK-modellag'
    })

    # Verificer
    if len(df) != 2259:
        print(f"WARNING: Expected 2259 rows, got {len(df)}")

    return df
```

**Tilføj også:**
```python
def load_rivers_2023() -> gpd.GeoDataFrame:
    """Load rivers from geodatabase."""
    return gpd.read_file(GRUNDDATA_RESULTS_GDB, layer='Rivers_gvf_vp3genbesog_kontakt')

def load_qpoints_2023() -> gpd.GeoDataFrame:
    """Load Q-points from geodatabase."""
    return gpd.read_file(GRUNDDATA_RESULTS_GDB, layer='dkm_qpoints_gvf_vp3genbesog_kontakt')
```

---

### 3. Step 1 (step1_all_gvfk.py) - Opdater GVFK kilde (PRIORITET 2)

**Ændringer:**
- Skift fra `gpd.read_file(GRUNDVAND_PATH)` til `load_gvfk_2023()`
- Verificer `dkmlag` kolonne eksisterer (erstatter gammel CSV mapping)
- Forventet antal GVFK: **2259** (op fra ~2044)
- GVForekom navne er uændrede → **ingen breaking changes** for downstream steps

---

### 4. Step 2 (step2_river_contact.py) - Opdater Rivers + Q-punkter (PRIORITET 2)

**Ændringer:**
- Skift fra `gpd.read_file(RIVERS_PATH)` til `load_rivers_2023()`
- Skift fra `gpd.read_file(RIVER_FLOW_POINTS_PATH)` til `load_qpoints_2023()`
- Verificer kolonner: `Kontakt`, `Q90`, `Q95`, `deltaQ90`, `ov_id`, `gvf_no`
- **Ny kolonne `deltaQ90`**: Forskel mellem Q90 med/uden indvinding (kan bruges til fremtidig analyse)

---

### 5. Step 3 (step3_v1v2_sites.py) - V1/V2 til GVFK kobling (PRIORITET 3)

**Status:** ✅ **INGEN ÆNDRINGER NØDVENDIGE**

**Rationale:**
- V1/V2 CSV filer har `Navn` kolonne = GVForekom (f.eks. "dkmj_16_ks", "dkms_3645_ks")
- Nye geodatabase har `GVForekom` kolonne med **100% kompatible navne**
- 2042/2043 (99.95%) gamle navne eksisterer stadig
- Spatial join eller CSV merge via `GVForekom` vil fortsætte med at virke

**Verificering nødvendig:**
- Check om den ene fjernede GVFK findes i V1/V2 data (sandsynligvis ikke)

---

### 6. Step 6 (step6_tilstandsvurdering.py) - Opdater til 2023 data (PRIORITET 1)

#### A) Kolonne Navn Ændring (SIMPELT - Find/Replace)

**Linje 92, 237, 242-285, 328-330, 529, osv.:**

Erstat alle forekomster:
- `"DK-modellag"` → `"dkmlag"`
- `layer_mapping[["GVForekom", "DK-modellag"]]` → `layer_mapping[["GVForekom", "dkmlag"]]`

**VIGTIGT:** `load_gvfk_layer_mapping()` virker stadig - bare returnerer `dkmlag` i stedet for `DK-modellag` nu.

**Eksempel på ændring:**
```python
# FØR:
if enriched["DK-modellag"].isna().any():
    missing_layers = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()

# EFTER:
if enriched["dkmlag"].isna().any():
    missing_layers = enriched.loc[enriched["dkmlag"].isna(), "GVFK"].unique()
```

#### B) Opdater Gradient Filtrering - Trin 1 (linje 290-390)

**NY funktion til downward flux sampling:**

```python
def _is_bornholm_site(dkmlag: str) -> bool:
    """Check if site is on Bornholm based on dkmlag value."""
    bornholm_layers = {'lag1', 'lag2', 'lag3', 'lag4', 'lag5', 'lag6'}
    if pd.isna(dkmlag):
        return False
    # Parse dkmlag (might be "lag2" or "Kalk: kalk; Lag: lag2")
    layers = _parse_dkmlag_2023(dkmlag)
    return any(layer in bornholm_layers for layer in layers)

def _sample_downward_flux(geometry, centroid, dkmlag: str) -> float:
    """Sample downward flux raster (dk16 for Denmark, dk7 for Bornholm)."""
    is_bornholm = _is_bornholm_site(dkmlag)
    raster_path = DOWNWARD_FLUX_DK7 if is_bornholm else DOWNWARD_FLUX_DK16

    # Sample polygon mean (preferred) or centroid fallback
    # Return mean downward flux in mm/år
    # ... [sampling logic her]
```

**Erstatter gammelt flertalsprincip:**
```python
# GAMMEL: Sample rå GVD, beregn % positive pixels
# NY: Sample downward_flux direkte
enriched['Downward_Flux_mm_yr'] = enriched.apply(
    lambda row: _sample_downward_flux(
        geometry_lookup[row['Lokalitet_ID']],
        centroid_lookup[row['Lokalitet_ID']],
        row['dkmlag']
    ),
    axis=1
)

# Filter: Behold kun sites med downward flux > threshold
DOWNWARD_FLUX_THRESHOLD = 0  # Eller andet cutoff
enriched = enriched[enriched['Downward_Flux_mm_yr'] > DOWNWARD_FLUX_THRESHOLD]
```

#### C) Opdater GVD Raster Sampling (linje 507-630) - KRITISK ÆNDRING

**PROBLEM:** Raster fil navne er ændret!

**Nuværende kode (linje 624):**
```python
def _sample_infiltration(layer: str, geometry, centroid):
    raster_file = GVD_RASTER_DIR / f"DKM_gvd_{layer}.tif"
    # Eksempel: layer="ks2" → DKM_gvd_ks2.tif
```

**Ny kode:**
```python
def _sample_infiltration(layer: str, geometry, centroid):
    # Determine if Bornholm layer
    is_bornholm = layer in ['lag1', 'lag2', 'lag3', 'lag4', 'lag5', 'lag6']

    # Construct new raster file path
    if is_bornholm:
        raster_file = DKMTIF_DIR_2023 / f"dk7_gvd_{layer}.tif"
    else:
        raster_file = DKMTIF_DIR_2023 / f"dk16_gvd_{layer}.tif"

    # Eksempler:
    # layer="kvs_0400" → dk16_gvd_kvs_0400.tif
    # layer="lag2" → dk7_gvd_lag2.tif

    if not raster_file.exists():
        print(f"WARNING: Raster not found: {raster_file}")
        return {"Combined": None, "Centroid": None, ...}

    # Rest af sampling logik er uændret
    # ...
```

**Funktion `_parse_dk_modellag()` skal IKKE ændres** - den parser stadig format som før:
- Input kan være: "kvs_0400" eller "Kalk: kak_8190" eller multi-lag
- Output er liste af lag navne
- Parsing logik er den samme

**ALTERNATIV: Brug topmag filer (simplere!):**

```python
def _sample_topmag_gvd(geometry, centroid, dkmlag: str) -> float:
    """Sample topmag GVD raster (simplere end per-lag sampling)."""
    is_bornholm = _is_bornholm_site(dkmlag)
    raster_path = TOPMAG_GVD_DK7 if is_bornholm else TOPMAG_GVD_DK16

    # Sample polygon mean eller centroid
    # Return GVD værdi i mm/år
    # Cap ved 750 mm/år (MST 2016 standard)
```

---

### 7. Opsummering af Step 6 Ændringer

**SIMPLE ændringer (Find/Replace):**
1. `"DK-modellag"` → `"dkmlag"` (alle forekomster i filen)
2. Output CSV kolonne navn opdateres automatisk

**KOMPLEKS ændring (raster fil naming):**
1. Linje ~624: Opdater `_sample_infiltration()` funktion:
   - Tilføj Bornholm check
   - Construct korrekt fil sti: `dk16_gvd_{layer}.tif` eller `dk7_gvd_{layer}.tif`
   - Rest af sampling logik uændret

**VALGFRI forbedring (downward flux):**
1. Linje ~290-390: Erstat gradient filtrering med downward flux sampling
   - Simplere end nuværende majority rule
   - Brug `dk16_downwardflux_lay12.tif` og `dk7_downwardflux_lay12.tif`

---

## HANDLINGSPLAN: Implementering af 2023 DK-Model Opdatering

### Fase 1: Modtagelse og Validering af Nye Data ✅ AFSLUTTET (11/26/2025)

**Opgaver:**
1. ✅ **Modtag filer fra Lars:**
   - ✅ GVD raster datasæt i mappe `dkmtif/` (dk7 og dk16 modeller)
   - ✅ Downward/upward flux filer (lay12)
   - ✅ GVFK i geodatabase `Grunddata_results.gdb`
   - ✅ Rivers layer i geodatabase
   - ✅ Q-punkter layer i geodatabase (med Q90, Q95, deltaQ90)
   - ✅ Infiltrations oplands i mappe `magopl/`
   - ⚠️ Clay cover data modtaget men ikke nødvendig (`fohm_descr/`)

2. ✅ **Inspicer nye data:**
   - ✅ GVFK navne: `dkmlag` bruger nye navne (kvs_XXXX, lag1-6)
   - ✅ GVFK antal: 2259 (stigning fra ~2044)
   - ✅ Nye lagnavne: dk16 (9 lag-typer) og dk7 (lag1-6)
   - ✅ Raster resolution: **100x100 meter** (verificeret)
   - ✅ CRS/projektion: **EPSG:25832** (standard for Danmark)

3. ✅ **Dokumenter ændringer:**
   - ✅ Dokumenteret i denne fil (se spørgsmål 1-3)
   - ⏳ Opret mapping tabel hvis V1/V2 bruger gamle lagnavne
   - ✅ Noteret: Geodatabase format i stedet for separate shapefiles

---

### Fase 2: GVFK Navne Kobling (Uge 1-2)

**Formål:** Sikre at V1/V2 lokaliteter kan kobles til nye GVFK navne

**Opgaver:**
1. ✅ **Analyser GVFK navne ændringer:**
   - [ ] Load 2019 GVFK.shp: `VP3Genbesøg_grundvand_geometri.shp`
   - [ ] Load 2023 GVFK.shp (ny fil)
   - [ ] Sammenlign `Navn` kolonnen mellem de to
   - [ ] Identificer:
     - Uændrede GVFK navne (direkte match)
     - Omdøbte GVFK (spatial overlap analyse)
     - Nye GVFK (kun i 2023)
     - Fjernede GVFK (kun i 2019)

2. ✅ **Opret GVFK navne mapping (hvis nødvendigt):**
   - [ ] Hvis GVFK navne er ændret: Opret `gvfk_2019_to_2023_mapping.csv`
   - [ ] Kolonner: `GVFK_2019`, `GVFK_2023`, `Match_Type` (exact/spatial/manual)
   - [ ] Gem i `Data/` folder

3. ✅ **Opdater V1/V2 kobling:**
   - [ ] Check V1/V2 CSV filer: Hvilke GVFK navne refererer de til?
   - [ ] Hvis 2019 navne: Opret script til at mappe til 2023 navne
   - [ ] Alternativt: Re-run spatial join med ny GVFK.shp i Step 3

---

### Fase 3: Opdater config.py for 2023 Filer (Uge 2)

**Opgaver:**
1. ✅ **Tilføj nye fil stier:**
```python
# I config.py - ny sektion
# === 2023 DK-MODEL FILER ===
DK_MODEL_VERSION = "2023"  # Eller "2019" for backward compatibility

# GVD Rastere (2023)
GVD_RASTER_DIR_2023 = PROJECT_ROOT / "Data" / "dkm2023_vp3_GVD"
GVD_WITH_PUMPING_DIR = GVD_RASTER_DIR_2023 / "med_indvinding"
GVD_WITHOUT_PUMPING_DIR = GVD_RASTER_DIR_2023 / "uden_indvinding"

# GVFK (2023)
GVFK_2023_PATH = DATA_DIR / "shp files" / "GVFK_2023_med_lagnavne.shp"
GVFK_LAYER_MAPPING_2023_PATH = DATA_DIR / "gvfk_2023_layer_mapping.csv"

# Rivers (2023)
RIVERS_2023_PATH = DATA_DIR / "shp files" / "Rivers_2023.shp"

# Q-punkter (2023)
RIVER_FLOW_POINTS_2023_PATH = DATA_DIR / "Q_punkter_2023.shp"
Q95_WITH_PUMPING_PATH = DATA_DIR / "Q95_med_indvinding_2023.shp"
Q95_PUMPING_DIFF_PATH = DATA_DIR / "Q95_difference_2023.shp"
```

2. ✅ **Opdater lagnavne mapping:**
```python
# Ny mapping for 2023 lagnavne
LAYER_MAPPING_2023 = {
    # Eksempel - opdater når vi ser de faktiske navne
    'nyt_lag_1': 'ks1',  # Backward reference
    'nyt_lag_2': 'ks2',
    # ... etc.
}
```

3. ✅ **Tilføj GVD håndterings konstanter:**
```python
# === GVD BEHANDLINGS PARAMETRE ===
GVD_MAX_INFILTRATION = 750  # mm/år (MST 2016, GrundRisk projekt)
GVD_MAJORITY_THRESHOLD = 0.5  # 50% af pixels skal være positive
GVD_NEGATIVE_MEANS_UPWARD = True  # Dokumentation flag

# Gradient retnings håndtering
FILTER_UPWARD_GRADIENT_SITES = True  # Trin 1 aktivering
ZERO_NEGATIVE_PIXELS = True  # Trin 2 aktivering
CAP_POSITIVE_VALUES = True  # Trin 2 aktivering
```

---

### Fase 4: Implementer To-Trins GVD Håndtering i Step 6 (Uge 2-3)

**Opgaver:**

**A) Opret ny modul: `gvd_gradient_handler.py`**
```python
# Kode/tilstandsvurdering/gvd_gradient_handler.py

def assess_gradient_direction(site_gdf, gvd_raster_path, majority_threshold=0.5):
    """
    Trin 1: Bestem gradient retning for hver lokalitet.
    
    Returns:
        - GeoDataFrame med ny kolonne: 'Gradient_Direction' (1=downward, 0=upward)
        - Dict med statistik
    """
    pass

def process_gvd_for_flux(site_gdf, gvd_raster_path, max_cap=750):
    """
    Trin 2: Behandl GVD værdier for flux beregning.
    - Nulstil negative pixels
    - Cap ved max_cap mm/år
    
    Returns:
        - GeoDataFrame med kolonne: 'GVD_Processed' (mm/år)
        - Dict med behandlings statistik
    """
    pass

def create_gvd_diagnostics(before_gdf, after_gdf, output_dir):
    """
    Trin 3: Opret diagnostik plots og logs.
    """
    pass
```

**B) Modificer `step6_tilstandsvurdering.py`:**
- [ ] Import ny modul
- [ ] Tilføj Trin 1 før flux beregning
- [ ] Tilføj Trin 2 GVD behandling
- [ ] Udvid filtering audit med GVD statistik
- [ ] Opdater logging

**C) Opdater `data_loaders.py`:**
- [ ] Tilføj funktion: `load_gvd_raster_2023()`
- [ ] Tilføj funktion: `load_gvfk_layer_mapping_2023()`
- [ ] Håndter version selection (2019 vs 2023)

---

### Fase 5: Opdater Step 1-3 for 2023 GVFK (Uge 3)

**Hvis GVFK navne er ændret:**

**Step 1:**
- [ ] Opdater til at bruge `GVFK_2023_PATH`
- [ ] Verificer antal GVFK (sammenlign med 2019)

**Step 2:**
- [ ] Opdater til at bruge `RIVERS_2023_PATH`
- [ ] Check `Kontakt` kolonne eksisterer stadig
- [ ] Verificer GVFK navne matching

**Step 3:**
- [ ] Re-run spatial join med ny GVFK.shp
- [ ] Alternativt: Anvend GVFK navne mapping fra Fase 2
- [ ] Verificer lokalitet-GVFK koblingen er korrekt

---

### Fase 6: Test og Validering (Uge 3-4)

**Opgaver:**
1. ✅ **Unit tests:**
   - [ ] Test `assess_gradient_direction()` med syntetisk data
   - [ ] Test `process_gvd_for_flux()` med edge cases
   - [ ] Verificer 750 mm/år cap fungerer

2. ✅ **Integration test:**
   - [ ] Kør hele workflow med 2023 data
   - [ ] Sammenlign outputs med 2019 version:
     - Antal GVFK i hver step
     - Antal lokaliteter filtreret i Step 6
     - Flux værdier distribution
     - Cmix værdier distribution
     - MKK overskridelser

3. ✅ **Validering af gradient filtrering:**
   - [ ] Identificer lokaliteter fjernet grundet opadrettet gradient
   - [ ] Manuel check af 5-10 tilfældige lokaliteter:
     - Visualiser GVD raster under lokalitet
     - Verificer gradient retning assessment er korrekt
   - [ ] Sammenlign med Lars' "flux til lag1_2" fil (hvis tilgængelig)

4. ✅ **Dokumentation review:**
   - [ ] Verificer alle logs er tydelige
   - [ ] Check filtering audit indeholder GVD statistik
   - [ ] Sikr citationer er korrekte (MST 2016)

---

### Fase 7: Dokumentation og Rapportering (Uge 4)

**Opgaver:**
1. ✅ **Opdater README filer:**
   - [ ] README_WORKFLOW.md: Tilføj sektion om 2023 opdatering
   - [ ] README_STEP6.md: Udvid med To-Trins GVD håndtering
   - [ ] Opret: `README_2023_MIGRATION.md`

2. ✅ **Opret validerings rapport:**
   - [ ] `2023_DK_MODEL_VALIDATION_REPORT.md`
   - [ ] Inkluder:
     - GVFK navne ændringer (hvis relevante)
     - GVD gradient filtrering statistik
     - Sammenligning 2019 vs 2023 resultater
     - Metodologisk begrundelse for To-Trins tilgang
     - Citationer (MST 2016, GEUS rapporter)

3. ✅ **Opret migrerings guide:**
   - [ ] Trin-for-trin guide til at skifte mellem 2019 og 2023
   - [ ] Config flag: `DK_MODEL_VERSION = "2023"`
   - [ ] Backward compatibility overvejelser

---

### Fase 8: Afsluttende Overvejelser og Åbne Spørgsmål

**Spørgsmål til afklaring:**
1. ✅ ~~dk7 vs dk16 model valg~~ → **AFKLARET**: Begge skal bruges samtidig (dk7=Bornholm, dk16=Danmark)
2. ⏳ **Downward flux threshold:**
   - Hvilken threshold værdi for downward flux skal klassificere lokalitet som nedadrettet?
   - Forslag: `mean(downward_flux) > 0`? Eller højere cutoff?
3. ✅ ~~V1/V2 lagnavne~~ → **AFKLARET**: GVForekom navne er 100% kompatible, ingen re-mapping nødvendig
4. ⏳ **Topmag vs per-lag GVD:**
   - Skal vi bruge `dk16_gvd_topmag.tif` (simplere) eller per-lag filer (f.eks. `dk16_gvd_kvs_0400.tif`)?
   - Anbefaling: Start med topmag for simplicitet
5. ⏳ **GVD capping:**
   - Behold 750 mm/år cap fra MST 2016 GrundRisk standard?

**Performance overvejelser:**
- Raster sampling kan være langsomt for mange lokaliteter
- Overvej caching af downward flux og GVD værdier per lokalitet
- Parallel processing hvis muligt

**Backward compatibility strategi:**
- Behold 2019 pipeline funktionel via `DK_MODEL_VERSION` flag
- Gem alle 2019 resultater før migration
- Dokumenter forskelle mellem 2019 og 2023 resultater

---

## OPSUMMERING: Hvad skal der ændres?

### ✅ GODT NYS
1. **GVForekom navne er 100% kompatible** → V1/V2 kobling virker uden ændringer
2. **Mapping struktur er identisk** → Samme `GVForekom → lag` mapping, bare ny kilde
3. **Downward/upward flux filer** → Mulighed for simplere gradient filtrering
4. **Topmag filer** → Mulighed for simplere GVD sampling

### ⚠️ TO ÆNDRINGER NØDVENDIGE

**1. Opdater data kilde (CSV → Geodatabase):**
- `load_gvfk_layer_mapping()`: Load fra geodatabase i stedet for CSV
- `load_rivers()` og `load_qpoints()`: Load fra geodatabase
- Step 1, 2: Brug nye load funktioner

**2. Opdater raster fil naming (DKM_gvd_X.tif → dkX_gvd_X.tif):**
- Step 6, linje ~624: `_sample_infiltration()` funktion
- Tilføj Bornholm check: `lag1-6` → dk7, ellers → dk16
- Construct ny fil sti: `dk16_gvd_kvs_0400.tif` eller `dk7_gvd_lag2.tif`

### 🟡 SIMPLE Find/Replace
- `"DK-modellag"` → `"dkmlag"` i Step 6 (kolonne navn ændring)

### ✅ INGEN ÆNDRINGER
- Step 3: V1/V2 kobling virker som før
- `_parse_dk_modellag()`: Parser format er det samme
- Raster sampling logik: Kun fil stier ændres, ikke sampling metode

### 📊 MIGRERINGS STRATEGI

**Anbefalet rækkefølge:**
1. **config.py**: Tilføj `GRUNDDATA_RESULTS_GDB` og `DKMTIF_DIR_2023` paths (10 min)
2. **data_loaders.py**: Opdater `load_gvfk_layer_mapping()` til geodatabase (30 min)
3. **Test**: Verificer geodatabase load og kolonner (15 min)
4. **Step 6**: Find/Replace `"DK-modellag"` → `"dkmlag"` (5 min)
5. **Step 6**: Opdater `_sample_infiltration()` raster fil naming (1 time)
6. **Test Step 6**: Sample enkelt lokalitet for at verificere (30 min)
7. **Step 1 + 2**: Opdater til geodatabase load (30 min)
8. **End-to-end test**: Kør hele workflow (1 time)
9. **Validation**: Sammenlign resultater (2 timer)

**Estimeret kompleksitet:**
- Core changes: **2-3 timer**
- Testing + validation: **3-4 timer**
- **Total: ~1 arbejdsdag**

---

## REFERENCELISTE

**Litteratur:**
- MST (2016). GrundRisk. Metode til at estimere lertykkelse under jordforureninger, der er kortlagt på V1 og V2. Miljøstyrelsen. Miljøprojekt nr. 1888.
- GEUS Rapport: "Identifikation af målsatte overfladevandsområder og GATØ" - Tabel 1: DK-model2019 VS DK-model2023

**Data kilder:**
- DK-model 2019: `Data/dkm2019_vp3_GVD/`
- DK-model 2023: (Modtages fra Lars - næste uge)

---

## CHANGELOG

**2025-11-26 (Opdatering 2):**
- ✅ **KRITISK OPDAGELSE**: dk7 = Bornholm, dk16 = Danmark (IKKE et valg!)
- ✅ **GODT NYS**: GVForekom navne er 100% kompatible (2042/2043 match)
- ✅ Dokumenteret komplet lagnavne mapping: `ks1, ks2` → `kvs_0400, lag2`
- ✅ Identificeret breaking change: Raster fil naming `DKM_gvd_ks2.tif` → `dk16_gvd_kvs_0400.tif`
- ✅ Detaljeret kode ændringer for Step 6 med eksempler
- ✅ Tilføjet opsummering og migrerings strategi

**2025-11-26 (Opdatering 1):**
- ✅ Data modtaget fra Lars
- ✅ Analyseret ny data struktur (dk7/dk16, geodatabase, downward/upward flux filer)
- ✅ Opdateret spørgsmål 1-3 med faktiske data detaljer
- ✅ Tilføjet "NØDVENDIGE KODE ÆNDRINGER" sektion med prioriteter
- ✅ Opdateret Fase 1 som afsluttet

**2025-11-21:**
- Første version af mødenoter
- Defineret To-Trins GVD håndterings tilgang
- Oprettet handlingsplan for 2023 migration

---

## NÆSTE SKRIDT

**Umiddelbare prioriteter:**
1. ✅ ~~Verificer raster metadata~~ (100x100m, EPSG:25832)
2. ✅ ~~Beslut dk7 vs dk16~~ (BEGGE skal bruges - geografisk opdelt)
3. ✅ ~~Check V1/V2 lagnavne~~ (100% kompatible via GVForekom)
4. ⏳ **Beslut topmag vs per-lag GVD** (anbefaling: topmag for simplicitet)
5. ⏳ **Beslut downward flux threshold** (forslag: > 0 mm/år)
6. ⏳ **Implementer config.py opdateringer** (se "NØDVENDIGE KODE ÆNDRINGER")
7. ⏳ **Test load af geodatabase layers** med geopandas

**Kode implementation rækkefølge:**
1. config.py + data_loaders.py (PRIORITET 1) - **Estimat: 1.5 timer**
2. Step 1 og Step 2 geodatabase integration (PRIORITET 2) - **Estimat: 1 time**
3. Step 6 GVD håndtering refactor (PRIORITET 1 - KRITISK!) - **Estimat: 5 timer**
   - Layer mapping opdatering (kolonne navn ændringer)
   - Downward flux gradient filtrering (Trin 1)
   - GVD raster sampling med nye fil navne (Trin 2)
   - dk7/dk16 geografisk håndtering
4. End-to-end testing og validering - **Estimat: 2-3 timer**
