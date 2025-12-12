---
title: "Risiko- og Tilstandsvurdering"
lang: da
---

# Risiko- og Tilstandsvurdering

## Risikovurdering

Formålet med risikovurderingen er at identificere hvilke grundvandsforekomster (GVF'er) med kontakt til målsatte vandløb der er i risiko for påvirkning fra forurenede lokaliteter (V1/V2). Metodikken anvender afstandsbaserede tærskler differentieret efter forureningskategori og filtrerer systematisk fra alle danske grundvandsforekomster ned til dem, hvor forureningsrisikoen er størst.

### Inputdata

Analysen bygger på følgende datagrundlag. Data er opdateret til Vandplan 4 (VP4) [REFERENCE: VP4 kilde]:

| Datasæt | Beskrivelse | Kilde |
|---------|-------------|-------|
| **Grundvandsforekomster (GVF)** | GVFK-polygoner fra `Grunddata_results.gdb` | GEUS (VP4) |
| **Vandløbssegmenter** | Vandløb med GVF-kontakt fra `Grunddata_results.gdb` | GEUS (VP4) |
| **V1/V2-lokaliteter** | Kortlagte forurenede grunde med stof- og brancheinformation (CSV) | MST/DKjord |
| **V1/V2-geometrier** | Polygongeometrier for lokaliteter (Shapefile) | MST/DKjord |
| **GVD-rasters** | Grundvandsdannelse (infiltration) i mm/år pr. DK-modellag, 100×100m opløsning | GEUS/DK-model [REFERENCE: DK-model version] |
| **Q-punkter** | Vandføringsdata (Q50-Q95) fra `Grunddata_results.gdb` | GEUS (VP4) |

---

### Fra grundvandsforekomster til risiko-lokaliteter

Udgangspunktet for risikovurderingen er de **2.049 grundvandsforekomster** i Danmark. Ikke alle grundvandsforekomster har kontakt til målsatte vandløb, og første filtreringstrin identificerer derfor de **547 GVF'er** (27%) med dokumenteret vandløbskontakt.

Inden for disse grundvandsforekomster er der registreret **34.801 forurenede lokaliteter** (V1 og V2) fordelt på **459 GVF'er**. Disse lokaliteter kobles med deres geometrier og forureningsdata, herunder stoffer og aktivitets/brancheinformation. Da en lokalitet kan påvirke flere grundvandsforekomster, genereres ca. **64.824 lokalitet-GVFK kombinationer** til videre analyse.

> **[FIGUR: GVFK Progression]**
> *Søjlediagram der viser antal GVF'er og lokaliteter efter hvert filtreringstrin i risikovurderingen.*

---

### Infiltrationsfiltrering

Før afstandsanalysen filtreres lokaliteter i opstrømningszoner fra. Fluxformlen (J = A × C × I) forudsætter nedadrettet grundvandsstrømning (positiv infiltration). I opstrømningszoner strømmer grundvand opad mod terræn, og forurening transporteres derfor ikke til vandløbet via infiltration. Disse lokaliteter er ikke relevante for risikovurderingen og fjernes fra analysen.

**Datagrundlag:** For hver lokalitet samples grundvandsdannelse (GVD) fra DK-modellens rasters (100×100m opløsning). Alle pixels der overlapper med lokalitetens polygon-geometri samples, med fallback til centroid-sampling for meget små polygoner.

**Binær klassificering:** Hver pixel-værdi konverteres til et binært flag baseret på strømningsretning: negative værdier indikerer opadrettet strømning (opstrømning), mens positive værdier indikerer nedadrettet strømning (infiltration). Denne binære tilgang er valgt fordi GVD-rasterne fra DK-modellen ved lokalitetsskala kan udvise ekstreme variationer mellem nabopixels – eksempelvis -10.000 mm/år ved siden af +100 mm/år. Ved at fokusere på *retningen* af strømning frem for selve værdien undgås at sådanne artefakter påvirker klassificeringen.

**Majoritetsafgørelse:** Andelen af pixels med nedadrettet strømning beregnes for hver lokalitet. Hvis over 50% af pixels har positiv strømning, klassificeres lokaliteten som "nedadrettet" og beholdes i analysen. Lokaliteter med overvejende opadrettet strømning fjernes.

**Resultat:** Infiltrationsfiltreringen fjernede **15.083 kombinationer** (23%) med opadrettet strømning (negative pixels), mens **49.741 kombinationer** (77%) med nedadrettet strømning (positive pixels) fortsatte til afstandsanalysen. Dette svarer til **29.570 unikke lokaliteter** (85% af originale) i **445 GVF'er**. Lokaliteter uden tilgængelig rasterdata bevares som konservativ tilgang.

---

### Afstandsanalyse

For hver tilbageværende lokalitet-GVFK kombination beregnes afstanden til nærmeste vandløbssegment. Afstanden måles fra kanten af lokalitetens polygon til det nærmeste punkt på et vandløbssegment inden for samme grundvandsforekomst. For lokaliteter der overlapper flere GVF'er (multi-GVFK lokaliteter) beregnes en separat minimumsafstand for hver GVFK-tilknytning, da vandløbssegmenterne kan variere mellem GVF'er.

> **[FIGUR: Afstandsfordeling]**
> *Histogram der viser fordelingen af afstande fra lokaliteter til nærmeste vandløbssegment. Gennemsnitlig lokalitet-gvf afstand: 4.546 m, median: 2.357 m.*

---

### Afstandsbaseret vurdering

Den endelige del af risikovurderingen anvender en to-trins tilgang for lokaliteter med kvalificerende data. En lokalitet kvalificerer sig hvis den enten har registrerede stoffer i DKjord-databasen (kolonnen `Lokalitetensstoffer` ikke tom) eller identificeres som losseplads baseret på nøgleord i Aktivitet/Branche-felterne (fx 'losseplads', 'deponi', 'fyldplads'). Af de **49.741 kombinationer** fra Step 4 har **25.601** (52%) kvalificerende data, mens **24.140** (48%) er "parkerede" lokaliteter uden stof- eller lossepladsdata.

1. **Generel 500m-screening:** Alle lokaliteter med kvalificerende data inden for 500 m af et vandløbssegment identificeres som potentielt i risiko. Parkerede lokaliteter (uden stof-/lossepladsdata) indgår ikke i denne optælling, men behandles separat.

2. **Stof-specifik vurdering:** For samme lokaliteter anvendes differentierede afstandstærskler baseret på stofkategori.

---

### Stof-specifik risikovurdering

Den stof-specifikke risikovurdering anvender litteraturbaserede afstandstærskler differentieret efter forureningskategori [REFERENCE: kilde til afstandstærskler]. Stoffer med høj mobilitet og persistens har tærskler op til 500 m, mens stoffer med lav mobilitet og høj sorption har tærskler ned til 30 m.

**Kategori-tærskler:**

| Kategori | Afstandstærskel | Eksempler på stoffer |
|----------|-----------------|----------------------|
| PAH-forbindelser | 30 m | Polycykliske aromatiske kulbrinter |
| BTXER | 50 m | Benzen, toluen, xylen, olieprodukter |
| Phenoler | 100 m | Phenolforbindelser |
| Uorganiske forbindelser | 150 m | Tungmetaller, salte |
| Klorerede phenoler | 200 m | Klorerede fenolforbindelser |
| Chlorerede kulbrinter | 200 m | Chlorerede/bromerede kulbrinter |
| Polare forbindelser | 300 m | MTBE, alkoholer, phthalater |
| Chlorerede opløsningsmidler | 500 m | TCE, PCE, vinylchlorid |
| Pesticider | 500 m | Herbicider, fungicider, insekticider |
| PFAS | 500 m* | Per- og polyfluoralkylstoffer |

*PFAS-tærsklen på 500 m er en placeholder-værdi; litteraturbaserede afstandstærskler for PFAS er ikke etableret. PFAS indgår i risikovurderingen men ikke i tilstandsvurderingen, da der ikke findes standardkoncentrationer for flux-beregning i litteraturen anvendt.

**Losseplads-overrides:** For lokaliteter identificeret som lossepladser (via branche/aktivitet-nøgleord) anvendes modificerede tærskler baseret på Bjerg et al. (2014) [REFERENCE: Bjerg, P.L., Sonne, A.T., Tuxen, N., Skov Nielsen, S., Roost, S. (2014). Risikovurdering af lossepladsers påvirkning af overfladevand]:

| Kategori | Standard tærskel | Losseplads-tærskel |
|----------|------------------|-------------------|
| BTXER | 50 m | 70 m |
| Chlorerede opløsningsmidler | 500 m | 100 m |
| Phenoler | 100 m | 35 m |
| Pesticider | 500 m | 180 m |
| Uorganiske forbindelser | 150 m | 50 m |

**Beslutningslogik:** For hver kombination af *lokalitet*, *GVFK* og *stofkategori* vurderes afstanden til nærmeste vandløbssegment mod kategoriens tærskel. En kombination kvalificerer sig til tilstandsvurderingen hvis afstanden er mindre end eller lig med tærsklen. En lokalitet med flere stoffer genererer derfor flere kvalificerende kombinationer – én pr. stofkategori der opfylder tærskelkravet.

---

### Resultater: Risikovurdering

**Generel 500m-screening:**
- Lokaliteter inden for 500 m: **2.812** (fordelt på **275 GVF'er**)
- Heraf parkerede lokaliteter: **2.923**

**Stof-specifik vurdering:**
Efter anvendelse af kategori-specifikke tærskler identificeres ca. **2.095 site-GVFK-stof kombinationer** fordelt på ca. **927 unikke lokaliteter** i **186 GVF'er**.

**Fordeling efter stofkategori:**

| Kategori | Antal kombinationer | Andel |
|----------|---------------------|-------|
| [KATEGORI 1] | X.XXX | XX% |
| [KATEGORI 2] | X.XXX | XX% |
| [KATEGORI 3] | X.XXX | XX% |
| Losseplads | X.XXX | XX% |
| Øvrige | X.XXX | XX% |

> **[FIGUR: Kategorifordeling]**
> *[Søjlediagram eller cirkeldiagram der viser fordelingen af lokaliteter efter stofkategori]*

---

### Lokaliteter uden stofdata ("parkerede" lokaliteter)

Lokaliteter klassificeres som "parkerede" hvis de hverken har registreret stoffer i DKjord-databasen (kolonnen `Lokalitetensstoffer` tom) eller lossepladsnøgleord i branche/aktivitet-felterne. Disse lokaliteter er typisk V1-kortlægninger, ofte ældre registreringer med ufuldstændige oplysninger.

**Begrænsninger:** Parkerede lokaliteter kan ikke indgå i den stofspecifikke distance analyse i trin 5 eller i den stofspecifikke tilstandsvurdering (Trin 6), da fluxberegningen kræver kendskab til stoftype for at tildele standardkoncentrationer og MKK-værdier. De indgår dog i den generelle 500m-screening.  

**Regional fordeling og påvirkning:** Inkludering af parkerede lokaliteter inden for 500m-tærsklen øger antallet af berørte GVF'er markant:

| Kategori | Antal lokaliteter | Antal GVF'er |
|----------|-------------------|--------------|
| **Trin 5a baseline (≤500m)** | 927 | 275 |
| **Parkerede lokaliteter (≤500m)** | +1.958 | +38 |
| **Total (inkl. parkerede)** | **2.885** | **313** |
| **Ændring** | **+111%** | **+13.8%** |

*Trin 5a = lokaliteter med stofdata inden for 500m; inkl. parkerede = med parkerede lokaliteter*

**Regional fordeling (parkerede lokaliteter ≤500m):**

| Region | Parkerede lokal. (≤500m) | Andel |
|--------|--------------------------|-------|
| Region Syddanmark | 750 | 38.3% |
| Region Midtjylland | 649 | 33.1% |
| Region Nordjylland | 296 | 15.1% |
| Region Sjælland | 140 | 7.2% |
| Region Hovedstaden | 123 | 6.3% |
| **TOTAL** | **1.958** | **100%** |

Analysen viser at inkludering af parkerede lokaliteter inden for 500m-tærsklen ville øge antallet af potentielt berørte GVF'er fra 275 til 313 (+13.8%) og mere end fordoble antallet af lokaliteter fra 927 til 2.885 (+111%). Den forholdsvis beskedne GVF-påvirkning (kun 38 nye GVF'er) skyldes at mange parkerede lokaliteter ligger i samme GVF'er som lokaliteter med stofdata.

---

### Resultater: Risikovurdering

Den trinvise filtrering reducerer fokusområdet systematisk:

| Trin | GVF'er | Lokaliteter | Kombinationer |
|------|--------|-------------|---------------|
| Alle GVF i Danmark | 2.049 | — | — |
| Med vandløbskontakt | 547 | — | — |
| Med V1/V2 lokaliteter | 459 | 34.801 | 64.824 |
| Efter infiltrationsfilter | 445 | 29.570 | 49.741 |
| Stof-specifik risiko | 186 | 927 | 2.095 |

---

## Tilstandsvurdering

Tilstandsvurderingen kvantificerer forureningsflux fra de identificerede risiko-lokaliteter og beregner blandingskoncentrationer i vandløbssegmenterne. Disse sammenlignes med miljøkvalitetskrav (MKK) for at identificere segmenter med potentiel overskridelse.

### Inputdata (Tilstandsvurdering)

Tilstandsvurderingen bygger på resultaterne fra risikovurderingen samt:

| Datasæt | Beskrivelse |
|---------|-------------|
| **Risiko-lokaliteter** | Kvalificerede lokalitet-GVFK-stof kombinationer fra risikovurderingen |
| **Lokalitetsarealer** | Polygonarealer beregnet fra V1/V2-geometrier |
| **Infiltrationsdata** | GVD-rasters med grundvandsdannelse pr. lokalitet |
| **Vandføringsdata** | Q-punkt data for forskellige vandføringsscenarier (Q95, Q50, etc.) |
| **Standardkoncentrationer** | Litteraturbaserede stofkoncentrationer (90% fraktiler fra Delprojekt 3) |

---

### Fluxberegning

Forureningsflux fra hver lokalitet beregnes ud fra formlen:

**J = A × C × I**

hvor J er flux (masse pr. tid), A er lokalitetsareal (m²), C er standardkoncentration (µg/L), og I er infiltrationsrate (mm/år).

**Modelstof-scenarier:** Da de fleste lokaliteter har mange stoffer registreret indenfor samme kategori, anvendes en scenariobaseret aggregering. Hver stofkategori har et sæt definerede *modelstoffer* med validerede standardkoncentrationer fra Delprojekt 3:

| Kategori | Modelstoffer | Koncentrationer (µg/L) |
|----------|--------------|------------------------|
| BTXER | Benzen, Olie C10-C25 | 400, 3.000 |
| KLOREREDE_OPLØSNINGSMIDLER | 1,1,1-Trichlorethan, TCE, Chloroform, Chlorbenzen | 100, 42.000, 100, 100 |
| POLARE_FORBINDELSER | MTBE, 4-Nonylphenol | 50.000, 9 |
| PHENOLER | Phenol | 1.300 |
| KLOREREDE_PHENOLER | 2,6-dichlorphenol | 10.000 |
| PESTICIDER | Mechlorprop, Atrazin | 1.000, 12 |
| PAH_FORBINDELSER | Fluoranthen | 30 |
| UORGANISKE_FORBINDELSER | Arsen, Cyanid | 100, 3.500 |

**Scenariehåndtering:** Hvert modelstof-scenarie behandles separat gennem flux- og Cmix-beregningen. Ved tælling af påvirkede GVF'er aggregeres dog alle scenarier: en GVFK tælles som påvirket hvis *mindst ét* scenarie viser MKK-overskridelse.

*Eksempel:* En lokalitet med 4 forskellige BTXER-stoffer genererer kun 2 flux-rækker: én for Benzen-scenariet og én for Olie-scenariet.

**Flux-aggregering:** For at undgå dobbelt-optælling grupperes data først på (Lokalitet, GVFK, Vandløbssegment, Stofkategori). Dette sikrer at én lokalitet kun bidrager med én flux pr. modelstof pr. segment den påvirker.

**Kategorier uden modelstoffer:** LOSSEPLADS, PFAS og ANDRE har ingen definerede modelstoffer og filtreres derfor fra i fluxberegningen. Disse kategorier indgår i risikovurderingen men ikke i Cmix-beregningen.

Standardkoncentrationerne stammer fra Delprojekt 3, Bilag D3 [REFERENCE: fuld reference til Delprojekt 3] og repræsenterer 90% fraktiler. For specifikke aktivitetstyper anvendes aktivitetsspecifikke koncentrationer hvor tilgængelige.

**Infiltrationsværdier:** Infiltrationsraten bestemmes ved sampling af GVD-rasters under hver lokalitet. Negative pixel-værdier sættes til 0, da kun positiv infiltration bidrager til transport mod vandløbet. En max-cap på 750 mm/år anvendes [REFERENCE: kilde til 750 mm/år cap].

---

### Blandingskoncentration og MKK-vurdering

For hvert vandløbssegment summeres flux fra alle bidragende lokaliteter, og blandingskoncentrationen (Cmix) beregnes:

**Cmix = Σ Flux / (Q × 1000)**

hvor Q er vandføringen (m³/s). Vurderingen udføres primært ved Q95 (lavvandsvandføring), som repræsenterer kritiske forhold.

Cmix sammenlignes med miljøkvalitetskrav (MKK) baseret på AA-EQS for ferskvand fra BEK nr. 1022 af 25/08/2010 [REFERENCE: fuld BEK reference] og BEK nr. 796/2023 for PFAS [REFERENCE: fuld BEK reference]. En overskridelsesratio (Cmix/MKK) over 1 indikerer potentiel overskridelse af miljøkvalitetskrav.

---

### Resultater: Tilstandsvurdering

Tilstandsvurderingen kvantificerer påvirkningen af de kortlagte lokaliteter på vandløb:

| Metrik | Værdi |
|--------|-------|
| Vandløbssegmenter med stofpåvirkning | 440 |
| Segmenter med MKK-overskridelse (Q95) | 282 |
| Bidragende lokaliteter | 354 |
| Påvirkede GVF'er | 116 |
| Højeste Cmix/MKK-forhold | 41.337× |
| Median Cmix/MKK-forhold | 7,2× |

**Vandføringsscenariets betydning:** Antallet af segmenter med MKK-overskridelse afhænger markant af vandføringsscenariet:

| Scenario | Segmenter med overskridelse | Beskrivelse |
|----------|----------------------------|-------------|
| Q95 | 282 | Lavvandsvandføring (kritisk) |
| Q50 | 237 | Medianvandføring |
| Q05 | 158 | Højvandsvandføring |

124 segmenter overskrider kun MKK ved lavvandsvandføring (Q95), mens 158 segmenter overskrider ved alle vandføringsscenarier.

**Overskridelser fordelt på stofkategorier (Q95):**

| Stofkategori | Segmenter | Max ratio | Median ratio |
|--------------|-----------|-----------|--------------|
| Klorerede opløsningsmidler | 147 | 41.337× | 12× |
| Pesticider | 63 | 3.529× | 11× |
| Uorganiske forbindelser | 39 | 344× | 5× |
| BTXER | 34 | 1.520× | 9× |
| Polare forbindelser | 31 | 2.899× | 13× |
| Klorede kulbrinter | 13 | 35.567× | 12× |
| PAH-forbindelser | 10 | 238× | 22× |
| Klorerede phenoler | 7 | 6.227× | 35× |
| Phenoler | 6 | 9.174× | 24× |

> **Bemærk:** De høje overskridelsesratioer (op til 41.337×) skyldes primært tre faktorer: (1) lavvandsvandføring ved Q95, (2) høje standardkoncentrationer for visse stoffer, og (3) akkumulering af flux fra flere lokaliteter til samme segment.

## Usikkerheder og forbehold (MÅSKE AFSNIT ELLER NOGET???)

Resultaterne er behæftet med usikkerheder på flere niveauer:

### Data-kvalitet

**V1/V2-registreringer:** Historiske data med varierende detaljeringsgrad. Stoffordelingen afhænger af korrekt nøgleordsmatch i kategoriseringen.

**Geometrivaliditet:** Analysen forudsætter gyldige polygon-geometrier for lokaliteter. Fejl i geometrier kan påvirke både infiltrationssampling og afstandsberegninger. 

### Metodiske antagelser

**Afstandstærskler:** Litteraturbaserede, generaliserede værdier og ikke stedspecifikke. Tærsklerne repræsenterer typiske transportafstande men kan variere betydeligt afhængigt af lokale hydrogeologiske forhold.

**Standardkoncentrationer:** Worst-case koncentrationer (90% fraktiler) fra Delprojekt 3 anvendes generelt. Disse er ikke site-specifikke og kan overvurdere faktiske koncentrationer.

**Infiltrationsfilter:** Binær klassificering baseret på majoritetsafgørelse (>50% nedadrettede pixels). Lokaliteter tæt på 50%-tærsklen har blandet strømningsretning og kan have betydelig lokal opstrømning, hvilket gør klassificeringen usikker.

**Cap-værdi for infiltration:** Max-cap på 750 mm/år [REFERENCE: kilde til cap-værdi] anvendes for at filtrere ekstreme værdier. Højere værdier kan både repræsentere reelle forhold (høj nedbør, permeabel geologi) eller være data-artefakter.

### Spatial heterogenitet

Store lokaliteter kan dække områder med fundamentalt forskellige hydrogeologiske forhold. Den binære infiltrationsklassificering antager at én overordnet klassificering er meningsfuld for hele lokaliteten, selvom der kan være betydelig variation internt.

Små lokaliteter samples med få pixels, hvilket giver højere usikkerhed på både majoritetsafgørelse (ét pixel kan tippe resultatet) og gennemsnitlig infiltration (mindre repræsentativ for området).

### Konservative tilgange

Metodikken anvender flere konservative antagelser for at undgå at undervurdere risikoen:

- **Multi-GVFK-tilgang:** Bevarer alle potentielt påvirkede GVF'er. En lokalitet med tilknytning til flere GVF'er tæller med i alle, selvom den primære påvirkning sandsynligvis kun sker via én.
- **Sites uden rasterdata:** Bevares i analysen (fremfor at filtreres) som konservativ tilgang.
- **Q95 (lavvandsvandføring):** Sikrer vurdering under kritiske forhold med lav fortynding, men repræsenterer ikke gennemsnitlige forhold.

---

## Bilag: Data Dictionary

Dette bilag beskriver de primære outputfiler fra risikovurdering og tilstandsvurdering.

### Risikovurdering: step5b_compound_combinations.csv  

Denne fil indeholder alle lokalitet-stof-kombinationer der opfylder afstandskriteriet.

| Kolonne | Type | Eksempel / Interval |
|---------|------|---------------------|
| `Lokalitet_ID` | Tekst | f.eks. 101-00006 |
| `GVFK` | Tekst | f.eks. dkms_3645_ks |
| `Site_Type` | Kategorisk | V1, V2, V1 og V2 |
| `Qualifying_Substance` | Tekst | f.eks. Tetrachlorethylen |
| `Qualifying_Category` | Tekst | f.eks. KLOREREDE_OPLØSNINGSMIDLER |
| `Distance_to_River_m` | Decimaltal | 0 – 500 m |
| `Category_Threshold_m` | Decimaltal | 30 – 500 m |
| `Within_Threshold` | Boolean | True / False |
| `Nearest_River_ov_id` | Tekst | f.eks. DKRIVER7798 |
| `Nearest_River_ov_navn` | Tekst | f.eks. Harrestrup Å, C |
| `River_Segment_FIDs` | Liste (;-separeret) | f.eks. 54906;54907;54908... |
| `Lokalitetensstoffer` | Liste (;-separeret) | f.eks. Benz[a]pyren; Tetrachlorethylen... |
| `Lokalitetensbranche` | Liste (;-separeret) | f.eks. Gasforsyning;Servicestationer... |

### Tilstandsvurdering: step6_site_mkk_exceedances.csv

Denne fil indeholder lokaliteter der bidrager til MKK-overskridelser i vandløb.

| Kolonne | Type | Eksempel / Interval |
|---------|------|---------------------|
| `Lokalitet_ID` | Tekst | f.eks. 815-00617 |
| `GVFK` | Tekst | f.eks. dkmj_983_ks |
| `Qualifying_Category` | Kategorisk | KLOREREDE_OPLØSNINGSMIDLER, PESTICIDER, etc. |
| `Qualifying_Substance` | Tekst | f.eks. KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethen |
| `Pollution_Flux_kg_per_year` | Decimaltal | 0 – 4.373 kg/år |
| `Cmix_ug_L` | Decimaltal | 0,1 – 103.344 µg/L |
| `MKK_ug_L` | Decimaltal | 0,1 – 10 µg/L |
| `Exceedance_Ratio` | Decimaltal | 1 – 41.337 (Cmix/MKK) |
| `Flow_Scenario` | Kategorisk | Q95, Q90, Q50, Q10, Q05 |
| `Flow_m3_s` | Decimaltal | 0 – 25 m³/s |
| `Nearest_River_ov_id` | Tekst | f.eks. DKRIVER3405 |
| `River_Segment_Name` | Tekst | f.eks. Hjulrenden |
| `Distance_to_River_m` | Decimaltal | 0 – 500 m |
