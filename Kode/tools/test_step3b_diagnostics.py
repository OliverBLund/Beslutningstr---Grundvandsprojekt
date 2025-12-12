"""
Quick test script to run Step 3b and see diagnostic output
"""
import sys
sys.path.insert(0, '.')

from risikovurdering.step3_v1v2_sites import run_step3
from risikovurdering.step2_river_contact import run_step2
from risikovurdering.step3b_infiltration_filter import run_step3b

print("="*80)
print("TESTING STEP 3B DIAGNOSTIC OUTPUT")
print("="*80)

# Run Step 2 to get river GVFKs
rivers_gvfk, _, _ = run_step2()

# Run Step 3 to get sites
_, v1v2_sites = run_step3(rivers_gvfk)

# Run Step 3b with diagnostics
print("\nRunning Step 3b with diagnostic logging...\n")
filtered_sites = run_step3b(v1v2_sites, verbose=True)

print(f"\n\nFinal result: {len(filtered_sites):,} site-GVFK combinations after filtering")
