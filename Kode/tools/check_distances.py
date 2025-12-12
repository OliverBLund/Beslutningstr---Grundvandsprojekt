import pandas as pd
import sys
sys.path.insert(0, '.')
from config import get_output_path

df = pd.read_csv(get_output_path('step4_final_distances_for_risk_assessment'))

print(f'Site-GVFK combinations: {len(df):,}')
print(f'\nDistance_to_River_m stats (all site-GVFK combinations):')
print(f'  Mean: {df["Distance_to_River_m"].mean():.0f}m')
print(f'  Median: {df["Distance_to_River_m"].median():.0f}m')
print(f'  Min: {df["Distance_to_River_m"].min():.0f}m')
print(f'  Max: {df["Distance_to_River_m"].max():.0f}m')

# Also show per-site minimum distances
site_min = df.groupby('Lokalitet_ID')['Distance_to_River_m'].min()
print(f'\nPer-site minimum distance stats (what workflow reports):')
print(f'  Mean: {site_min.mean():.0f}m')
print(f'  Median: {site_min.median():.0f}m')
