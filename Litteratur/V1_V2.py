# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import pandas as pd

# Indlæs CSV-filen
df = pd.read_csv("dkjord-View_Lokaliteter - Kopi.csv", sep=';')

# Fjern specifikke kolonner (fx 'kolonne1', 'kolonne2')
df_cleaned = df.drop(columns=['lokalitetensforureningsflader', 'Id', 'Lokalitetsejerlavkode','Lokalitetsmatrikler','GUID'])

# Split 'Lokalitetensstoffer' column by semicolon and expand into new rows
df_expanded = df_cleaned.assign(Lokalitetensstoffer=df['Lokalitetensstoffer'].str.split(';')).explode('Lokalitetensstoffer')


# Fjern dubletter baseret på alle kolonner (kan også specificere kolonner, fx subset=['kolonne1', 'kolonne2'])
df_unique = df_expanded.drop_duplicates()

# Tæl unikke værdier i 'Lokalitetsnr'-kolonnen
unique_count = df_unique['Lokalitetsnr'].nunique()

# Print antallet af unikke værdier
print(f"Antal unikke værdier i kolonnen 'Lokalitsnr': {unique_count}")

# Gem den nye tabel til en ny CSV-fil
df_unique.to_csv("expanded_lokaliteter.csv", index=False)


# Fjern dubletter baseret på alle kolonner (kan også specificere kolonner, fx subset=['kolonne1', 'kolonne2'])
df_uniquelokalitet = df_unique.drop_duplicates(subset=['Lokalitetsnr'])

# Tæl antallet af forekomster af hver unik værdi i kolonnen 'Lokalitsforureningstatus'
value_counts = df_uniquelokalitet['Lokalitetetsforureningsstatus'].value_counts()

# Print resultatet
print(value_counts)

#Join informationer til V2 grunde i .shp filen

df2 = pd.read_csv("V2_gvfk.csv", sep=';')


# Udfør et mange-til-mange join på 'nøglekolonne'
df_joined = pd.merge(df2, df_unique, left_on='Lokalitets', right_on='Lokalitetsnr', how='inner')


# Fjern specifikke kolonner (fx 'kolonne1', 'kolonne2')
V2_gvfk = df_joined.drop(columns=['OID_', 'Shape_Length', 'Shape_Area','Lokalitete','Lokalitets','Lokalite_1','Regionsnav','SenesteInd'])

# Gem den nye tabel til en ny CSV-fil
V2_gvfk.to_csv("v2_gvfk_forurening.csv", index=False)

# Fjern dubletter baseret på alle kolonner (kan også specificere kolonner, fx subset=['kolonne1', 'kolonne2'])
df_uniquelokalitetv2 = df_joined.drop_duplicates(subset=['Lokalitetsnr'])

# Tæl antallet af forekomster af hver unik værdi i kolonnen 'Lokalitsforureningstatus'
value_countsV2 = df_uniquelokalitetv2['Lokalitetetsforureningsstatus'].value_counts()

#Det samme for alle V1 Grunde

df3 = pd.read_csv("V1_gvfk.csv", sep=';')


# Udfør et mange-til-mange join på 'nøglekolonne'
df_joined2 = pd.merge(df3, df_unique, left_on='Lokalitets', right_on='Lokalitetsnr', how='inner')


# Fjern specifikke kolonner (fx 'kolonne1', 'kolonne2')
V1_gvfk = df_joined2.drop(columns=['OID_', 'Shape_Length', 'Shape_Area','Lokalitete','Lokalitets','Lokalite_1','Regionsnav','SenesteInd'])

# Gem den nye tabel til en ny CSV-fil
V1_gvfk.to_csv("v1_gvfk_forurening.csv", index=False)

# Fjern dubletter baseret på alle kolonner (kan også specificere kolonner, fx subset=['kolonne1', 'kolonne2'])
df_uniquelokalitetv1 = df_joined2.drop_duplicates(subset=['Lokalitetsnr'])

# Tæl antallet af forekomster af hver unik værdi i kolonnen 'Lokalitsforureningstatus'
value_countsV1 = df_uniquelokalitetv1['Lokalitetetsforureningsstatus'].value_counts()