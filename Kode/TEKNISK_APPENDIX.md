# TEKNISK APPENDIX: RISIKOVURDERING AF GRUNDVANDSFOREKOMSTERS PÅVIRKNING AF OVERFLADEVAND

**Projekt:** Beslutningstræ for grundvandsforekomsters påvirkning af overfladevand
**Forfatter:** Oliver B. Lund
**Dato:** 6. Oktober 2025
**Institution:** DTU Sustain i samarbejde med GEUS, SGAV og Miljøstyrelsen

---

## 1. INTRODUKTION & SETUP

### 1.1 Projektoverblik

Dette appendix dokumenterer den tekniske implementation af et automatiseret beslutningstræ til risikovurdering og tilstandsvurdering af forureningslokaliteter i grundvandsforekomster og deres potentielle påvirkning af overfladevand. Appendixet er målrettet tekniske læsere, udviklere og fagfolk der ønsker at forstå, reproducere eller videreudvikle workflowet.

Metoden anvender en systematisk fem-trins tilgang til risikovurdering efterfulgt af en kvantitativ tilstandsvurdering, baseret på principper fra Miljøstyrelsens vejledning for screening af jordforurening mod overfladevand.

### 1.2 Tekniske Krav

**Python Environment:**
- Python 3.8+
- Nøglebiblioteker:
  - `geopandas` ≥0.10.0 (spatial data manipulation)
  - `pandas` ≥1.3.0 (data processing)
  - `shapely` ≥1.8.0 (geometric operations)
  - `numpy` (numerical operations)

**Koordinatsystem:**
- Alle spatiale operationer udføres i EPSG:25832 (UTM Zone 32N, EUREF89)
- Afstandsberegninger i meter

**Hardware:**
- Minimum 8 GB RAM anbefales for processing af landsdækkende datasæt
- Forventet runtime: ~5-10 minutter for komplet workflow

### 1.3 Mappestruktur

```
Beslutningstræ - Grundvands projekt/
├── Kode/
│   ├── step1_all_gvfk.py
│   ├── step2_river_contact.py
│   ├── step3_v1v2_sites.py
│   ├── step4_distances.py
│   ├── step5_risk_assessment.py
│   ├── tilstandsvurdering/
│   │   └── step6_tilstandsvurdering.py
│   └── risikovurdering/
│       ├── compound_matching.py
│       └── refined_compound_analysis.py
├── Data/
│   ├── VP3Genbesøg_grundvand_geometri.shp
│   ├── Rivers_gvf_rev20230825_kontakt.shp
│   ├── V1FLADER.shp
│   ├── V2FLADER.shp
│   ├── v1_gvfk_forurening.csv
│   └── v2_gvfk_forurening.csv
└── Output/
    ├── step2_river_gvfk.shp
    ├── step3_v1v2_sites.shp
    ├── step4_final_distances.csv
    ├── step5_high_risk_sites_500m.csv
    └── step5_compound_detailed_combinations.csv
```

### 1.4 Datakilder

**Shapefiler:**
- **VP3Genbesøg_grundvand_geometri.shp:** Grundvandsforekomster (GVFK) fra national registry
- **Rivers_gvf_rev20230825_kontakt.shp:** Vandløbssegmenter med GVFK-tilknytning og kontaktflag (fra DK-Model, Lars Troldborg, GEUS)
- **V1FLADER.shp / V2FLADER.shp:** Kortlagte V1/V2-lokaliteter fra DK-jord (Danmarks Miljøportal, udtræk 27-09-2024)

**CSV-filer:**
- **v1_gvfk_forurening.csv / v2_gvfk_forurening.csv:** Pre-processerede data med lokalitets-GVFK relationer, forureningsstoffer, branche- og aktivitetsoplysninger. Skabt via V1V2.py script med ArcGIS spatial join + DK-jord data.

Se "Fremgangsmåde til klassifikationer af forurenede grunde.docx" (Luc Taliesin Eisenbrückner, september 2024) for detaljer om CSV-generering.

---

## 2. WORKFLOW OVERBLIK

### 2.1 Risikovurdering (Trin 1-5)

Risikovurderingen identificerer potentielt problematiske lokaliteter gennem systematisk filtrering og afstandsbaseret kategorisering:

1. **Trin 1 - Baseline:** Optælling af alle grundvandsforekomster
2. **Trin 2 - Kontakt:** Filtrering til GVFK med vandløbskontakt
3. **Trin 3 - Lokaliteter:** Identifikation af V1/V2-lokaliteter i GVFK med vandløbskontakt
4. **Trin 3b - Infiltrationsfilter:** Filtrering baseret på grundvandsstrømningsretning (fjerner discharge-zoner)
5. **Trin 4 - Afstande:** Beregning af afstand fra lokaliteter til vandløb
6. **Trin 5 - Kategorisering:** To-lags risikovurdering:
   - **5a - Generel:** 500 m universal tærskel
   - **5b - Stofspecifik:** Variable tærskler 30-500 m baseret på stofmobilitet

### 2.2 Tilstandsvurdering (Trin 6)

Tilstandsvurderingen kvantificerer faktisk påvirkning af vandløb:

6. **Trin 6 - Flux & Koncentration:** Beregning af forureningsflux fra højrisiko-lokaliteter, transport til vandløb, blandingskoncentration (Cmix) og sammenligning med miljøkvalitetskrav (MKK)

### 2.3 Data Flow Diagram

```
[VP3 GVFK geometri]  [Rivers kontakt]  [V1/V2 FLADER]  [v1/v2_gvfk_forurening.csv]
        │                   │                  │                    │
        ▼                   ▼                  │                    │
   ┌─────────┐       ┌──────────┐             │                    │
   │ Trin 1  │       │  Trin 2  │             │                    │
   │Baseline │───────│ Kontakt  │             │                    │
   │  GVFK   │       │   GVFK   │             │                    │
   └─────────┘       └──────────┘             │                    │
                           │                   │                    │
                           ▼                   ▼                    ▼
                     ┌──────────────────────────────────────────────┐
                     │      Trin 3: V1/V2 Lokaliteter               │
                     │    Lokaliteter i GVFK med kontakt            │
                     └──────────────────┬───────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────┐
                     │    Trin 3b: Infiltrationsfilter              │
                     │  Fjern discharge-zoner (upward flow)         │
                     │     [GVD raster + layer mapping]             │
                     └──────────────────┬───────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────┐
                     │      Trin 4: Afstandsberegning               │
                     │   Kombinationer med afstand til vandløb      │
                     └──────────────────┬───────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────┐
                     │        Trin 5: Kategorisering                │
                     │    5a: Generel (500m)                        │
                     │    5b: Stofspecifik (30-500m)                │
                     └──────────────────┬───────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────┐
                     │     Trin 6: Tilstandsvurdering               │
                     │  Flux, Cmix, MKK-sammenligning               │
                     └──────────────────────────────────────────────┘
```

---

## 3. DETALJERET TRIN-FOR-TRIN SPECIFIKATION

### TRIN 1: OPTÆLLING AF GRUNDVANDSFOREKOMSTER

#### Input

**Fil:** `VP3Genbesøg_grundvand_geometri.shp`
- **Kilde:** National grundvandsforekomst (GVFK) registry fra Danmark
- **Features:** 2.043 grundvandsforekomst-polygoner
- **CRS:** EPSG:25832 (UTM Zone 32N, EUREF89)
- **Nøglekolonner:**
  - `Navn` (string): Unik identifikator for hver grundvandsforekomst
  - `geometry` (polygon): Spatiale afgrænsninger af GVFK

#### Metodologi

Dette trin etablerer en baseline-optælling af alle grundvandsforekomster i Danmark. Formålet er at skabe et referencepunkt for de efterfølgende filtreringstrin, så man kan beregne hvor stor en andel af alle GVFK'er der passerer hvert filter.

Shapefilen indlæses med `geopandas.read_file()`, som automatisk håndterer koordinatsystem-detektion og geometri-parsing. Der foretages en kolonne-validering for at sikre, at `Navn`-feltet eksisterer, da dette felt bruges som primær identifikator gennem hele workflowet.

Antallet af unikke grundvandsforekomster beregnes med `df['Navn'].nunique()`, som returnerer antallet af distinkte ikke-null værdier i `Navn`-kolonnen.

Der anvendes ingen filtrering eller transformationer på dette trin. Det fulde datasæt bevares i hukommelsen som en GeoDataFrame til brug i efterfølgende trin.

#### Output

**Kun i hukommelsen** (ingen filer skrives til disk)

Trinnet returnerer:
- **GeoDataFrame:** Komplet datasæt med alle GVFK-geometrier og attributter
- **Integer:** Antal unikke grundvandsforekomster

Dette output bruges som nævner til procentberegninger i senere filtreringstrin.

---

### TRIN 2: GRUNDVANDSFOREKOMSTER MED VANDLØBSKONTAKT

#### Input

**Fil 1:** `Rivers_gvf_rev20230825_kontakt.shp`
- **Kilde:** DK-Model vandløbsnetværk med GVFK-tilknytning (Lars Troldborg, GEUS, rev. 25-08-2023)
- **Features:** [antal] vandløbssegmenter
- **CRS:** EPSG:25832
- **Nøglekolonner:**
  - `GVForekom` (string): GVFK-navn tilknyttet vandløbssegmentet
  - `Kontakt` (integer): Kontaktflag (1 = har kontakt, 0 = ingen kontakt) - kan være fraværende i nyere Grunddata format
  - `geometry` (linestring): Vandløbssegment-geometri

**Fil 2:** `VP3Genbesøg_grundvand_geometri.shp`
- Samme som Trin 1 (genbruges fra hukommelse eller disk)

#### Metodologi

Dette trin identificerer de grundvandsforekomster hvor der forekommer faktisk grundvand-overfladevand interaktion, hvilket er en forudsætning for at forurening kan sprede sig fra grundvandet til vandløb.

**Vandløbsfiltrering:**
Vandløbsdata indlæses med `geopandas.read_file()`. Kolonnen `GVForekom` renses for whitespace ved hjælp af `.str.strip()` og konverteres til strenge for ensartet sammenligning.

Der anvendes to forskellige filtreringslogikker afhængigt af dataformat:
- **Legacy format:** Hvis kolonnen `Kontakt` eksisterer, filtres til segmenter hvor `Kontakt == 1` OG `GVForekom` ikke er tom
- **Nyere Grunddata format:** Hvis `Kontakt`-kolonnen ikke eksisterer, antages det at tilstedeværelsen af et GVFK-navn i `GVForekom` i sig selv indikerer kontakt

**Ekstraktion af GVFK-navne:**
Fra de filtrerede vandløbssegmenter ekstraheres unikke GVFK-navne med `.unique()`. None-værdier og ikke-string typer fjernes via list comprehension for at sikre kun gyldige GVFK-identifikatorer bevares.

**Geometri-kobling:**
GVFK-geometrier fra Trin 1 filtreres til kun dem hvis `Navn` findes i listen af GVFK'er med vandløbskontakt. Dette udføres med `df[df['column'].isin(list)]`, som er en effektiv pandas-operation for membership testing.

**Note:** Der kan observeres en mindre diskrepans mellem antallet af unikke GVFK-navne fra vandløbsdata og antallet af geometrier i output. Dette skyldes at enkelte GVFK-navne fra vandløbsdata ikke findes i VP3-geometrifilen (potentielt navneforskel eller versionforskelle mellem datasættene).

#### Output

**Fil:** `step2_river_gvfk.shp`
- **Features:** [antal] GVFK-polygoner med vandløbskontakt
- **CRS:** EPSG:25832
- **Kolonner:** Alle kolonner fra input VP3-filen bevares
- **Formål:** Geografisk subset af GVFK'er til brug i Trin 3

**I hukommelsen:**
- **Liste:** GVFK-navne med vandløbskontakt
- **Integer:** Antal unikke GVFK med kontakt
- **GeoDataFrame:** GVFK-geometrier med vandløbskontakt

Dette subset repræsenterer de grundvandsforekomster hvor forurening potentielt kan sprede sig til overfladevand gennem dokumenteret grundvand-vandløb interaktion.

---

### TRIN 3: V1/V2-LOKALITETER I GVFK MED VANDLØBSKONTAKT

#### Input

**CSV-filer:**

**Fil 1:** `v1_gvfk_forurening.csv`
- **Kilde:** Pre-processeret via V1V2.py med ArcGIS spatial join + DK-jord data
- **Rækker:** [antal] rækker med V1-lokalitetsdata
- **Nøglekolonner:**
  - `Lokalitetsnr` (string): Lokalitetsidentifikator
  - `Navn` (string): GVFK-navn fra ArcGIS spatial join
  - `Lokalitetensstoffer` (string): Forureningsstof (ét stof per række)
  - `Lokalitetensbranche` (string): Branche-information (semikolon-separeret liste)
  - `Lokalitetensaktivitet` (string): Aktivitetstype (semikolon-separeret liste)
  - Andre metadata-kolonner (status, region, kommune, etc.)

**Fil 2:** `v2_gvfk_forurening.csv`
- Samme struktur som V1
- **Rækker:** [antal] rækker med V2-lokalitetsdata

**Note om input datastruktur:** Samme lokalitet kan forekomme flere gange i CSV'en - én række per unikt stof i `Lokalitetensstoffer`. Branche og aktivitet er lagret som semikolon-separerede lister for at undgå yderligere rækkeeksplosion.

**Shapefiler:**

**Fil 3:** `V1FLADER.shp`
- **Kilde:** DK-jord udtræk, Danmarks Miljøportal
- **Features:** [antal] polygoner
- **CRS:** EPSG:25832
- **Nøglekolonner:**
  - `Lokalitet_` (eller `Lokalitets`/`Lokalitetsnr`/`LokNr`): Lokalitetsidentifikator
  - `geometry` (polygon/multipolygon): Lokalitetens geografiske udstrækning

**Fil 4:** `V2FLADER.shp`
- Samme struktur som V1FLADER.shp
- **Features:** [antal] polygoner

**Fra Trin 2:**
- Liste med GVFK-navne der har vandløbskontakt

#### Metodologi

Dette trin identificerer forurenede lokaliteter i grundvandsforekomster med vandløbskontakt og bevarer én-til-mange lokalitet-GVFK relationer. En enkelt lokalitet kan overlappe flere GVFK'er, hvilket kræver separate afstandsberegninger i Trin 4.

**Eksempel på én-til-mange relation:**
Lokalitet "12345" overlapper to GVFK-polygoner ("GVFK_A" og "GVFK_B"), hvilket resulterer i to kombinationer: (12345, GVFK_A) og (12345, GVFK_B). Hver kombination skal have sin egen afstand beregnet i Trin 4.

##### 1. Indlæsning og Initial Filtrering

CSV-data indlæses med `pandas.read_csv()`. Der foretages en kvalificerings-filtrering baseret på tilstedeværelse af forureningsdata:

**Kvalificeringskriterier (OR-logik):**
En lokalitet kvalificerer hvis den har:
- **Stofdata:** `Lokalitetensstoffer` er ikke-tom (efter `.notna()` og `.str.strip()`)
- **ELLER Branchedata:** `Lokalitetensbranche` er ikke-tom

Dette sikrer at både lokaliteter med dokumenterede forureningsstoffer OG lokaliteter med potentielt forurenende aktiviteter (uden registrerede stoffer) inkluderes.

Kvalificerede lokaliteter kategoriseres i tre grupper:
- Kun stofdata (har stoffer, ingen branche)
- Kun branchedata (har branche, ingen stoffer)
- Begge dele (har både stoffer og branche)

Lokaliteter uden hverken stof- eller branchedata filtreres fra.

##### 2. Geometri-Processering med Caching

Shapefiler indlæses og dissolves for at håndtere multipart-polygoner (en lokalitet kan bestå af flere separate geografiske områder).

**Dissolve-operation:**
```python
dissolved = gdf.dissolve(by=locality_col, as_index=False)
```

Dette aggregerer alle polygoner med samme lokalitetsnummer til én multipart-feature.

**Caching-mekanisme:**
For at undgå gentagen dissolve-processering (som er computationelt tung), gemmes dissolved geometrier i en cache-mappe. Ved efterfølgende kørsler tjekkes:
1. Om cache-filen eksisterer
2. Om cache-filen er nyere end kilde-shapefiles (via timestamp-sammenligning)

Hvis cache er valid, indlæses direkte herfra. Ellers dissolves på ny og cache opdateres.

##### 3. Filtrering til Vandløbskontakt-GVFK

CSV-data filtreres til kun kombinationer hvor `Navn`-kolonnen (GVFK-identifikator) findes i listen fra Trin 2:

```python
filtered = csv_data[csv_data['Navn'].isin(rivers_gvfk_set)]
```

Dette sikrer at kun lokaliteter i GVFK'er med vandløbskontakt bevares.

##### 4. Aggregering af Lokalitet-GVFK Kombinationer

For at håndtere den oprindelige CSV-struktur (hvor samme lokalitet-GVFK kombination kan forekomme flere gange på grund af forskellige stoffer på separate rækker), aggregeres data:

```python
grouped = df.groupby(['Lokalitet_', 'Navn']).agg({
    'Lokalitetensstoffer': lambda x: '; '.join(x.dropna().astype(str).unique()),
    # Andre kolonner: 'first'
})
```

Dette samler alle stoffer for en given lokalitet-GVFK kombination til én semikolon-separeret streng (konsistent med branche og aktivitet formatering), mens andre attributter bevarer den første værdi. Efter denne operation har hver lokalitet-GVFK kombination præcis én række.

##### 5. Join med Geometrier

Aggregerede CSV-data joins med dissolved geometrier:

```python
result = geometries.merge(csv_aggregated,
                         left_on=locality_col_shp,
                         right_on='Lokalitet_',
                         how='inner')
```

Inner join sikrer at kun lokaliteter med både attributdata OG geometri bevares.

##### 6. Kombinering og Deduplikering af V1 og V2

V1 og V2 datasæt kombineres med `pd.concat()`. Dubletter identificeres som lokalitet-GVFK kombinationer der findes i både V1 og V2.

**Deduplikerings-logik:**

For hver unik (Lokalitet, GVFK) kombination:
- **Hvis kun i V1:** Bevar som "V1", ingen ændringer
- **Hvis kun i V2:** Bevar som "V2", ingen ændringer
- **Hvis i både V1 og V2:**
  - Aggreger alle stoffer fra begge registreringer (fjern dubletter)
  - Marker `Lokalitete`-kolonne som "V1 og V2"
  - Bevar geometri og øvrige attributter fra den ene registrering

Dette implementeres via iteration over alle kombinationer med progress bar (`tqdm`).

#### Output

**Fil 1:** `step3_v1v2_sites.shp`
- **Features:** [antal] lokalitet-GVFK kombinationer med geometri
- **CRS:** EPSG:25832
- **Nøglekolonner:**
  - `Lokalitet_` (string): Lokalitetsidentifikator
  - `Navn` (string): GVFK-navn
  - `Lokalitetensstoffer` (string): Aggregerede forureningsstoffer (semikolon-separeret liste)
  - `Lokalitete` (string): Klassifikation ("V1", "V2", eller "V1 og V2")
  - `geometry` (polygon/multipolygon): Lokalitetens geometri
  - Alle metadata-kolonner fra CSV-input
- **Formål:** Input til Trin 4 afstandsberegning

**Fil 2:** `step3_gvfk_with_v1v2.shp`
- **Features:** [antal] GVFK-polygoner
- **CRS:** EPSG:25832
- **Indhold:** Subset af GVFK'er der indeholder mindst én V1/V2-lokalitet
- **Formål:** Geografisk visualisering af berørte GVFK'er

**I hukommelsen:**
- **Set:** GVFK-navne med V1/V2-lokaliteter
- **GeoDataFrame:** Kombinerede V1/V2-data til Trin 4

**Dataflow til Trin 3b:**
Output fra dette trin sendes videre til Trin 3b for infiltrationsfiltrering baseret på grundvandsstrømningsretning.

---

### TRIN 3B: INFILTRATIONSFILTER

#### Input

**Fra Trin 3:** `step3_v1v2_sites.shp` (GeoDataFrame i hukommelse)
- **Features:** [antal] lokalitet-GVFK kombinationer
- **Nøglekolonner:**
  - `Lokalitet_` (string): Lokalitetsidentifikator
  - `Navn` (string): GVFK-navn
  - `geometry` (polygon/multipolygon): Lokalitetens geometri

**Eksternt data:**

**GVFK Layer Mapping:** Kobling mellem GVFK og DK-model lag
- **Kolonner:**
  - `GVForekom` (string): GVFK-navn
  - `dkmlag` (string): DK-modellag identifikator (semikolon-separeret liste)
  - `dknr` (string): DK-model region (f.eks. "dk16" eller "dk7")

**GVD Raster Data:** Grundvandsdynamik infiltrationsraster
- **Format:** GeoTIFF filer for hvert DK-modellag
- **Navnekonvention:** `{dk16|dk7}_gvd_{lag}.tif` (f.eks. `dk16_gvd_ks1.tif`)
- **Værdier:**
  - Positive værdier (≥0): Downward flow (infiltration)
  - Negative værdier (<0): Upward flow (discharge)
  - NoData: Ingen infiltrationsdata tilgængelig

#### Metodologi

Dette trin filtrerer lokaliteter baseret på grundvandsstrømningsretning. Lokaliteter i discharge-zoner (upward flow) kan ikke transportere forurening til vandløb og fjernes fra videre analyse.

**Rationale:** Kun lokaliteter med downward flow (infiltration) udgør en risiko for transport af forurening til vandløb gennem grundvandssystemet.

##### 1. GVFK-til-Modellag Kobling

For hver lokalitet-GVFK kombination kobles GVFK-navnet med DK-modellag information:

```python
enriched = df.merge(layer_mapping, left_on='GVFK', right_on='GVForekom', how='left')
```

**DK-modellag parsing:**
Kolonnen `dkmlag` indeholder typisk flere lag separeret med semikolon, f.eks. `"1:ks1;2:ks2"`. Disse parses til individuelle lag-koder:
- `"1:ks1;2:ks2"` → `["ks1", "ks2"]`
- Prefix (f.eks. "1:", "2:") fjernes, kun lag-koden bevares
- Duplikater elimineres

**Model region:**
Kolonnen `dknr` identificerer om GVFK tilhører DK16 (hovedmodel) eller DK7 (regionale modeller). Default: `"dk16"`.

##### 2. Raster Sampling Strategi

For hver lokalitet-GVFK kombination og hvert DK-modellag samples infiltrationsdata:

**Filnavnskonstruktion:**
```python
raster_file = f"{region_prefix}_gvd_{layer}.tif"
# Eksempel: "dk16_gvd_ks1.tif"
```

**To-trins sampling (polygon-first med centroid fallback):**

**Trin 1 - Polygon sampling (foretrukket):**
```python
masked_data, _ = rasterio.mask.mask(src, geometry, crop=True, all_touched=False)
valid_pixels = masked_data[(masked_data != nodata) & (~np.isnan(masked_data))]
```

Dette udtrækker ALLE pixels der overlapper lokalitetens polygon-geometri. Fordele:
- Repræsentativt sample af hele lokalitetsområdet
- Robust for større lokaliteter
- Fanger spatial variabilitet i infiltration

**Trin 2 - Centroid sampling (fallback):**
Hvis polygon sampling fejler eller returnerer 0 pixels, samples ved lokalitetens centroid:
```python
centroid_value = src.sample([(centroid.x, centroid.y)])
```

Anvendes for:
- Meget små lokaliteter uden pixels
- Edge cases ved raster-grænser
- Geometri-fejl

##### 3. Multi-Layer Aggregering

Hvis en GVFK er tilknyttet flere DK-modellag (f.eks. `["ks1", "ks2", "ks3"]`), samples alle lag og alle pixels aggregeres:

```python
all_pixel_values = []
for layer in layers:
    pixel_values = sample_raster(layer, geometry, centroid)
    if pixel_values:
        all_pixel_values.extend(pixel_values)
```

Dette sikrer at alle relevante grundvandslag indgår i flow direction vurderingen.

##### 4. Majority Voting for Flow Direction

Flow direction bestemmes via majority voting på alle aggregerede pixels:

```python
binary_values = [1 if pixel_value >= 0 else 0 for pixel_value in all_pixel_values]
majority_vote = sum(binary_values) / len(binary_values)

if majority_vote > 0.5:
    flow_direction = "downward"
else:
    flow_direction = "upward"
```

**Klassifikation:**
- **Downward:** >50% af pixels har værdi ≥0 (infiltration)
- **Upward:** ≤50% af pixels har værdi ≥0 (discharge)
- **No_data:** Ingen gyldige pixels kunne samples

**Grænsetilfælde:**
Lokaliteter med ~50% positive pixels klassificeres som "upward" (konservativ tilgang). Dette kan forekomme i:
- Overgangszoner mellem infiltration og discharge
- Lokaliteter der spænder over flere hydrologiske regimer
- Meget små lokaliteter med få pixels

##### 5. Diagnostisk Analyse

Under processering trackes følgende statistikker:

**Per site-GVFK kombination:**
- Antal pixels sampled
- Majority vote procent (andel positive pixels)
- Flow direction klassifikation

**Aggregerede statistikker:**
- Gennemsnitligt og median antal pixels per kombination
- Distribution af majority votes
- Grænsetilfælde (45-55% positive pixels)
- Sites med få pixels (≤5, ≤10)

**Per-site analyse:**
For lokaliteter i multiple GVFK'er aggregeres total pixel count på tværs af alle GVFK-affilieringer for at vurdere samlet datasikkerhed.

##### 6. Filtrering

Baseret på flow direction klassifikation filtreres kombinationer:

**BEVARES (sendes til Trin 4):**
```python
filtered = df[(df['Flow_Direction'] == 'downward') |
              (df['Flow_Direction'] == 'no_data')]
```

- **Downward flow:** Kan transportere forurening til vandløb
- **No_data:** Konservativ tilgang - bevar ved manglende data

**FJERNES:**
```python
removed = df[df['Flow_Direction'] == 'upward']
```

- **Upward flow:** Discharge-zoner kan ikke transportere forurening til vandløb

Fjernede kombinationer gemmes i audit-fil for sporbarhed.

##### 7. Håndtering af Manglende Data

Følgende situationer resulterer i `flow_direction = "no_data"`:

- GVFK mangler DK-modellag mapping
- Ingen raster-filer findes for de angivne lag
- Polygon og centroid sampling begge fejler
- Geometri er invalid eller tom

Disse kombinationer bevares (konservativ tilgang).

#### Output

**Fil 1:** `step3b_filtered_sites.shp`
- **Features:** [antal] lokalitet-GVFK kombinationer med downward flow eller no_data
- **CRS:** EPSG:25832
- **Kolonner:** Samme som input fra Trin 3 (uden `Flow_Direction` kolonne)
- **Formål:** Filtreret input til Trin 4 afstandsberegning

**Fil 2:** `step3b_removed_upward_flow.csv`
- **Rækker:** [antal] fjernede lokalitet-GVFK kombinationer
- **Kolonner:** `Lokalitet_`, `Navn`
- **Formål:** Audit trail for fjernede discharge-zone lokaliteter

**Performance fordel:**
Ved at filtrere FØR Trin 4 undgås unødvendige afstandsberegninger for lokaliteter der alligevel ville blive filtreret fra senere. Dette reducerer computational overhead betydeligt.

---

### TRIN 4: AFSTANDSBEREGNING TIL VANDLØB

#### Input

**Fra Trin 3b:** `step3b_filtered_sites.shp` (GeoDataFrame i hukommelse)
- **Features:** [antal] lokalitet-GVFK kombinationer (efter infiltrationsfiltrering)
- **Nøglekolonner:**
  - `Lokalitet_` (string): Lokalitetsidentifikator
  - `Navn` (string): GVFK-navn for denne kombination
  - `geometry` (polygon/multipolygon): Lokalitetens geometri
  - Alle metadata-kolonner fra Trin 3

**Fra Datagrundlag:** `Rivers_gvf_rev20230825_kontakt.shp`
- Samme fil som i Trin 2
- Genindlæses for at få vandløbssegmenter med kontaktinformation

#### Metodologi

Dette trin beregner minimumsafstanden fra hver lokalitet-GVFK kombination til vandløbssegmenter med grundvandskontakt inden for samme GVFK. Alle kombinationer bevares - der reduceres ikke til minimumsafstand per lokalitet, da forskellige GVFK'er har forskellige vandløbsnetværk.

**Kritisk koncept:** Én lokalitet kan have forskellige afstande til vandløb i forskellige GVFK'er. Eksempel:
- Lokalitet "12345" i GVFK_A: 50m til nærmeste vandløb i GVFK_A
- Lokalitet "12345" i GVFK_B: 300m til nærmeste vandløb i GVFK_B

Begge afstande bevares, da de repræsenterer forskellige forureningsrisici.

##### 1. Indlæsning og Filterering af Vandløbsdata

Vandløbsdata indlæses med `geopandas.read_file()` og filtreres til segmenter med GVFK-kontakt (samme logik som Trin 2):

```python
if 'Kontakt' in rivers.columns:
    rivers_contact = rivers[(rivers['Kontakt'] == 1) & (rivers['GVForekom'] != "")]
else:
    rivers_contact = rivers[rivers['GVForekom'] != ""]
```

**CRS-validering:**
Hvis vandløbsdata har et andet koordinatsystem end lokalitetsdata, transformeres med `.to_crs()` for at sikre korrekte afstandsberegninger.

##### 2. Iteration gennem Lokalitet-GVFK Kombinationer

For hver af de [antal] kombinationer fra Trin 3 udføres følgende:

```python
for idx, row in tqdm(v1v2_combined.iterrows(), total=len(v1v2_combined)):
    lokalitet_id = row['Lokalitet_']
    gvfk_name = row['Navn']
    site_geom = row.geometry
```

Progress visualiseres med `tqdm` progress bar.

##### 3. Matching af Vandløbssegmenter

For hver kombination identificeres alle vandløbssegmenter i det specifikke GVFK:

```python
matching_rivers = rivers_contact[rivers_contact['GVForekom'] == gvfk_name]
```

Denne filtrering sikrer at:
- Kun vandløb i samme GVFK inkluderes
- Afstanden beregnes til relevante vandløbssegmenter for forureningsspredning

Metadata om matchende segmenter gemmes:
- Antal matchende segmenter
- FID (Feature ID) for alle matchende segmenter (semikolon-separeret)
- OV_ID (overfladevand-ID) hvis tilgængelig (semikolon-separeret)

##### 4. Afstandsberegning

Hvis der findes matchende vandløbssegmenter, beregnes minimum euklidisk afstand:

```python
min_distance = float('inf')
for river_idx, river in matching_rivers.iterrows():
    distance = site_geom.distance(river.geometry)
    if distance < min_distance:
        min_distance = distance
        nearest_river_idx = river_idx
```

**Geometrisk operation:**
- `geometry.distance()` beregner minimum euklidisk afstand mellem to geometrier
- For polygon-til-linestring: afstand fra polygonens kant til nærmeste punkt på linjen
- Hvis polygon overlapper eller berører vandløb: afstand = 0,0 m
- Enhed: meter (da CRS er EPSG:25832)

For den nærmeste vandløbsstræknings metadata gemmes:
- FID (Feature ID)
- OV_ID (overfladevand identifikator)
- OV_navn (vandløbsnavn)

##### 5. Metadata-Bevarelse

Alle relevante kolonner fra Trin 3 bevares i output:
- `Lokalitetensbranche`
- `Lokalitetensaktivitet`
- `Lokalitetensstoffer`
- `Lokalitetsnavn`
- `Lokalitetetsforureningsstatus`
- `Regionsnavn`
- `Kommunenavn`

Dette sikrer at Trin 5 har adgang til al nødvendig information for stofspecifik risikovurdering.

##### 6. Minimum-Afstand Identifikation

Efter alle afstande er beregnet, identificeres minimum-afstanden for hver unik lokalitet:

```python
site_min_distances = results.groupby('Lokalitet_ID')['Distance_to_River_m'].min()
results['Is_Min_Distance'] = (results['Distance_to_River_m'] == results['Min_Distance_m'])
```

Dette tilføjer:
- `Min_Distance_m`: Minimum afstand på tværs af alle GVFK'er for denne lokalitet
- `Is_Min_Distance`: Boolean flag der indikerer om denne kombination har lokalitetens minimum-afstand

**Formål:** Tillader senere analyser at fokusere på "worst case" (korteste afstand), men bevarer alle kombinationer til stofspecifik vurdering.

##### 7. Håndtering af Manglende Matches

Hvis en lokalitet-GVFK kombination ikke har nogen matchende vandløbssegmenter:
- `Distance_to_River_m` sættes til `None`/`NaN`
- `Has_Matching_Rivers` sættes til `False`
- Kombinationen bevares i output for sporbarhed

Disse kombinationer filtreres typisk fra i senere trin.

#### Output

**Fil:** `step4_final_distances_for_risk_assessment.csv`
- **Rækker:** [antal] lokalitet-GVFK kombinationer med gyldige afstande
- **Kolonner:**
  - `Lokalitet_ID` (string): Lokalitetsidentifikator
  - `GVFK` (string): GVFK-navn
  - `Site_Type` (string): "V1", "V2", eller "V1 og V2"
  - `Distance_to_River_m` (float): Afstand i meter til nærmeste vandløb i dette GVFK
  - `Min_Distance_m` (float): Minimum afstand for denne lokalitet på tværs af alle GVFK'er
  - `Is_Min_Distance` (boolean): Om dette er lokalitetens minimum-afstand
  - `Nearest_River_FID` (integer): Feature ID for nærmeste vandløbssegment
  - `Nearest_River_ov_id` (string): Overfladevand-ID for nærmeste vandløb
  - `Nearest_River_ov_navn` (string): Navn på nærmeste vandløb
  - `River_Segment_Count` (integer): Antal vandløbssegmenter i dette GVFK
  - `River_Segment_FIDs` (string): Semikolon-separeret liste af alle segment FID'er
  - `River_Segment_ov_ids` (string): Semikolon-separeret liste af alle segment OV_ID'er
  - Alle metadata-kolonner fra Trin 3 (stoffer, branche, aktivitet, status, region, kommune)
- **Formål:** Kritisk input til Trin 5 risikovurdering

**Sekundært output (kun visualisering):**
Koden opretter også en interaktiv HTML-kort visualisering med sampled data (max 1000 lokaliteter for performance), men dette er ikke del af den kritiske workflow.

**Dataflow til Trin 5:**
Alle lokalitet-GVFK kombinationer med gyldige afstande sendes videre til Trin 5, hvor afstandstærskler anvendes for kategorisering.

---

### TRIN 5: TÆRSKEL-VURDERING OG KATEGORISERING

#### Input

**Fra Trin 4:** `step4_final_distances_for_risk_assessment.csv`
- **Rækker:** [antal] lokalitet-GVFK kombinationer med afstandsdata
- **Nøglekolonner:**
  - `Lokalitet_ID` (string): Lokalitetsidentifikator
  - `GVFK` (string): GVFK-navn
  - `Distance_to_River_m` (float): Afstand til vandløb i meter
  - `Lokalitetensstoffer` (string): Semikolon-separeret liste af forureningsstoffer
  - `Lokalitetensbranche` (string): Semikolon-separeret liste af brancher
  - `Lokalitetensaktivitet` (string): Semikolon-separeret liste af aktiviteter
  - Øvrige metadata-kolonner fra tidligere trin

#### Metodologi

Dette trin anvender en to-lags risikovurdering: en konservativ generel vurdering (5a) efterfulgt af en stofspecifik vurdering med losseplads-override logik (5b). Trinnet identificerer højrisiko-lokaliteter der kræver nærmere undersøgelse eller indsats.

##### Præ-processing: Datakvalificering

Før risikovurdering separeres kombinationer i to grupper:

**Gruppe 1 - Kvalificerende kombinationer:**
Kombinationer med ENTEN:
- Ikke-tom `Lokalitetensstoffer` (dokumenterede forureningsstoffer)
- ELLER losseplads-keywords i `Lokalitetensbranche` eller `Lokalitetensaktivitet`
  (keywords: "losseplads", "affald", "deponi", "fyld", "skraldeplads")

**Gruppe 2 - Parkerede kombinationer:**
Kombinationer UDEN:
- Stofdata OG uden losseplads-keywords i branche/aktivitet

Parkerede kombinationer gemmes i `step5_unknown_substance_sites.csv` til manuel opfølgning, men indgår ikke i risikovurderingen.

---

#### TRIN 5A: GENEREL RISIKOVURDERING

##### Formål

Konservativ screening med universel afstandstærskel uafhængig af forureningstype.

##### Logik

Filtrering baseret på fast tærskel:

```python
high_risk = df[df['Distance_to_River_m'] <= 500]
```

**Tærskel:** 500 meter (konfigurerbar via `WORKFLOW_SETTINGS['risk_threshold_m']`)

Denne tærskel repræsenterer et konservativt worst-case scenarie hvor alle forureningstyper antages at kunne sprede sig op til 500 meter.

##### Output

**Fil 1:** `step5_high_risk_sites_500m.csv`
- **Rækker:** [antal] lokalitet-GVFK kombinationer inden for 500m
- **Kolonner:** Alle kolonner fra input bevares
- **Formål:** Bred screening til identifikation af potentielt problematiske lokaliteter

**Fil 2:** `step5_gvfk_high_risk_500m.shp`
- **Features:** [antal] GVFK-polygoner
- **Indhold:** Grundvandsforekomster med mindst én lokalitet inden for 500m
- **Formål:** Geografisk visualisering af berørte GVFK'er

---

#### TRIN 5B: STOFSPECIFIK RISIKOVURDERING

##### Formål

Litteraturbaseret vurdering med variable afstandstærskler baseret på stofmobilitet og losseplads-karakteristika.

##### Fase 1: Kategorisering og Initial Screening

**Stofkategorisering:**

For hver lokalitet-GVFK kombination med stofdata parses `Lokalitetensstoffer` (semikolon-separeret liste) og hvert enkelt stof kategoriseres:

```python
substances = stoffer.split(';')
for substance in substances:
    category, threshold_m = categorize_substance(substance)
```

**11 Litteraturbaserede Kategorier:**

Baseret på "Jordforureningens påvirkning af overfladevand, delprojekt 2" (Miljøprojekt 1565, 2014).

*Komplet kategorisering og keyword mapping findes i `compound_categories.py` (se Appendix H i hovedrapporten)*:

| Kategori | Tærskel | Repræsentative stoffer |
|----------|---------|------------------------|
| **PAH_FORBINDELSER** | 30m | Benzo[a]pyren, naftalen, fluoranthen |
| **BTXER** | 50m | Benzen*, toluen, xylen, olieprodukter |
| **PHENOLER** | 100m | Phenol, klorofenol |
| **ANDRE_AROMATISKE** | 150m | Chlorbenzen, dichlorbenzen |
| **UORGANISKE_FORBINDELSER** | 150m | Arsen, bly, cadmium, nitrat |
| **KLOREREDE_PHENOLER** | 200m | Dichlorophenol, klorofenol |
| **POLARE_FORBINDELSER** | 300m | MTBE, acetone, phthalater |
| **KLOREDE_KULBRINTER** | 500m | TCE, PCE, chloroform |
| **PESTICIDER** | 500m | MCPP, atrazin, glyphosat |
| **PFAS** | 500m | PFOS, PFOA, PFHxS |
| **LOSSEPLADS** | 100m | Perkolat, methan, deponigas |
| **ANDRE** | 500m | Ukendte eller ukategoriserede stoffer |

\* Benzen har stofspecifik override til 200m (selvom det tilhører BTXER-kategorien med 50m)

**Keyword Matching:**

Kategorisering sker via normaliseret keyword matching (case-insensitive, accent-stripped):

```python
def categorize_substance(substance_text):
    normalized = normalize(substance_text)  # lowercase + remove accents
    for category, data in COMPOUND_CATEGORIES.items():
        for keyword in data['keywords']:
            if keyword in normalized:
                return category, data['distance_m']
    return "ANDRE", 500
```

**Losseplads-flagging:**

Under kategorisering identificeres lokaliteter med losseplads-karakteristika:

```python
landfill_keywords = ['losseplads', 'affald', 'depon', 'fyldplads', 'skraldeplads']
is_landfill = any(keyword in branch.lower() or keyword in activity.lower()
                  for keyword in landfill_keywords)
```

**Branche-baseret kategorisering:**

Lokaliteter UDEN stofdata men MED branche/aktivitet kategoriseres via branch/activity keywords:
- Hvis losseplads-keywords matches → `LOSSEPLADS` kategori (100m)
- Ellers → `ANDRE` kategori (500m default)

**Screening:**

For hvert stof/lokalitet-GVFK kombination evalueres:

```python
if is_landfill_site and category in LANDFILL_THRESHOLDS:
    effective_threshold = LANDFILL_THRESHOLDS[category]  # Phase 2 will apply
else:
    effective_threshold = category_threshold

if distance <= effective_threshold:
    # Kombination kvalificerer til videre analyse
    high_risk_combinations.append({
        'Lokalitet_ID': lokalitet_id,
        'GVFK': gvfk,
        'Distance_to_River_m': distance,
        'Qualifying_Substance': substance,
        'Qualifying_Category': category,
        'Category_Threshold_m': category_threshold,
        ...
    })
```

**Vigtigt:** For losseplads-sites anvendes midlertidigt `max(category_threshold, landfill_threshold)` i screening-fasen for ikke at frasortere kombinationer der kun kvalificerer ved lossepladstærsklen.

##### Fase 2: Losseplads-Override (Post-Processering)

Baseret på "Risikovurdering af lossepladsers påvirkning af overfladevand" (Bjerg et al., 2014, Tabel 7.1).

For kombinationer der passerede Fase 1 OG har losseplads-karakteristika, anvendes nu losseplads-specifikke tærskler:

**Losseplads-specifikke tærskler:**

| Kategori | Normal tærskel | Losseplads tærskel | Effekt |
|----------|----------------|--------------------|--------|
| **BTXER** | 50m | 70m | Lempligere (benzendampning) |
| **KLOREDE_KULBRINTER** | 500m | 100m | Strengere (nedbrydning) |
| **ANDRE_AROMATISKE** | 150m | 100m | Strengere |
| **PHENOLER** | 100m | 35m | Strengere (nedbrydning) |
| **PESTICIDER** | 500m | 180m | Strengere (nedbrydning) |
| **UORGANISKE_FORBINDELSER** | 150m | 50m | Strengere (reducerende forhold) |

**Override logik:**

```python
for row in qualified_combinations:
    if row['Qualifying_Category'] == 'LOSSEPLADS':
        continue  # Allerede losseplads-klassificeret

    if is_landfill_site and category in LANDFILL_THRESHOLDS:
        landfill_threshold = LANDFILL_THRESHOLDS[category]

        if distance <= landfill_threshold:
            # Reklassificér til LOSSEPLADS
            row['Original_Category'] = category
            row['Qualifying_Category'] = 'LOSSEPLADS'
            row['Losseplads_Subcategory'] = f"LOSSEPLADS_{category}"
            row['Category_Threshold_m'] = landfill_threshold
            row['Qualifying_Substance'] = f"Landfill Override: {category}"
            row['Landfill_Override_Applied'] = True
        else:
            # Diskvalificér - for langt væk for losseplads-tærskel
            mark_for_removal(row)
```

**Eksempel:**

- Lokalitet med Phenol (100m tærskel) + losseplads-flag ved 80m afstand:
  - Fase 1: Passerer med effective_threshold = max(100m, 35m) = 100m
  - Fase 2: 80m > 35m losseplads-tærskel → **FJERNES**

- Lokalitet med BTXER (50m) + losseplads-flag ved 60m afstand:
  - Fase 1: Passerer med effective_threshold = max(50m, 70m) = 70m
  - Fase 2: 60m ≤ 70m losseplads-tærskel → **BEVARES**, reklassificeres til LOSSEPLADS_BTXER

##### Output

**Fil:** `step5b_compound_detailed_combinations.csv`
- **Rækker:** [antal] site-GVFK-substance kombinationer
- **Kolonner:**
  - Alle basis-kolonner fra Trin 4
  - `Qualifying_Substance` (string): Det stof der gjorde at kombinationen kvalificerede
  - `Qualifying_Category` (string): Stofkategori (eller "LOSSEPLADS" hvis reklassificeret)
  - `Category_Threshold_m` (float): Anvendt tærskel
  - `Losseplads_Subcategory` (string): Original kategori hvis losseplads-override anvendt
  - `Original_Category` (string): Kategori før override
  - `Landfill_Override_Applied` (boolean): Om losseplads-override blev anvendt
  - `Within_Threshold` (boolean): Om afstand er inden for tærskel

**Vigtigt:** Denne fil har FLERE rækker end unikke lokalitet-GVFK par fordi:
- Én lokalitet kan have flere stoffer → flere rækker per GVFK
- Én lokalitet kan være i flere GVFK → kombinationer ganges yderligere

**Fil:** `step5b_compound_gvfk_high_risk.shp`
- **Features:** [antal] GVFK-polygoner
- **Indhold:** Grundvandsforekomster med mindst én stofspecifik højrisiko-lokalitet
- **Formål:** Geografisk visualisering

---

#### Samlet Output fra Trin 5

**Risikokategorier:**

1. **Generel risiko (5a):** Lokaliteter inden for 500m uanset stoftype
2. **Stofspecifik risiko (5b):** Lokaliteter inden for stofspecifikke tærskler (30-500m)
3. **Parkerede:** Lokaliteter uden stof- eller branchedata (manuel opfølgning)

**Dataflow til Trin 6:**
De stofspecifikke højrisiko-lokaliteter fra 5b sendes videre til Trin 6 tilstandsvurdering for kvantitativ flux- og koncentrationsberegning.

---

### TRIN 6: TILSTANDSVURDERING

#### Input

**Fra Trin 5b:** `step5b_compound_detailed_combinations.csv`
- **Rækker:** [antal] site-GVFK-substance kombinationer
- **Nøglekolonner:**
  - `Lokalitet_ID`, `GVFK`, `Qualifying_Category`, `Qualifying_Substance`
  - `Distance_to_River_m`, `Nearest_River_FID`, `Nearest_River_ov_id`

**Fra Trin 3:** Lokalitetsgeometrier med arealer og centroids

**GVFK Layer Mapping:** DK-modellag tilknytning
- `GVForekom` (string): GVFK-navn
- `dkmlag` (string): DK-modellag identifikator (enkeltværdi, f.eks. "kvs_0200")
- `dknr` (string): Model region ("dk16", "dk7", eller "dk89")

**Vandløbsdata:** `Rivers_gvf_rev20230825_kontakt.shp`
- Samme som tidligere trin + segmentlængde

**Flow Scenarios:** Q-point data med vandføring
- `ov_id`, `Q05`, `Q10`, `Q50`, `Q90`, `Q95` (flow i m³/s), `geometry` (point)

**GVD Raster Data:** Grundvandsdynamik infiltrationsraster
- **Placering:** `Data/Ny_data_Lars_11_26_2025/dkmtif/`
- **Navnekonvention:** `{dk16|dk7}_gvd_{lag}.tif`
  - Eksempel: `dk16_gvd_kvs_0200.tif`, `dk7_gvd_lag1.tif`
- **Værdier:** Infiltrationshastighed i mm/år
- **CRS:** EPSG:25832
- **Coverage:** ~99.7% af GVFK har matchende raster

#### Metodologi

Dette trin kvantificerer den faktiske forureningspåvirkning af vandløb gennem beregning af forureningsflux fra lokaliteter, transport til vandløb, og fortynding i vandløbet (blandingskoncentration Cmix). Resultaterne sammenlignes med miljøkvalitetskrav (MKK) for at identificere hvor påvirkningen overstiger acceptable niveauer.

**Overordnet workflow:**
1. Infiltrationsberegning fra GVD-raster
2. Koncentrationsopslag (hierarkisk)
3. Fluxberegning per site-scenario
4. Aggregering per vandløbssegment
5. Cmix-beregning for multiple flow-scenarier
6. MKK-sammenligning og exceedance-flagging

##### 1. Infiltrationsberegning

For hver lokalitet-GVFK kombination samples grundvandsinfiltration fra GVD-raster.

**Raster Filnavnskonstruktion:**

Mapping fra Grunddata til raster-fil:

```python
# Input fra Grunddata: dkmlag="kvs_0200", dknr="dk16"
# Output: "dk16_gvd_kvs_0200.tif"

filename = f"{dknr}_gvd_{dkmlag}.tif"
```

Fallback til dk16 hvis dk7/dk89-fil ikke findes. I praksis har alle GVFK enkeltværdi i `dkmlag` (0% har multiple lag i nuværende data).

**To-trins Sampling Strategi:**

**Trin 1 - Polygon Sampling (foretrukket):**

```python
with rasterio.open(raster_file) as src:
    masked_data, _ = rasterio.mask.mask(src, [geometry], crop=True, all_touched=False)
    valid_pixels = masked_data[(masked_data != nodata) & (~np.isnan(masked_data))]
```

Udtrækker ALLE pixels inden for lokalitetens polygon og beregner mean, min, max, pixel count.

**Valg af `all_touched=False`:**

Parameteren `all_touched=False` betyder at kun pixels hvis **centrum** falder inden for polygonen inkluderes. Komparativ analyse (`compare_infiltration_methods.py`) viste:

- **Pixel counts:** Median 1 pixel (vs 2 med `all_touched=True`), mean 1.63 (vs 3.94)
- **Små sites:** 96.9% af sites har ≤5 pixels (trigger ofte centroid fallback)
- **Kritisk forskel:** `all_touched=False` bevarer ~833 flere sites i analysen
  - Med `all_touched=True`: 1,391 sites skifter fra downward→upward (fjernes)
  - Med `all_touched=False`: 558 sites skifter fra upward→downward (bevares)

**Rationale:** Selvom `all_touched=False` giver færre pixels per site, undgår det at filtrere sites baseret på edge-pixels med negativ infiltration. Dette er en mere inklusiv tilgang hvor små lokaliteter får en ren centroid-baseret vurdering i stedet for at blive fjernet på grund af tilfældige negative randpixels.

**GVD Value Cleaning:**

Rå raster-værdier renses:

```python
gvd_cap = 750  # mm/år [REF: GVD_cap_rationale]

# Zero negative values (upward flux → discharge zones)
cleaned = np.where(valid_pixels < 0, 0, valid_pixels)

# Cap extreme positive values (raster artifacts)
cleaned = np.where(cleaned > gvd_cap, gvd_cap, cleaned)
```

**Trin 2 - Centroid Sampling (fallback):**

Hvis polygon sampling returnerer 0 pixels, samples ved lokalitetens centroid:

```python
coords = [(centroid.x, centroid.y)]
centroid_value = src.sample(coords)[0][0]
```

Anvendes for meget små lokaliteter eller ved raster-grænser.

**Output kolonner:**
- `Infiltration_mm_per_year`: Combined værdi (polygon mean hvis tilgængelig, ellers centroid)
- `Polygon_Infiltration_mm_per_year`: Mean fra polygon-pixels
- `Polygon_Infiltration_Min_mm_per_year`: Min fra polygon-pixels
- `Polygon_Infiltration_Max_mm_per_year`: Max fra polygon-pixels
- `Polygon_Infiltration_Pixel_Count`: Antal pixels sampled
- `Centroid_Infiltration_mm_per_year`: Værdi fra centroid

**Filtrering:**

Kombinationer filtreres hvis:
- GVFK mangler DK-modellag mapping (Filter 1)
- Infiltration < 0 mm/år efter cleaning (Filter 2 - discharge zones)
- Infiltration = NaN (Filter 3 - udenfor raster coverage)

Alle filtrerede kombinationer logges i `step6_filtering_audit.csv`.

##### 2. Koncentrationsopslag

For hver site-kategori-scenario kombination slås standardkoncentration op via hierarkisk system.

**Scenario-baseret Tilgang:**

Kategorier med modelstoffer genererer scenarier baseret på de **16 prioriterede modelstoffer fra Delprojekt 3**:

| Modelstof | Kategori | Koncentration (µg/L) |
|-----------|----------|---------------------|
| Benzen | BTXER | 400 |
| Olie C10-C25 | BTXER | 3000 |
| 1,1,1-Trichlorethan | KLOREDE_KULBRINTER | 100 |
| Trichlorethylen | KLOREDE_KULBRINTER | 42000 |
| Chloroform | KLOREDE_KULBRINTER | 100 |
| Chlorbenzen | ANDRE_AROMATISKE_FORBINDELSER | 100 |
| MTBE | POLARE_FORBINDELSER | 50000 |
| 4-Nonylphenol | POLARE_FORBINDELSER | 9 |
| Phenol | PHENOLER | 1300 |
| 2,6-dichlorphenol | KLOREREDE_PHENOLER | 10000 |
| Mechlorprop | PESTICIDER | 1000 |
| Atrazin | PESTICIDER | 12 |
| Fluoranthen | PAH_FORBINDELSER | 30 |
| Arsen | UORGANISKE_FORBINDELSER | 100 |
| Cyanid | UORGANISKE_FORBINDELSER | 3500 |
| COD | (Losseplads kontekst) | 380000 |

**Kategorier uden modelstoffer (ekskluderes fra Step 6):**
- LOSSEPLADS: Ingen validerede modelstoffer - bruger kontekst-specifikke opslag
- ANDRE: Ukategoriserede stoffer - ingen valideret koncentration
- PFAS: Ikke fra Delprojekt 3 - kræver fremtidig validering

[REF: Standard_concentrations] - Kilde: Delprojekt 3 tabeller

**Eksempel - BTXER kategori:**
- Modelstoffer: ["Benzen", "Olie C10-C25"]
- Et site med 4 forskellige BTXER-forbindelser (Benzen, Toluen, Ethylbenzen, Xylen) genererer 2 flux-scenarier:
  - `BTXER__via_Benzen` (konc: 400 µg/L)
  - `BTXER__via_Olie C10-C25` (konc: 3000 µg/L)

**Vigtigt:** Alle forbindelser i en kategori bruger modelstof-koncentrationerne, IKKE deres eget stofnavn. F.eks. "Ethylbenzen" (ikke et modelstof) vil bruge enten Benzen eller Olie C10-C25 scenarierne.

**Hierarkisk Koncentrationsopslag:**

For hvert scenario søges koncentration i følgende rækkefølge:

**Niveau 1: Aktivitet + Modelstof**
- Aktivitetsspecifikke koncentrationer (højeste prioritet)
- Eksempel: Tankstationer har højere benzen-koncentrationer end generiske sites

**Niveau 2: Losseplads Kontekst**
- Hvis `Qualifying_Category == "LOSSEPLADS"`, brug losseplads-specifikke koncentrationer
- Prøv først specifikt modelstof, ellers kategori

**Niveau 3: Direkte Modelstof**
- Bruges for de 16 prioriterede modelstoffer
- Modelstof-specifikke koncentrationer (f.eks. Benzen = 400 µg/L)

**Niveau 4: Kategori-Scenario**
- Kategori med specifikt modelstof-scenario
- Eksempel: `BTXER__via_Benzen` = 400 µg/L

**Niveau 5: Kategori Fallback**
- For kategorier uden scenarier (LOSSEPLADS, ANDRE, PFAS)
- Direkte kategori-koncentration

**Gennemgang Eksempel:**

Lokalitet med følgende attributter:
- **Branche:** "Servicestationer"
- **Kategori:** BTXER
- **Modelstof-scenario:** Benzen

**Hierarki-søgning:**
1. **Niveau 1:** Søg "Servicestationer_Benzen" → **MATCH** ✓
   - Returnerer: 2000 µg/L (tankstation-specifik koncentration)
   - **STOP** - ingen videre søgning

**Alternativt eksempel** (hvis IKKE servicestation):

Lokalitet med:
- **Branche:** Tom/anden aktivitet
- **Kategori:** BTXER
- **Modelstof-scenario:** Benzen

**Hierarki-søgning:**
1. **Niveau 1:** Søg "anden_aktivitet_Benzen" → Ikke fundet
2. **Niveau 2:** Er det losseplads? Nej → Skip
3. **Niveau 3:** Søg "Benzen" i modelstoffer → **MATCH** ✓
   - Returnerer: 400 µg/L (generisk benzen-koncentration)
   - **STOP**

**Tredje eksempel** (kategori uden modelstof-data):

Lokalitet med:
- **Kategori:** PFAS
- **Modelstof-scenario:** Ingen (PFAS har ikke scenarier)

**Hierarki-søgning:**
1. **Niveau 1:** Ingen aktivitet → Skip
2. **Niveau 2:** Ikke losseplads → Skip
3. **Niveau 3:** Intet modelstof → Skip
4. **Niveau 4:** Ingen scenarier for PFAS → Skip
5. **Niveau 5:** Søg "PFAS" i kategorier → **MATCH** ✓
   - Returnerer: 500 µg/L (kategori-niveau koncentration)
   - **STOP**

**Fjerde eksempel** (detekteret stof er IKKE et modelstof):

Lokalitet med:
- **Detekteret stof:** "Ethylbenzen" (tilhører BTXER, men er IKKE et modelstof)
- **Kategori:** BTXER
- **Modelstof-scenario:** Benzen (kategori-scenarie)

**Hierarki-søgning:**
1. **Niveau 1:** Ingen aktivitet → Skip
2. **Niveau 2:** Ikke losseplads → Skip
3. **Niveau 3:** Søg "Ethylbenzen" i modelstoffer → Ikke fundet (ikke et af de 16)
4. **Niveau 4:** Søg "BTXER__via_Benzen" → **MATCH** ✓
   - Returnerer: 400 µg/L (kategori-scenario koncentration)
   - **STOP**

**Vigtigt:** Selv om det detekterede stof er "Ethylbenzen", bruges Benzen-koncentrationen fordi Ethylbenzen ikke er et prioriteret modelstof. Alle ikke-modelstof forbindelser i BTXER bruger enten Benzen eller Olie C10-C25 scenarier.

Hvis INGEN match findes på noget niveau, raises ValueError med detaljer om missing koncentration.

##### 3. Fluxberegning

**Formål:** Beregn hvor meget forurening der transporteres fra hver lokalitet til vandløb per år.

**Grundlæggende Formel:**

```
Flux (µg/år) = Areal (m²) × Infiltration (m/år) × Koncentration (µg/m³)
```

**Konkret Eksempel:**

En lokalitet med følgende parametre:
- **Areal:** 5,000 m²
- **Infiltration:** 200 mm/år = 0.2 m/år
- **Koncentration:** Benzen = 400 µg/L = 400,000 µg/m³

**Beregning:**
1. Vandvolumen per år: 5,000 m² × 0.2 m/år = **1,000 m³/år**
2. Flux: 1,000 m³/år × 400,000 µg/m³ = **400,000,000 µg/år** = **0.4 kg/år**

**Håndtering af Multi-GVFK Sites:**

En kritisk detalje er at samme lokalitet kan bidrage til flere vandløbssegmenter. Overvej følgende scenario:

**Scenario:** Lokalitet "Site_A" overlapper to GVFK'er:

| Lokalitet | GVFK | Nærmeste Vandløb | Afstand |
|-----------|------|------------------|---------|
| Site_A | GVFK_Nord | Å_Segment_100 (ov_id: "Å1") | 150m |
| Site_A | GVFK_Syd | Å_Segment_101 (ov_id: "Å1") | 80m |

Dette er **samme flod** ("Å1") men **to forskellige fysiske segmenter** (FID 100 og 101). Lokaliteten påvirker begge segmenter, så der skal beregnes **to separate flux-værdier**.

**Gruppering for at undgå dobbelt-tælling:**

Koden grupperer på: `(Lokalitet_ID, GVFK, Nearest_River_FID, Qualifying_Category)`

Dette sikrer at:
- Site_A → GVFK_Nord → Segment_100: Én flux-værdi
- Site_A → GVFK_Syd → Segment_101: Én anden flux-værdi
- Ingen dobbelt-tælling sker

**Scenario-generering:**

For kategorier med flere modelstoffer (f.eks. BTXER), genereres flere scenarier:

**Eksempel:** Site_A har BTXER-forurening → genererer 2 flux-rækker:
1. Site_A → Segment_100 → BTXER__via_Benzen (400 µg/L)
2. Site_A → Segment_100 → BTXER__via_Olie_C10-C25 (3000 µg/L)

Hvert scenario repræsenterer et "hvad hvis"-tilfælde for den værst tænkelige koncentration i den kategori.

##### 4. Segmentaggregering

**Formål:** Summér flux fra alle lokaliteter der påvirker samme vandløbssegment.

**Scenario:** Tre lokaliteter bidrager til samme vandløbssegment:

| Lokalitet | Segment | Substance | Flux (kg/år) | Afstand (m) |
|-----------|---------|-----------|--------------|-------------|
| Site_A | Segment_100 | BTXER__via_Benzen | 0.4 | 150 |
| Site_B | Segment_100 | BTXER__via_Benzen | 0.8 | 220 |
| Site_C | Segment_100 | KLOREDE__via_PCE | 0.15 | 80 |

**Aggregering per segment-substance:**

Efter aggregering fås to rækker (én per unik substans):

**Række 1: Segment_100 + BTXER__via_Benzen**
- Total Flux: 0.4 + 0.8 = **1.2 kg/år**
- Bidragende sites: 2 (Site_A, Site_B)
- Afstandsinterval: 150m - 220m

**Række 2: Segment_100 + KLOREDE__via_PCE**
- Total Flux: **0.15 kg/år**
- Bidragende sites: 1 (Site_C)
- Afstandsinterval: 80m - 80m

**Vigtigt:** Aggregering sker per substans fordi forskellige stoffer har forskellige MKK-tærskler. En flod kan have acceptable niveauer af Benzen men samtidig overstige tærsklen for PCE.

**Output kolonner:**
- `Total_Flux_ug_per_year`: Sum af flux fra alle sites
- `Contributing_Site_Count`: Antal unikke lokaliteter
- `Contributing_Site_IDs`: "Site_A, Site_B, Site_C"
- `Min_Distance_to_River_m`: Korteste afstand
- `Max_Distance_to_River_m`: Længste afstand

##### 5. Cmix Beregning (Blandingskoncentration)

**Formål:** Beregn den faktiske koncentration i vandløbet efter fortynding.

**Koncept:** Forurening fra grundvandet fortyndes i vandløbets flow. Jo højere flow, jo større fortynding.

**Formel:**
```
Cmix (µg/L) = Flux (µg/s) / [Flow (m³/s) × 1000]
```

**Konkret Eksempel:**

Fra tidligere har vi:
- **Segment_100 → BTXER__via_Benzen:** Total flux = 1.2 kg/år

Dette konverteres til µg/s:
- 1.2 kg/år = 1,200,000,000 µg/år
- 1,200,000,000 µg/år ÷ 31,536,000 s/år = **38.05 µg/s**

Nu slås vandføring op for dette segment. Vandføring varierer med årstid og vejr, så der bruges flere scenarier:

| Flow Scenario | Beskrivelse | Flow (m³/s) | Cmix (µg/L) |
|---------------|-------------|-------------|-------------|
| Q05 | Høj flow (vinter) | 5.0 | 38.05 / (5.0 × 1000) = **0.0076** |
| Q50 | Median flow | 1.5 | 38.05 / (1.5 × 1000) = **0.0254** |
| Q90 | Lav flow (sommer) | 0.3 | 38.05 / (0.3 × 1000) = **0.127** |
| Q95 | Meget lav flow (tørke) | 0.1 | 38.05 / (0.1 × 1000) = **0.381** |

**Observation:** Under lav-flow forhold (Q90, Q95) stiger koncentrationen markant.

**Flow Data Matching:**

Vandføring måles i Q-punkter langs floden, men et vandløbssegment kan være langt fra et Q-punkt. Tre metoder til at matche flow til segmenter:

**Metode 1: max_per_ov_id (default)**
- Brug det højeste flow målt nogen steder på floden (konservativ)
- Eksempel: Flod "Å1" har 5 Q-punkter med Q90 flow: [0.5, 0.3, 0.8, 0.4, 0.6] → brug 0.8 m³/s

**Metode 2: max_near_segment**
- Find Q-punkter inden for 100m af segmentet
- Brug det højeste flow blandt de nære punkter
- Mere repræsentativt for lokale forhold

**Metode 3: downstream_per_segment**
- Find Q-punktet nærmest segmentets nedstrøms-ende
- Mest præcis, men kræver at Q-punkter er jævnt fordelt

**Output:**

For hvert segment genereres 5 Cmix-værdier (én per flow-scenario). Eksempel:

| Segment | Substance | Flow_Scenario | Flow (m³/s) | Cmix (µg/L) |
|---------|-----------|---------------|-------------|-------------|
| Seg_100 | BTXER__via_Benzen | Q05 | 5.0 | 0.0076 |
| Seg_100 | BTXER__via_Benzen | Q50 | 1.5 | 0.0254 |
| Seg_100 | BTXER__via_Benzen | Q90 | 0.3 | 0.127 |
| Seg_100 | BTXER__via_Benzen | Q95 | 0.1 | 0.381 |

**Primær Scenario for Beslutningsgrundlag:**

Selvom Cmix beregnes for alle fem scenarier, anvendes **Q95** (lavvandføring) som primær scenario for beslutningsgrundlag og rapportering. Dette er mest konservativt/beskyttende da:

- Q95 repræsenterer meget lav vandføring (95% af tiden er flowet højere)
- Lav flow → minimal fortynding → højeste Cmix
- Worst-case scenario for økosystembeskyttelse

**Matematisk sammenhæng:**

Eftersom Cmix = Flux / Flow, gælder:
- Hvis et segment overskrider MKK ved Q95 → det overskrider også ved lavere flows (Q90, Q50, Q05 kan have lavere Cmix)
- Hvis et segment IKKE overskrider ved Q95 → det overskrider heller ikke ved højere flows

**Derfor:** Q95-scenarier definerer det endelige sæt af problematiske segmenter. Segmenter rapporteret som "MKK-overskridelse" er baseret på Q95-vurdering.

```python
cmix_row = {
    'Nearest_River_FID': fid,
    'Nearest_River_ov_id': ov_id,
    'Qualifying_Substance': substance,
    'Flow_Scenario': 'Q90',
    'Flow_m3_s': 2.5,
    'Total_Flux_ug_per_year': 1_500_000_000,  # Fra aggregering
    'Flux_ug_per_second': 47.55,
    'Cmix_ug_L': 0.019,
    ...
}
```

##### 6. MKK-sammenligning og Exceedance Flagging

**Formål:** Identificer hvor vandløbskvaliteten overskrider miljøkvalitetskrav (MKK).

**MKK Opslag:**

Miljøkvalitetskrav er lovfæstede grænseværdier for koncentrationer i overfladevand [REF: MKK_thresholds]. Opslag følger hierarki:

1. **Modelstoffer** (de 16 prioriterede): Brug stof-specifik MKK
   - Eksempel: "BTXER__via_Benzen" → ekstrahér "Benzen" → MKK = 1.0 µg/L
2. **Alle andre**: Brug kategori-MKK
   - Eksempel: "BTXER__via_Olie_C10-C25" → "Olie" er ikke modelstof → brug BTXER kategori-MKK

**Konkret Eksempel:**

Fra tidligere Cmix-beregning har vi:

| Segment | Substance | Flow_Scenario | Cmix (µg/L) | MKK (µg/L) |
|---------|-----------|---------------|-------------|------------|
| Seg_100 | BTXER__via_Benzen | Q05 | 0.0076 | 1.0 |
| Seg_100 | BTXER__via_Benzen | Q50 | 0.0254 | 1.0 |
| Seg_100 | BTXER__via_Benzen | Q90 | 0.127 | 1.0 |
| Seg_100 | BTXER__via_Benzen | Q95 | 0.381 | 1.0 |

**Exceedance Flagging:**

```
Exceedance_Flag = (Cmix > MKK)
Exceedance_Ratio = Cmix / MKK
```

Resultater:

| Flow_Scenario | Cmix | MKK | Flag | Ratio | Fortolkning |
|---------------|------|-----|------|-------|-------------|
| Q05 | 0.0076 | 1.0 | False | 0.008 | 0.8% af MKK ✓ |
| Q50 | 0.0254 | 1.0 | False | 0.025 | 2.5% af MKK ✓ |
| Q90 | 0.127 | 1.0 | False | 0.127 | 12.7% af MKK ✓ |
| Q95 | 0.381 | 1.0 | False | 0.381 | 38.1% af MKK ✓ |

**Konklusion:** Ingen overskridelser - selv under lav-flow (Q95) er koncentrationen under MKK.

**Alternativ Scenario - Overskridelse:**

Hvis et andet segment havde højere flux:

| Flow_Scenario | Cmix | MKK | Flag | Ratio | Fortolkning |
|---------------|------|-----|------|-------|-------------|
| Q05 | 0.8 | 1.0 | False | 0.8 | Under MKK ✓ |
| Q90 | 2.3 | 1.0 | **True** | 2.3 | **2.3× over MKK** ❌ |
| Q95 | 4.1 | 1.0 | **True** | 4.1 | **4.1× over MKK** ❌ |

**Konklusion:** Overskridelser under lav-flow scenarier (Q90, Q95). Failing scenarios: "Q90, Q95".

**Beslutningsgrundlag:**

For endelig rapportering og beslutningstagning anvendes **Q95-scenariet** som primær indikator:
- Segmenter hvor Q95 overskrider MKK rapporteres som "MKK-overskridelse"
- Q95 repræsenterer worst-case lavvandsforhold
- Dette sikrer beskyttelse af økosystemer også under tørkeperioder

Teknisk bemærkning: Koden evaluerer alle scenarier og gemmer "Failing_Scenarios" (f.eks. "Q90, Q95"), men det **endelige antal segmenter med MKK-overskridelse** er baseret på Q95-vurdering.

**Segment Summary:**

For hvert vandløbssegment aggregeres:
- **Max Cmix:** Højeste koncentration på tværs af alle flow-scenarier og substanser
- **Max Exceedance Ratio:** Værste overskridelse
- **Failing Scenarios:** Liste af scenarier med overskridelser
- **Has_MKK_Exceedance:** Boolean - om nogen scenario overskrider

**Exceedance Views:**

To fokuserede tabeller genereres for manuel review:

**1. Site Exceedances:** Hvilke lokaliteter bidrager til overskridelser?
- Filter til kun segmenter med `Exceedance_Flag == True`
- Viser hver lokalitets bidrag til problemet

**2. GVFK Exceedances:** Hvilke grundvandsforekomster påvirker problematiske segmenter?
- Aggreger per GVFK
- Viser total flux fra hver GVFK til berørte segmenter

#### Output

**Fil 1:** `step6_flux_site_segment.csv`
- **Rækker:** [antal] site-scenario kombinationer
- **Kolonner:**
  - Site identifikation: `Lokalitet_ID`, `GVFK`, `Lokalitetsnavn`
  - Flux parametre: `Area_m2`, `Infiltration_mm_per_year`, `Standard_Concentration_ug_L`
  - Flux output: `Pollution_Flux_ug_per_year`, `Pollution_Flux_kg_per_year`
  - Vandløb: `Nearest_River_FID`, `Nearest_River_ov_id`, `River_Segment_Name`
  - Substans: `Qualifying_Category`, `Qualifying_Substance`
- **Formål:** Detaljeret site-level flux for alle scenarier

**Fil 2:** `step6_cmix_results.csv`
- **Rækker:** [antal] segment-substance-scenario kombinationer
- **Kolonner:**
  - Segment: `Nearest_River_FID`, `Nearest_River_ov_id`, `River_Segment_Name`
  - Substans: `Qualifying_Category`, `Qualifying_Substance`
  - Flow: `Flow_Scenario` (Q05/Q10/Q50/Q90/Q95), `Flow_m3_s`
  - Flux: `Total_Flux_ug_per_year`, `Flux_ug_per_second`
  - Koncentration: `Cmix_ug_L`
  - MKK: `MKK_ug_L`, `Exceedance_Flag`, `Exceedance_Ratio`
  - Sites: `Contributing_Site_Count`, `Contributing_Site_IDs`
- **Formål:** Komplet Cmix beregning for alle flow-scenarier

**Fil 3:** `step6_segment_summary.csv`
- **Rækker:** [antal] unikke vandløbssegmenter
- **Kolonner:**
  - Segment: `Nearest_River_FID`, `Nearest_River_ov_id`, `River_Segment_Name`
  - GVFK: `River_Segment_GVFK`
  - Flux: `Total_Flux_kg_per_year` (sum på tværs af alle substanser)
  - Cmix: `Max_Cmix_ug_L` (højeste på tværs af scenarier og substanser)
  - Exceedance: `Max_Exceedance_Ratio`, `Has_MKK_Exceedance`, `Failing_Scenarios`
  - Sites: `Site_Count`, `Site_IDs`
  - Metadata: `Flow_Scenarios`, `Categories`
- **Formål:** Segment-level overview for prioritering

**Fil 4:** `step6_site_mkk_exceedances.csv`
- **Rækker:** [antal] site-kombinationer på segmenter med MKK-overskridelser
- **Kolonner:** Subset af cmix_results filtreret til `Exceedance_Flag == True`
- **Formål:** Fokuseret liste til manuel review af problematiske sites

**Fil 5:** `step6_filtering_audit.csv`
- **Rækker:** [antal] filtrerede kombinationer
- **Kolonner:**
  - Site info: `Lokalitet_ID`, `Lokalitetsnavn`, `GVFK`
  - Filter info: `Filter_Stage`, `Filter_Reason`, `Additional_Info`
  - Metadata: `Qualifying_Category`, `Nearest_River_ov_id`, `Distance_to_River_m`
- **Formål:** Komplet audit trail for alle filtrerede sites

**Visualiseringer:**

Automatisk genererede plots (via `step6_visualizations.py`):
- Flux distribution per kategori
- Cmix vs MKK scatter plots
- Flow scenario comparison
- Infiltration distribution histograms
- Exceedance heatmaps per GVFK

**Sammenhæng med Hovedrapport:**

Trin 6 output danner grundlag for:
- Prioritering af indsatsområder
- Kvantitativ risikovurdering
- Compliance-rapportering ift. vandrammedirektivet
- Grundlag for afbødende tiltag (remediation prioritization)

---
