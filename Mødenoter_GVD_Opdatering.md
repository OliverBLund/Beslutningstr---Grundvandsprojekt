# Mødenoter: GVD Filer og 2023 Opdatering

## Baggrund
Diskussion om anvendelse af GVD (grundvandsdannelse) raster filer i projektet. Nuværende system anvender 2019 versionen, men skal opdateres til 2023 versionen af DK-modellen.

**Vigtig note om gradient retning:**
- **Negative GVD værdier** = opadrettet gradient (grundvand strømmer opad - discharge zone)
- **Positive GVD værdier** = nedadrettet gradient (infiltration - vand strømmer ned gennem kontamineret jord)

---

## 1. Er der tilsvarende raster filer for ks1, ks2 etc. i 2023 versionen på 100x100 m resolution?

### Svar:
I 2023 udgaven af DK-modellen er der blevet lavet nye navne for DK-lagene. De hedder altså **ikke længere ks1, ks2, ps4 osv.**

**Hvad vi får:**
- **To GVD raster datasæt**: 
  - Med indvinding
  - Uden indvinding
- **Ny GVFK shapefile** med kobling til de nye lagnavne
  - Hvordan denne præcist skal anvendes er svært at sige lige nu - er nødt til at se dataen
  - Nye GVFK navne eller de samme som før?
  
  Ny GVFK.shp med nye lagnavne som kan kobles til de nye raster filer (forventligt ligetil).
  
  Lars nævnte en python dictionary med kobling mellem nye og gamle lagnavne?
  
**Andre opdaterede filer (grundet nye modelkørsler):**
- Ny **rivers.shp** fil med vandløbssegmenter
- To **Q95 filer**:
  - En med indvinding
  - En med difference mellem indvinding og ingen indvinding (?)

**Forventet levering:** Næste uge

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

## 3. Er infiltrations-/GVD-rasterne de rette at anvende?

### Kontekst:
- Nuværende tilgang beholder V1/V2 lokaliteter med negative pixel værdier (opadrettet gradient)
- Spørgsmål om alternative filer findes
- Hvis vi skal bruge nogle andre filer, skal det stå **klokkeklart** hvilke filer det skal være

### Svar:
Overordnet set virker det som om at vi får nye GVD rastere + en ny GVFK.shp fil til at koble. 

**Vigtige overvejelser:**
- Dette skal gøres **forsigtigt**
- **Check om der er stor forskel i GVFK navne** mellem de nye og de gamle
  - Specielt vigtigt for V1 og V2 filerne
  - Der skal måske laves en opdateret kobling af V1 og V2 lokaliteterne til den nye GVFK fil hvis det er en rigtig ny GVFK fil med alle GVFK ligesom den der anvendes lige pt i step 1

**Yderligere filer fra Lars:**
- **Infiltrations oplands**: Måske interessante at kigge på
- **Flux til lag1_2 fil**: Til at undersøge om der er nedadrettet gradient for en lokalitet
- **En anden fil**: (ikke helt fanget hvad denne indeholder)

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

## HANDLINGSPLAN: Implementering af 2023 DK-Model Opdatering

### Fase 1: Modtagelse og Validering af Nye Data (Uge 1)

**Opgaver:**
1. ✅ **Modtag filer fra Lars:**
   - [ ] To GVD raster datasæt (med/uden indvinding)
   - [ ] Ny GVFK shapefile med lagnavne kobling
   - [ ] Ny rivers.shp fil
   - [ ] To Q95 filer
   - [ ] Opdateret Q-punkter fil
   - [ ] Infiltrations oplands filer (optional)
   - [ ] Flux til lag1_2 fil
   - [ ] Anden fil (afvent specifikation)

2. ✅ **Inspicer nye data:**
   - [ ] Check GVFK navne: Er de ændret fra 2019 version?
   - [ ] Sammenlign GVFK antal: 2019 (~2044) vs. 2023 (?)
   - [ ] Check nye lagnavne struktur (erstatter ks1, ks2, ps4, etc.)
   - [ ] Verificer raster resolution (100x100m eller 500x500m?)
   - [ ] Check CRS/projektion konsistens

3. ✅ **Dokumenter ændringer:**
   - [ ] Opret mapping tabel: Gamle lagnavne → Nye lagnavne
   - [ ] Dokumenter GVFK navne ændringer (hvis relevante)
   - [ ] Noter fil format ændringer

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

### Fase 8: Afsluttende Overvejelser

**Spørgsmål til afklaring med Lars/GEUS:**
1. [ ] Hvilken GVD version skal bruges: Med eller uden indvinding?
   - Rationale for valg?
2. [ ] Skal vi anvende infiltrations oplands filerne?
   - Hvordan integreres disse?
3. [ ] Hvad indeholder "flux til lag1_2" filen præcist?
   - Kan denne bruges til at validere vores gradient retnings assessment?
4. [ ] Q95 filer: Skal vi bruge "med indvinding" eller "difference" versionen?
   - Hvad er anbefalingen for risikovurdering?

**Performance overvejelser:**
- [ ] Raster sampling kan være langsomt for mange lokaliteter
- [ ] Overvej caching af GVD værdier per lokalitet
- [ ] Parallel processing hvis muligt

**Backup strategi:**
- [ ] Behold 2019 pipeline funktionel (backward compatibility)
- [ ] Gem alle 2019 resultater før migration
- [ ] Config flag til at skifte mellem versioner

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

**2025-11-21:**
- Første version af mødenoter
- Defineret To-Trins GVD håndterings tilgang
- Oprettet handlingsplan for 2023 migration

---

**Næste skridt:** Afvent modtagelse af 2023 data filer (næste uge)
