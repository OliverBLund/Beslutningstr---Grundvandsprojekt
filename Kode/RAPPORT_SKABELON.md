# Risiko- og Tilstandsvurdering

## Risikovurdering (Trin 1-5)

### Formål
Risikovurderingen identificerer forurenede lokaliteter (V1/V2), der udgør en potentiel risiko for grundvandsforekomster (GVF) med kontakt til målsatte vandløb. Metodikken anvender afstandsbaserede tærskler differentieret efter forureningskategori.

### Input Data

#### Primære datasæt

| Datasæt | Kilde | Dato | Beskrivelse |
|---------|-------|------|-------------|
| **Grundvandsforekomster (GVF)** | Grunddata_results.gdb, lag: `dkm_gvf_vp3genbesog_kontakt` | [DATO] | GVFK-polygoner. **Kilde:** [KILDE - ex. GEUS/Miljøstyrelsen] |
| **Vandløbssegmenter** | Grunddata_results.gdb, lag: `Rivers_gvf_vp3genbesog_kontakt` | [DATO] | Vandløb med GVF-kontakt. **Kilde:** [KILDE] |
| **V1-lokaliteter (CSV)** | v1_gvfk_forurening_NEW.csv | [DATO] | Kortlagte forurenede grunde (V1). **Kilde:** [KILDE - ex. DKjord] |
| **V2-lokaliteter (CSV)** | v2_gvfk_forurening_NEW.csv | [DATO] | Kortlagte forurenede grunde (V2). **Kilde:** [KILDE - ex. DKjord] |
| **V1-geometrier** | V1FLADER.shp | [DATO] | Polygongeometrier for V1-lokaliteter. **Kilde:** [KILDE] |
| **V2-geometrier** | V2FLADER.shp | [DATO] | Polygongeometrier for V2-lokaliteter. **Kilde:** [KILDE] |
| **GVD-rasters** | dkmtif/ mappe | [DATO] | Grundvandsdannelse (infiltration) i mm/år pr. DK-modellag. **Kilde:** [KILDE - ex. DK-model] |
| **Q-punkter** | Grunddata_results.gdb, lag: `dkm_qpoints_gvf_vp3genbesog_kontakt` | [DATO] | Vandføringsdata (Q50-Q95). **Kilde:** [KILDE] |
| **GVFK volumen/areal** | volumen areal_genbesøg.csv | [DATO] | Areal og volumen data. **Kilde:** [KILDE] |

#### Kolonne-mappings
Datasættene forbindes via standard kolonnenavne konfigureret i `config.py`:
- GVFK identificeres via `GVForekom`-kolonnen
- Lokaliteter identificeres via `Lokalitetsnr`
- Vandløbskontakt er implicit i datasættet (tilstedeværelse af GVFK-værdi = kontakt)

---

### Workflow

#### Trin 1 – Optælling af GVF
**Formål:** Etablering af baseline-optælling af alle grundvandsforekomster i Danmark.

**Metode:**
- Indlæsning af GVF-shapefile fra Grunddata geodatabase
- Optælling af unikke GVF baseret på `GVForekom`-kolonnen

**Resultat:** ~X.XXX unikke grundvandsforekomster i Danmark.

---

#### Trin 2 – GVF med vandløbskontakt
**Formål:** Identifikation af GVF'er med direkte kontakt til målsatte vandløb.

**Metode:**
- Filtrering af vandløbssegmenter med valid GVFK-værdi
- I det nye Grunddata-format indikerer tilstedeværelsen af GVFK-værdi kontakt (tidligere `Kontakt = 1`)
- Ekstraktion af unikke GVFK-navne fra vandløbsdatasættet
- Tilknytning af GVF-polygoner til filtreret liste

**Resultat:** ~X.XXX GVF'er med vandløbskontakt (~XX% af total).

---

#### Trin 3 – GVF med V1/V2 lokaliteter
**Formål:** Identifikation af forurenede lokaliteter i GVF'er med vandløbskontakt.

**Metode:**
1. Indlæsning af V1/V2 forureningsdata (CSV) med stof- og brancheinformation
2. **Data-kvalificering:** Lokaliteter kvalificerer sig hvis de har:
   - Stoffdata (`Lokalitetensstoffer` udfyldt), ELLER
   - Lossepladsnøgleord i branche/aktivitet (fx "losseplads", "affald", "deponi")
3. Filtrering til lokaliteter i GVF'er fra Trin 2
4. Sammenkobling med geometrier fra V1/V2 shapefiles
5. **Deduplikering:** Aggregering af stofdata ved dubletter (samme lokalitet i V1 og V2)

**Note om "multi-GVFK tilgang":**  
En lokalitet kan påvirke flere GVF'er (fx ved grænser). Derfor oprettes en kombination pr. lokalitet-GVFK par, hvilket bevarer alle relationer.

**Resultat:** ~X.XXX unikke lokaliteter i ~XXX GVF'er (~XX.XXX lokalitet-GVFK kombinationer).

---

#### Trin 3b – Infiltrationsfilter
**Formål:** Fjernelse af lokaliteter i opstrømningszoner (negativ grundvandsdannelse) FØR afstandsberegning.

**Baggrund:**  
Fluxformlen `J = A × C × I` forudsætter nedadrettet grundvandsstrømning (positiv infiltration). I opstrømningszoner (discharge areas) strømmer grundvand opad mod terræn, og forurening transporteres ikke til grundvandsmagasinet via infiltration. Disse lokaliteter er derfor ikke relevante for risikovurderingen.

**Data:**  
GVD-rasters (Grundvandsdannelse) fra DK-modellen, organiseret pr. DK-modellag. Hver GVFK er tilknyttet ét eller flere modellag via `dkmlag`-kolonnen.  
**Kilde:** [KILDE - ex. DK-model 2019, GEUS]

##### Metode: Pixel-baseret Majority Voting

**Trin 1: Sampling af infiltrationsværdier**

For hver lokalitet-GVFK kombination:
1. Identificér relevante GVD-raster(e) baseret på GVFK'ens DK-modellag
2. Sample alle pixels der overlapper med lokalitetens polygon-geometri
3. Fallback til centroid-sampling hvis polygon-sampling fejler (fx meget små polygoner)

```
Eksempel: Lokalitet dækker 15 grid-celler
→ Sample 15 pixel-værdier fra GVD-raster
→ Værdier: [-50, -30, 10, 25, 40, -15, 80, 120, -5, 35, 45, 60, -20, 90, 110]
```

**Trin 2: Binær klassificering af strømningsretning**

Hver pixel-værdi konverteres til binært flag:
- **Negativ værdi (< 0):** `0` = opadrettet strømning (opstrømning)
- **Positiv værdi (≥ 0):** `1` = nedadrettet strømning (infiltration)

```
Eksempel (15 pixels):
Værdier:     [-50, -30, 10, 25, 40, -15, 80, 120, -5, 35, 45, 60, -20, 90, 110]
Binært flag: [  0,   0,  1,  1,  1,   0,  1,   1,  0,  1,  1,  1,   0,  1,   1]
```

**Fordele ved binær tilgang:**
- Undgår at ekstreme negative værdier (fx -500 mm/år) dominerer gennemsnittet
- Fokuserer på *retning* af strømning, ikke *størrelse*
- Robust overfor outliers og data-artefakter

**Trin 3: Majority Voting**

Beregn andel af nedadrettede pixels:
```
Majority Vote = Σ(binære flags) / antal pixels
             = 11 / 15
             = 0.73 (73% nedadrettet)
```

**Beslutningsregel:**
- **Majority Vote > 0.5:** Lokaliteten har overvejende nedadrettet strømning → **BEHOLDES**
- **Majority Vote ≤ 0.5:** Lokaliteten har overvejende opadrettet strømning → **FJERNES**

**Trin 4: Håndtering af manglende data**

Lokaliteter uden rasterdata (no_data) **beholdes** som konservativ tilgang. Dette kan forekomme ved:
- Lokaliteter udenfor raster-dækning
- GVFK'er uden DK-modellag mapping

##### Resultat

Typiske værdier fra kørsler:

| Kategori | Kombinationer | Andel |
|----------|---------------|-------|
| Nedadrettet strømning (beholdt) | ~X.XXX | ~XX% |
| Opadrettet strømning (fjernet) | ~X.XXX | ~XX% |
| Ingen data (beholdt) | ~XXX | ~X% |

> **Note:** Infiltrationsfiltreringen sker i Trin 3b (FØR afstandsberegning), ikke i det tidligere Trin 5c. Dette sikrer at opstrømningslokaliteter ikke inkluderes i afstandsstatistik.

##### Sammenhæng med Trin 6: To-trins GVD-håndtering

Den samlede GVD-håndtering sker i to adskilte trin med forskellige formål:

| Trin | Formål | Metode | Output |
|------|--------|--------|--------|
| **Trin 3b** | Bestem strømningsretning | Binær klassificering + majority voting | Fjern/behold lokalitet |
| **Trin 6** | Beregn kvantitativ flux | Værdi-rensning + mean | Infiltrationsrate (mm/år) |

##### Fordele ved to-trins tilgangen

**1. Robusthed overfor ekstreme værdier**

GVD-rasters kan have meget heterogene værdier indenfor samme lokalitet. Det er observeret at en pixel kan have værdi -15.000 mm/år mens nabopixlen har +100 mm/år. 

Ved brug af *gennemsnit* ville den ekstreme negative værdi dominere:
```
Mean af [-15000, +100] = -7.450 mm/år → Klassificeres som opstrømning
```

Ved brug af *binær majority voting*:
```
Binært: [0, 1] → 50% nedadrettet → Grænsetilfælde (men ikke domineret af ekstrem værdi)
```

**2. Logisk sammenhæng mellem trin**

Når et site passerer Trin 3b, ved vi at >50% af pixels har nedadrettet strømning. I Trin 6 kan vi derfor:
- **Nulstille negative pixels:** De repræsenterer lokale opstrømningszoner indenfor en generelt nedadrettet lokalitet
- **Fokusere på nedadrettet flux:** Kun positive værdier bidrager til transport mod grundvandsmagasinet

Dette er metodisk konsistent: vi har allerede besluttet at lokaliteten har overvejende nedadrettet strømning.

**3. Separation af beslutning og beregning**

- **Trin 3b (beslutning):** Binær ja/nej - skal lokaliteten indgå i analysen?
- **Trin 6 (beregning):** Kvantitativ - hvor meget flux bidrager lokaliteten med?

##### Usikkerheder og begrænsninger

**1. Grænsetilfælde ved 50%-tærskel**

Lokaliteter med majority vote tæt på 0.5 (fx 51% nedadrettet) klassificeres som "nedadrettet", men har reelt blandet strømningsretning. Disse sites kan have:
- Betydelig lokal opstrømning
- Usikker faktisk transportretning
- Følsomhed overfor rasteropløsning

**2. Spatial heterogenitet**

Store lokaliteter kan dække områder med fundamentalt forskellige hydrogeologiske forhold. Den binære tilgang antager at én overordnet klassificering er meningsfuld for hele lokaliteten.

**3. Cap-værdi for infiltration**

Max-cap på 750 mm/år er en pragmatisk grænse baseret på [KILDE TIL CAP-VÆRDI]. Højere værdier kan:
- Repræsentere reelle forhold (fx områder med høj nedbør og permeabel geologi)
- Være data-artefakter

**4. Raster-opløsning og polygon-størrelse**

Små lokaliteter samples med få pixels, hvilket giver højere usikkerhed på både:
- Majority vote (få pixels → ét pixel kan tippe resultatet)
- Mean infiltration (mindre repræsentativ for området)

Se Trin 6 for detaljer om selve værdi-rensningen i flux-beregningen.

---

#### Trin 4 – Afstandsanalyse
**Formål:** Beregning af afstand fra hver lokalitet-gvfk kombination til nærmeste vandløbssegment i samme GVFK.

**Metode:**
1. For hver lokalitet-GVFK kombination:
   - Find alle vandløbssegmenter i GVFK'en
   - Beregn minimum afstand (meters) til nærmeste segment
   - Gem vandløbsinfo (FID, ov_id, ov_navn)
2. Tilknytning af metadata (branche, aktivitet, stoffer)
3. Identifikation af minimum-afstand pr. kombination (for multi-GVFK cases)

**Resultat:** Afstande for ~XX.XXX lokalitet-GVFK kombinationer. Statistik: Gennemsnit = XXX m, Median = XXX m.

---

#### Trin 5a – Generel risikovurdering (500m-tærskel)
**Formål:** Konservativ screeningsfilter med universel afstandstærskel.

**Tærskel:** 500 m  
**Kilde:** [KILDE TIL 500M TÆRSKEL - ex. MST vejledning, projekt-definition]

**Metode:**
- Alle kombinationer med afstand ≤ 500m markeres som høj-risiko
- Udelukkende anvendt på kvalificerede sites (med stof- eller lossepladsdata)

**Resultat:** ~X.XXX kombinationer inden for 500m (~XXX unikke lokaliteter i ~XXX GVF'er).

---

#### Trin 5b – Stof-specifik risikovurdering
**Formål:** Målrettet risikovurdering baseret på litteraturbaserede afstandstærskler pr. forureningskategori.

**Metode:**
For hver lokalitet-GVFK kombination:
1. **Kategorisering:** Stoffer kategoriseres via nøgleordsmatch (se nedenfor)
2. **Afstandstærskel:** Kategori-specifik tærskel anvendes
3. **Kvalificering:** Kombination inkluderes hvis afstand ≤ kategoriens tærskel
4. **Losseplads-override:** For lossepladser anvendes særlige tærskler pr. stofkategori

##### Litteraturbaserede kategorier og afstandstærskler

| Kategori | Afstandstærskel | Beskrivelse | Kilde |
|----------|-----------------|-------------|-------|
| **PAH_FORBINDELSER** | 30 m | Polycykliske aromatiske kulbrinter (lav mobilitet, høj sorption) | [KILDE TIL PAH TÆRSKEL] |
| **BTXER** | 50 m | Benzen, toluen, xylen, ethylbenzen + olieprodukter | [KILDE TIL BTXER TÆRSKEL] |
| **PHENOLER** | 100 m | Phenolforbindelser | [KILDE TIL PHENOL TÆRSKEL] |
| **LOSSEPLADS** | 100 m | Lossepladsperkolat (basisværdi) | [KILDE TIL LOSSEPLADS TÆRSKEL] |
| **UORGANISKE_FORBINDELSER** | 150 m | Tungmetaller, salte | [KILDE TIL UORGANISK TÆRSKEL] |
| **KLOREDE_KULBRINTER** | 200 m | Chlorerede/bromerede kulbrinter | [KILDE TIL KLOREDE KULBRINTER] |
| **KLOREREDE_PHENOLER** | 200 m | Chlorerede phenolforbindelser | [KILDE TIL KLOREREDE PHENOLER] |
| **POLARE_FORBINDELSER** | 300 m | MTBE, alkoholer, phthalater | [KILDE TIL POLARE FORBINDELSER] |
| **KLOREREDE_OPLØSNINGSMIDLER** | 500 m | TCE, PCE, vinylchlorid (høj mobilitet) | [KILDE TIL KLOREREDE OPL.MIDLER] |
| **PESTICIDER** | 500 m | Herbicider, fungicider, insekticider | [KILDE TIL PESTICIDER] |
| **PFAS** | 500 m | "Forever chemicals" (høj mobilitet og persistens) | [KILDE TIL PFAS TÆRSKEL] |
| **ANDRE** | 500 m | Ukategoriserede stoffer (default) | [PROJECT DEFAULT] |

> **Note:** Afstandstærskler stammer fra `compound_categories.py`. Kilder til de individuelle tærskler skal tilføjes.

##### Stof-specifikke overrides
Visse stoffer har individuelle tærskler, der overskriver kategori-defaults:

| Stof | Override-tærskel | Kategori-default | Kilde |
|------|------------------|------------------|-------|
| **Benzen** | 200 m | BTXER: 50 m | [KILDE TIL BENZEN OVERRIDE] |
| **Cyanid** | 100 m | UORGANISKE: 150 m | [KILDE TIL CYANID OVERRIDE] |
| **COD** | 500 m | (lossepladsindikator) | [KILDE TIL COD OVERRIDE] |

##### Losseplads-specifikke tærskler
For sites identificeret som lossepladser (via branche/aktivitet-nøgleord) anvendes reducerede tærskler:

| Kategori | Standard tærskel | Losseplads-tærskel | Kilde |
|----------|------------------|-------------------|-------|
| BTXER | 50 m | 70 m | [KILDE TIL LOSSEPLADS OVERRIDES] |
| KLOREREDE_OPLØSNINGSMIDLER | 500 m | 100 m | [KILDE TIL LOSSEPLADS OVERRIDES] |
| PHENOLER | 100 m | 35 m | [KILDE TIL LOSSEPLADS OVERRIDES] |
| PESTICIDER | 500 m | 180 m | [KILDE TIL LOSSEPLADS OVERRIDES] |
| UORGANISKE_FORBINDELSER | 150 m | 50 m | [KILDE TIL LOSSEPLADS OVERRIDES] |

> **Note:** Losseplads-tærskler defineret i `step5_risk_assessment.py` (`LANDFILL_THRESHOLDS`). Kilde til værdier skal tilføjes.

**Resultat:** ~X.XXX site-GVFK-stof kombinationer (~XXX unikke lokaliteter i ~XXX GVF'er).

---

### Diskussion: "Parkerede" Lokaliteter

#### Hvad er parkerede lokaliteter?
Lokaliteter klassificeres som "parkerede" (no qualifying data) hvis de:
1. **Ikke har stoffdata** (`Lokalitetensstoffer` tom eller "nan"), OG
2. **Ikke har lossepladsnøgleord** i branche/aktivitet

#### Hvorfor parkeres de?
Den stof-specifikke risikovurdering (Trin 5b) kræver kendskab til forureningstype for at:
- Tildele den korrekte afstandstærskel
- Kategorisere mht. modelstof og koncentration i Trin 6

Sites uden disse oplysninger kan ikke vurderes kvantitativt og "parkeres" til manuel gennemgang eller fremtidig dataindsamling.

#### Omfang
I typiske kørsler udgør parkerede sites ~X% af input-kombinationerne. De karakteriseres ofte ved:
- Branche/aktivitetstekst uden lossepladsnøgleord (men potentielt anden industritype)
- Helt manglende branche- og aktivitetsdata
- Ældre kortlægninger med ufuldstændige registreringer

#### Håndtering
Parkerede lokaliteter:
- Rapporteres separat (statistik over antal, afstandsfordeling)
- Fanges af den konservative 500m-screening i Trin 5a (hvis de har gyldig geometri)
- Er tilgængelige for fremtidig analyse ved dataopdatering

---

## Tilstandsvurdering (Trin 6)

### Formål
Tilstandsvurderingen kvantificerer forureningsflux fra lokaliteter til vandløbssegmenter og beregner blandingskoncentrationer (Cmix) under forskellige vandføringsscenarier for sammenligning med miljøkvalitetskrav (MKK).

### Input Data

| Datasæt | Kilde | Beskrivelse |
|---------|-------|-------------|
| **Trin 5b output** | step5b_compound_combinations.csv | Kvalificerede lokalitet-GVFK-stof kombinationer (genereret af workflow) |
| **Lokalitetsgeometrier** | step3_v1v2_sites.shp | Polygonarealer for lokaliteter (genereret af workflow) |
| **GVFK→DK-modellag mapping** | Grunddata_results.gdb | Kobling mellem GVFK og infiltrationsraster-lag. **Kilde:** [KILDE] |
| **GVD-rasters** | dkmtif/ | Grundvandsdannelse (mm/år) pr. modellag. **Kilde:** [KILDE - ex. DK-model 2019] |
| **Q-punkter** | Grunddata_results.gdb | Vandføringsdata (Q05-Q95). **Kilde:** [KILDE] |

### Workflow

#### GVD-værdi håndtering i Flux-beregning

I modsætning til Trin 3b (hvor GVD bruges til binær filtrering), bruges GVD-værdier i Trin 6 kvantitativt til faktisk flux-beregning. Dette kræver særlig håndtering af ekstreme værdier.

##### Sampling-strategi

For hver lokalitet samples GVD-raster via **kombineret polygon/centroid tilgang**:

1. **Polygon-sampling (primær):** Alle pixels der overlapper med lokalitetens polygon
2. **Centroid-sampling (fallback):** Bruges hvis polygon-sampling fejler (fx meget små polygoner)

##### Værdi-rensning (Value Cleaning)

Før flux-beregning renses GVD-værdier:

| Værditype | Handling | Begrundelse |
|-----------|----------|-------------|
| **Negative værdier (< 0)** | Sættes til 0 | Opstrømning bidrager ikke til flux |
| **Høje værdier (> cap)** | Cappes til max | Undgår urealistiske flux-værdier |
| **NoData** | Springes over | Ingen data tilgængelig |

**Max infiltrations-cap:** 750 mm/år (konfigurerbar i `config.py` via `gvd_max_infiltration_cap`)

```
Eksempel: Lokalitet med 10 pixels
Råværdier:     [-50, 200, 300, 400, 850, 600, -20, 150, 900, 250]
Efter zeroing: [  0, 200, 300, 400, 850, 600,   0, 150, 900, 250]
Efter capping: [  0, 200, 300, 400, 750, 600,   0, 150, 750, 250]
Mean:          340 mm/år (bruges som I i flux-formlen)
```

##### Output-kolonner

| Kolonne | Beskrivelse |
|---------|-------------|
| `Infiltration_mm_per_year` | Kombineret værdi (polygon hvis mulig, ellers centroid) |
| `Polygon_Infiltration_mm_per_year` | Mean af polygon-pixels |
| `Polygon_Infiltration_Min/Max` | Min/max pixel-værdier |
| `Polygon_Infiltration_Pixel_Count` | Antal samplede pixels |
| `Centroid_Infiltration_mm_per_year` | Centroid-værdi (fallback) |

---

#### Fluxberegning
**Formel:** `J = A × C × I`

Hvor:
- **J** = Flux (masse pr. tid)
- **A** = Lokalitetsareal (m²)
- **C** = Standardkoncentration (µg/L) baseret på kategori/stof
- **I** = Infiltrationsrate (mm/år → m/år)

**Standardkoncentrationer:**  
Koncentrationer er defineret i `config.py` (`STANDARD_CONCENTRATIONS`) med følgende hierarki og kilder:

##### Niveau 1-2: Aktivitet+Stof overrides
90% fraktiler fra Delprojekt 3, Bilag D3.

| Aktivitet + Stof | Koncentration (µg/L) | Kilde |
|------------------|----------------------|-------|
| Servicestationer_Benzen | 8.000 | D3 Tabel 3 |
| Villaolietank_Olie C10-C25 | 6.000 | D3 Tabel 4 |
| Renserier_Trichlorethylen | 42.000 | D3 Tabel 6 |

##### Niveau 3: Losseplads-kontekst
For lokaliteter identificeret som lossepladser:

| Stof | Koncentration (µg/L) | Kilde |
|------|----------------------|-------|
| Benzen | 17 | D3 Tabel 3 |
| Olie C10-C25 | 2.500 | D3 Tabel 4 |
| Trichlorethylen | 2,2 | D3 Tabel 6 |
| Phenol | 6,4 | D3 Tabel 8 |
| Arsen | 25 | D3 Tabel 16 |
| COD | 380.000 | D3 Tabel 17 |

##### Niveau 4: Generelle stof-koncentrationer

| Stof | Koncentration (µg/L) | Kilde |
|------|----------------------|-------|
| Benzen | 400 | D3 Tabel 3 |
| Olie C10-C25 | 3.000 | D3 Tabel 4 |
| 1,1,1-Trichlorethan | 100 | D3 Tabel 5 |
| Trichlorethylen | 42.000 | D3 Tabel 6 |
| Chloroform | 100 | D3 Tabel 7 |
| Phenol | 1.300 | D3 Tabel 8 |
| 4-Nonylphenol | 9 | D3 Tabel 9 |
| MTBE | 50.000 | D3 Tabel 10 |
| Fluoranthen | 30 | D3 Tabel 13 |
| Mechlorprop | 1.000 | D3 Tabel 14 |
| Atrazin | 12 | D3 Tabel 15 |
| Arsen | 100 | D3 Tabel 16 |
| COD | 380.000 | D3 Tabel 17 |
| Cyanid | 3.500 | D3 Tabel 18 |

> **Overordnet kilde:** Delprojekt 3, Bilag D3 (90% fraktil koncentrationer)

##### Niveau 5: Kategori-scenarier
Modelstoffer pr. kategori genererer separate flux-beregninger:

| Kategori | Modelstoffer | Koncentrationer (µg/L) |
|----------|--------------|------------------------|
| BTXER | Benzen, Olie C10-C25 | 400, 3.000 |
| KLOREREDE_OPLØSNINGSMIDLER | 1,1,1-TCA, TCE, Chloroform, Chlorbenzen | 100, 42.000, 100, 100 |
| PHENOLER | Phenol | 1.300 |
| PESTICIDER | Mechlorprop, Atrazin | 1.000, 12 |
| PAH_FORBINDELSER | Fluoranthen | 30 |
| UORGANISKE_FORBINDELSER | Arsen, Cyanid | 100, 3.500 |
| LOSSEPLADS | — | Ingen scenarier (bruges overrides) |
| ANDRE | — | Ingen scenarier (filtreres) |
| PFAS | — | Ingen scenarier (afventer validering) |

**Note:** Kategorier med koncentration = -1 (LOSSEPLADS, ANDRE, PFAS) filtreres fra flux-beregningen.

---

#### Cmix-beregning
**Formel:** `Cmix = Σ Flux / (Q × 1000)`

Hvor:
- **Σ Flux** = Summeret flux fra alle bidragende sites til segment
- **Q** = Vandføring (m³/s) for det valgte scenarie

**Vandføringsscenarier:**
- Q95: Lavvandsvandføring (primært scenarie for MKK-vurdering)
- Q90, Q50, Q10, Q05: Alternative scenarier

**Q-punkt-valg:**  
For hvert vandløbssegment vælges Q-punkt via `downstream_per_segment`-metoden (nærmeste Q-punkt nedstrøms segmentet).

---

#### MKK-overskridelser
**Miljøkvalitetskrav (MKK):** AA-EQS for ferskvand.

##### Kilder til MKK-værdier:
- **Primær:** BEK nr. 1022 af 25/08/2010 (Bilag 2 & 3)
- **PFAS:** BEK nr. 796/2023

##### MKK-værdier (modelstoffer)

| Stof | MKK (µg/L) | Kilde |
|------|------------|-------|
| Benzen | 10 | BEK 1022/2010 |
| 1,1,1-Trichlorethan | 21 | BEK 1022/2010 |
| Trichlorethylen | 10 | BEK 1022/2010 |
| Chloroform | 2,5 | BEK 1022/2010 |
| Phenol | 7,7 | BEK 1022/2010 |
| 4-Nonylphenol | 0,3 | BEK 1022/2010 |
| 2,6-dichlorphenol | 3,4 | BEK 1022/2010 |
| MTBE | 10 | BEK 1022/2010 |
| Fluoranthen | 0,0063 | BEK 1022/2010 |
| Mechlorprop | 18 | BEK 1022/2010 |
| Atrazin | 0,6 | BEK 1022/2010 |
| Arsen | 4,3 | BEK 1022/2010 |
| Cyanid | 10 | BEK 1022/2010 |
| COD | 1.000 | BEK 1022/2010 |

**Note:** Olie C10-C25 og Chlorbenzen har ingen EQS-værdi defineret (`None` i config).

##### MKK-værdier (kategorier)
For ikke-modelstoffer anvendes den laveste EQS i kategorien:

| Kategori | MKK (µg/L) | Basis |
|----------|------------|-------|
| BTXER | 10 | Laveste i gruppe |
| PAH_FORBINDELSER | 0,1 | Laveste i gruppe |
| PHENOLER | 0,3 | Laveste i gruppe |
| KLOREREDE_OPLØSNINGSMIDLER | 2,5 | Laveste i gruppe |
| PESTICIDER | 0,6 | Laveste i gruppe |
| UORGANISKE_FORBINDELSER | 4,3 | Laveste i gruppe |
| PFAS | 0,0044 | BEK 796/2023 |
| LOSSEPLADS | 10 | Default |
| ANDRE | 10 | Default |

**Overskridelsesratio:** `Cmix / MKK`  
Værdier > 1 indikerer overskridelse af miljøkvalitetskrav.

---

### Output

| Fil | Beskrivelse |
|-----|-------------|
| step6_flux_site_segment.csv | Flux pr. lokalitet-segment kombination |
| step6_cmix_results.csv | Cmix pr. segment/stof/scenarie med MKK-flag |
| step6_segment_summary.csv | Ét række pr. segment med max overskridelse |
| step6_sites_mkk_exceedance.csv | Lokaliteter med MKK-overskridelser |
| step6_gvfk_mkk_exceedance.csv | GVF'er med MKK-overskridelser |

---

## Overblik over Metodik

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RISIKOVURDERING                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Trin 1: Alle GVF (~2.200)                                                  │
│     ↓                                                                        │
│  Trin 2: Vandløbskontakt filter → (~1.600 GVF)                              │
│     ↓                                                                        │
│  Trin 3: V1/V2 lokaliteter → (~800 GVF, ~69.000 kombinationer)              │
│     ↓                                                                        │
│  Trin 3b: Infiltrationsfilter (opstrømning) → (filtreret)                   │
│     ↓                                                                        │
│  Trin 4: Afstandsberegning → (~XX.XXX kombinationer med afstand)            │
│     ↓                                                                        │
│  Trin 5a: Generel 500m screening → (~300 GVF)                               │
│  Trin 5b: Stof-specifik vurdering → (~212 GVF, ~3.700 kombinationer)        │
├─────────────────────────────────────────────────────────────────────────────┤
│                            TILSTANDSVURDERING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Trin 6: Flux → Cmix → MKK-overskridelser → (~100 GVF, ~226 lokaliteter)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Kilder og Placeholders at Udfylde

### Manglende kilder (markeret med [KILDE...])

| Parameter-type | Lokation i kode | Status |
|----------------|-----------------|--------|
| **Afstandstærskler (kategorier)** | `compound_categories.py` | ❌ Mangler litteraturreferencer |
| **Afstandstærskler (overrides)** | `compound_categories.py` | ❌ Mangler litteraturreferencer |
| **Losseplads-tærskler** | `step5_risk_assessment.py` | ❌ Mangler litteraturreferencer |
| **500m generel tærskel** | `config.py` (WORKFLOW_SETTINGS) | ❌ Mangler projektreference |
| **Standardkoncentrationer** | `config.py` (STANDARD_CONCENTRATIONS) | ✅ Fra Delprojekt 3, Bilag D3 |
| **MKK-værdier** | `config.py` (MKK_THRESHOLDS) | ✅ BEK nr. 1022/2010, BEK 796/2023 |
| **Input datasæt** | Eksterne filer | ❌ Mangler dato og oprindelsesangivelse |
| **GVD-rasters** | dkmtif/ | ❌ Mangler version (DK-model 2019?) |

### Dokumenterede kilder

| Parameter | Kilde |
|-----------|-------|
| Standardkoncentrationer | Delprojekt 3, Bilag D3 (90% fraktiler) |
| MKK-værdier (modelstoffer) | BEK nr. 1022 af 25/08/2010, Bilag 2 & 3 |
| MKK-værdier (PFAS) | BEK nr. 796/2023 |

---

## Usikkerheder og Forbehold

### Data-kvalitet
- **V1/V2-registreringer:** Historiske data med varierende detaljeringsgrad
- **Stoffordeling:** Afhængig af korrekt nøgleordsmatch i kategorisering
- **Geometrivaliditet:** Forudsætter gyldige polygon-geometrier

### Metodiske antagelser
- **Afstandstærskler:** Litteraturbaserede, men generaliserede værdier
- **Standardkoncentrationer:** Worst-case fra Delprojekt 3, ikke site-specifikke
- **Infiltration:** Antagelse om nedadrettet strømning (sites med opstrømning filtreres)

### Konservative tilgange
- Multi-GVFK tilgang bevarer alle potentielt påvirkede GVF'er
- Sites uden rasterdata bevares (fremfor at filtreres)
- Q95 (lavvandsvandføring) sikrer vurdering under kritiske forhold
