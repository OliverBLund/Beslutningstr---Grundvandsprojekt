"""Quick test for combined map generation."""
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import get_output_path
from Kode.tilstandsvurdering.step6_combined_map import create_combined_impact_maps

# Load data
site_flux = pd.read_csv(get_output_path("step6_flux_site_segment"), encoding='utf-8')
segment_summary = pd.read_csv(get_output_path("step6_segment_summary"), encoding='utf-8')

print(f"Loaded {len(site_flux)} site flux rows")
print(f"Loaded {len(segment_summary)} segment summary rows")

# Generate maps
create_combined_impact_maps(site_flux, segment_summary)
print("\nDone!")
