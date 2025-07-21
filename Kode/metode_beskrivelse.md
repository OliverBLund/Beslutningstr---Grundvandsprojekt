# Metodebeskrivelse: Analyse af V1/V2-lokaliteters Afstand til Vandløb i Grundvandsforekomster

## Datagrundlag
Analysen er baseret på følgende datafiler:

### Shape-filer:
- `VP3Genbesøg_grundvand_geometri.shp`: Grundvandsforekomster (GVFK) - 2.043 unikke forekomster
- `Rivers_gvf_rev20230825_kontakt.shp`: Vandløbsstrækninger med tilknyttet GVFK og kontaktflag (14.454 segmenter, 7.496 med kontakt)
- `V1FLADER.shp`: V1-lokaliteter som polygoner (28.717 polygoner, 23.209 unikke lokaliteter)
- `V2FLADER.shp`: V2-lokaliteter som polygoner (33.040 polygoner, 21.269 unikke lokaliteter)

### CSV-filer (med detaljerede attributter):
- `Data/v1_gvfk_forurening.csv`: V1-lokaliteter med GVFK-relationer og forureningsdata (84.601 rækker)
- `Data/v2_gvfk_forurening.csv`: V2-lokaliteter med GVFK-relationer og forureningsdata (134.636 rækker)

**Vigtige kolonner til risikovurdering:**
- `Lokalitetensbranche`: Branche/industri-information
- `Lokalitetensaktivitet`: Aktivitetstype
- `Lokalitetensstoffer`: Forureningsstoffer (kun lokaliteter med data medtages)

## Analysetrin

### Trin 1: Optælling af Grundvandsforekomster
**Formål**: Identificere det totale antal unikke grundvandsforekomster (GVFK).

**Metode**:
- Indlæsning af `VP3Genbesøg_grundvand_geometri.shp`
- Optælling af unikke værdier i "Navn"-kolonnen
- Resultat gemmes i `step1_all_gvfk.shp`

**Aktuelle Resultater**:
- **2.043 unikke grundvandsforekomster** identificeret

### Trin 2: Grundvandsforekomster med Vandløbskontakt
**Formål**: Identificere hvilke grundvandsforekomster der har kontakt med vandløb.

**Metode**:
- Indlæsning af `Rivers_gvf_rev20230825_kontakt.shp` (14.454 vandløbssegmenter)
- Udtræk af unikke GVFK-navne fra "GVForekom"-kolonnen
- Kun vandløbsstrækninger med `Kontakt = 1` medtages (7.496 segmenter)
- Resultater gemmes i `step2_gvfk_with_rivers.shp`

**Aktuelle Resultater**:
- **593 GVFK har kontakt med vandløb** (29,0% af alle GVFK)
- 588 GVFK-geometrier gemt med vandløbskontakt
- Disse GVFK danner grundlag for videre analyse af V1/V2-lokaliteter

### Trin 3: V1/V2-lokaliteter med Aktive Forureninger i GVFK med Vandløbskontakt
**Formål**: Identificere V1/V2-lokaliteter med aktive forureninger i grundvandsforekomster med vandløbskontakt.

**Metode**:
1. **Indlæsning og filtrering af CSV-data**:
   - `Data/v1_gvfk_forurening.csv`: 84.601 rækker → **34.232 efter filtrering** (60% reduktion - fjernet 50.369)
   - `Data/v2_gvfk_forurening.csv`: 134.636 rækker → **121.984 efter filtrering** (9% reduktion - fjernet 12.652)
   - **Aktiv forureningsfilter**: Kun lokaliteter med konkrete forureningsstoffer i `Lokalitetensstoffer`-kolonnen medtages
     - Fjerner lokaliteter uden forureningsdata (NaN/tom værdi)
     - Sikrer fokus på steder med dokumenterede aktive forureninger
   - **Vandløbsfilter**: Kun lokaliteter i GVFK med vandløbskontakt fra Trin 2 medtages

2. **Geometri-kobling**:
   - Indlæsning af V1/V2-shapefiles: `V1FLADER.shp` og `V2FLADER.shp`
   - Opløsning af geometrier per lokalitet (dissolve by `Lokalitets`-kolonne)
   - Kobling af CSV-data med geometri baseret på lokalitetsnummer

3. **Deduplikering**:
   - V1: 21.697 → **8.269 unikke lokalitet-GVFK kombinationer** efter deduplikering
   - V2: 79.893 → **28.694 unikke lokalitet-GVFK kombinationer** efter deduplikering
   - Fjernelse af 4.572 duplikerede lokalitet-GVFK kombinationer mellem V1 og V2
   - Håndtering af lokaliteter der forekommer i både V1 og V2 (markeres som "V1 og V2")

4. **Resultater gemmes i**:
   - `step3_v1v2_sites.shp`: Alle lokalitet-GVFK kombinationer med geometri
   - `step3_gvfk_with_v1v2.shp`: GVFK-polygoner med V1/V2-lokaliteter
   - `step3_site_gvfk_relationships.csv`: Detaljerede relationer med forureningsdata

**Aktuelle Resultater**:
- **16.934 unikke V1/V2-lokaliteter** med aktive forureninger
- **32.391 totale lokalitet-GVFK kombinationer** efter deduplikering
- **432 GVFK har V1/V2-lokaliteter** (21,1% af alle GVFK)
- Gennemsnitligt 1,9 GVFK per lokalitet

**Lokalitet-fordeling efter type**:
- **V2**: 12.663 lokaliteter (72,2%)
- **V1 og V2**: 2.398 lokaliteter (13,7%)
- **V1**: 1.873 lokaliteter (14,1%)

**Kvalitetssikring**:
- Eliminerer "tomme" lokaliteter uden forureningsinformation
- Sikrer at kun steder med potentiel påvirkning af grundvand medtages
- Reducerer datamængde til de mest relevante lokaliteter for risikovurdering

### Trin 4: Afstandsanalyse til Vandløb
**Formål**: Beregne afstande mellem V1/V2-lokaliteter og nærmeste vandløbsstrækninger inden for samme GVFK.

**Metode**:
1. **Dataindlæsning**:
   - V1/V2-lokaliteter fra Trin 3 (med forureningsdata bevaret)
   - Vandløbsstrækninger fra `Rivers_gvf_rev20230825_kontakt.shp` (kun `Kontakt = 1`)

2. **Afstandsberegning per lokalitet-GVFK kombination**:
   - For hver lokalitet-GVFK kombination fra Trin 3:
     - Find vandløbsstrækninger med `Kontakt = 1` i samme GVFK
     - Beregn minimumsafstand til disse vandløbsstrækninger
     - Bevar alle forureningsdata (branche, aktivitet, stoffer)

3. **Identifikation af endelige afstande**:
   - For lokaliteter i flere GVFK: identificer den korteste afstand
   - Marker denne som `Is_Min_Distance = True` for risikovurdering
   - Bevar information om alle berørte GVFK

4. **Resultater gemmes i**:
   - `step4_distance_results.csv`: Alle lokalitet-GVFK kombinationer med afstande
   - `step4_valid_distances.csv`: Kun kombinationer med gyldige afstande
   - `step4_final_distances_for_risk_assessment.csv`: **Endelige afstande per lokalitet** ⭐
   - `unique_lokalitet_distances.csv`: For visualiseringer
   - `v1v2_sites_with_distances.shp`: Shapefil med alle data
   - `step4_site_level_summary.csv`: Sammenfattende lokalitet-niveau statistik
   - Interaktivt kort med stikprøvedata (1.000 lokaliteter)

**Vigtige Output-kolonner til Trin 5**:
- `Final_Distance_m`: Korteste afstand per lokalitet
- `Lokalitetensbranche`: Branche/industri
- `Lokalitetensaktivitet`: Aktivitetstype  
- `Lokalitetensstoffer`: Forureningsstoffer
- `Total_GVFKs_Affected`: Antal berørte GVFK per lokalitet

**Aktuelle Resultater**:
- **32.391 lokalitet-GVFK kombinationer** med beregnede afstande (100% success rate)
- **16.934 unikke lokaliteter** med endelige afstande
- **Afstandsstatistik for alle kombinationer**: 0,0m - 81.437m (gennemsnit: 6.476m, median: 3.003m)
- **Endelige afstande per lokalitet**: 0,0m - 47.116m (gennemsnit: 3.486m, median: 1.550m)

**Afstandsberegninger efter lokalitet-type**:
- V2: 24.122 lokalitet-GVFK kombinationer
- V1 og V2: 4.572 lokalitet-GVFK kombinationer  
- V1: 3.697 lokalitet-GVFK kombinationer

## Trin 5: Risikovurdering (500m Tærskel)
**Formål**: Identificere lokaliteter med høj risiko baseret på afstand og forureningsdata.

**Inddata fra Trin 4**:
- `step4_final_distances_for_risk_assessment.csv` med endelige afstande per lokalitet
- Alle nødvendige kolonner til risikovurdering er inkluderet

**Metode**:
1. **Afstandsfiltrering**: Filtrer lokaliteter med `Final_Distance_m ≤ 500` meter
2. **Risikoanalyse**: Analyser baseret på:
   - `Lokalitetensbranche`: Industri-/brancherisiko
   - `Lokalitetensaktivitet`: Aktivitetsrisiko
   - `Lokalitetensstoffer`: Specifikke forureningsstoffer
3. **Multi-GVFK analyse**: Undersøg lokaliteter der påvirker flere GVFK

**Aktuelle Resultater**:
- **3.606 højrisiko-lokaliteter** inden for 500m af vandløb (21,3% af alle lokaliteter)
- **350 GVFK indeholder højrisiko-lokaliteter** (17,1% af alle GVFK, 81,0% af V1/V2 GVFK)
- Afstandsstatistik for højrisiko-lokaliteter: 0,0m - 500,0m (gennemsnit: 232m, median: 229m)

**Højrisiko-lokaliteter efter type**:
- V2: 2.605 (72,2%)
- V1 og V2: 560 (15,5%)
- V1: 441 (12,2%)

**Forureningsanalyse (Top 5)**:
- **Brancher**: Servicestationer (651), Autoreparationsværksteder (614), Affaldsbehandling (388)
- **Aktiviteter**: Andet (897), Benzin/olie salg (661), Benzin/olie oplag (436)
- **Stoffer**: Tungmetaller (451), Olieprodukter (250), Fyringsolie (226)

**Multi-GVFK påvirkning**:
- 2.969 lokaliteter (82,3%) påvirker flere GVFK
- Gennemsnitligt 2,6 GVFK per multi-GVFK lokalitet
- Maksimum 5 GVFK påvirket af én lokalitet

## Samlet Overblik
- **Datagrundlag**: **2.043 grundvandsforekomster** i Danmark
- **Vandløbskontakt**: **593 GVFK** (29,0%) har kontakt med vandløb
- **Aktiv forureningsfiltrering**: 
  - V1: 84.601 → **34.232 lokaliteter** med aktive forureninger (60% reduktion)
  - V2: 134.636 → **121.984 lokaliteter** med aktive forureninger (9% reduktion)
  - Eliminerer lokaliteter uden dokumenterede forureningsstoffer
- **Endelig analyse**: **16.934 unikke lokaliteter** med både aktive forureninger og vandløbskontakt
- **Risikovurdering**: **3.606 højrisiko-lokaliteter** inden for 500m af vandløb
- **Output**: Præcise afstande til vandløb med komplet forureningsinformation til risikovurdering

**Fordele ved denne metode**:
- Fokuserer kun på relevante risikolokaliteter (med dokumenterede aktive forureninger)
- Eliminerer "støj" fra lokaliteter uden forureningspotentiale
- Bevarer vigtige attributter til risikovurdering
- Beregner præcise afstande inden for samme GVFK
- Identificerer minimale afstande per lokalitet for risikoprioritering
- Kvantificerer risiko baseret på afstand og forureningskarakteristika 