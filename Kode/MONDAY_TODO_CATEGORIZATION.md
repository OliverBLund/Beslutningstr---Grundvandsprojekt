# MONDAY TODO: Fix Modelstof Categorization

**Date Identified:** 2025-11-07  
**Priority:** HIGH - Affects both Step 5 and Step 6

---

## ISSUE: Delprojekt 3 Modelstoffer Are Miscategorized

The 16 modelstoffer from Delprojekt 3 are being split across different categories in Step 5, which doesn't align with the intended grouping.

### Current Categorization (Step 5):

| Modelstof | Should Be In | Currently In | Status |
|-----------|--------------|--------------|--------|
| Benzen | BTXER | BTXER | ✓ OK |
| Olie C10-C25 | BTXER | BTXER | ✓ OK |
| 1,1,1-Trichlorethan | KLOREREDE_OPLØSNINGSMIDLER | KLOREREDE_OPLØSNINGSMIDLER | ✓ OK |
| Trichlorethylen (TCE) | KLOREREDE_OPLØSNINGSMIDLER | KLOREREDE_OPLØSNINGSMIDLER | ✓ OK |
| **Chloroform** | KLOREREDE_OPLØSNINGSMIDLER | **KLOREDE_KULBRINTER** | ✗ WRONG |
| **Chlorbenzen** | ??? | **BTXER** | ✗ WRONG? |

### Root Cause:

**File:** `Kode/risikovurdering/refined_compound_analysis.py`

**KLOREREDE_OPLØSNINGSMIDLER keywords:**
```python
'keywords': ['1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor', 'tetrachlor',
            'vinylchlorid', 'dichlorethylen', 'dichlorethan', 'chlorerede', 'opl.midl', 'opløsningsmidl',
            'cis-1,2-dichlorethyl', 'trans-1,2-dichloreth', 'chlorethan']
```
**Missing:** 'chloroform'

**KLOREDE_KULBRINTER keywords:**
```python
'keywords': ['chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform', 'dibromethane', 'bromerede']
```
**Has:** 'chloroform' ← This causes Chloroform to be categorized here instead

**BTXER keywords:**
```python
'keywords': ['btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', ...]
```
**Has:** 'benzen' ← This catches "Chlorbenzen" because it contains "benzen"

---

## DECISIONS NEEDED:

### 1. Chloroform
**Question:** Should Chloroform be in KLOREREDE_OPLØSNINGSMIDLER or KLOREDE_KULBRINTER?

**Option A:** Move to KLOREREDE_OPLØSNINGSMIDLER (align with Delprojekt 3)
- Add 'chloroform' to KLOREREDE_OPLØSNINGSMIDLER keywords
- Remove 'chloroform' from KLOREDE_KULBRINTER (or make sure precedence works)

**Option B:** Keep in KLOREDE_KULBRINTER (different distance: 200m vs 500m)
- Acknowledge it as separate category
- Update Step 6 scenarios accordingly

### 2. Chlorbenzen
**Question:** What category should it be in?

**Current:** BTXER (caught by 'benzen' keyword)

**Options:**
- Create new category: "KLOREREDE_AROMATER" or "ANDRE_AROMATISKE"
- Keep in BTXER (it IS aromatic, but chlorinated)
- Move to KLOREREDE_OPLØSNINGSMIDLER (it's chlorinated)

### 3. Impact on Step 6

Currently Step 6 has:
```python
CATEGORY_SCENARIOS = {
    "KLOREREDE_OPLØSNINGSMIDLER": ["1,1,1-Trichlorethan", "Trichlorethylen", "Chloroform", "Chlorbenzen"],
    "KLOREDE_KULBRINTER": ["1,1,1-Trichlorethan", "Trichlorethylen", "Chloroform", "Chlorbenzen"],
}
```

**But actual data shows:**
- KLOREREDE_OPLØSNINGSMIDLER: Only has TCE and 1,1,1-TCA
- KLOREDE_KULBRINTER: Has Chloroform (29 occurrences)
- BTXER: Has Chlorbenzen (2 occurrences)

**Need to align scenarios with actual categories!**

---

## RECOMMENDED ACTION PLAN:

1. **Monday morning:** Review Delprojekt 3 documentation
   - Confirm which 16 modelstoffer belong to which groups
   - Confirm if Chlorbenzen is actually a modelstof or not

2. **Update `refined_compound_analysis.py`:**
   - Adjust keywords to match Delprojekt 3 grouping
   - Ensure proper precedence (specific matches before general)
   - Test with actual V1/V2 data

3. **Rerun Step 5:**
   - Generate new `step5_compound_detailed_combinations.csv`
   - Verify categories are correct

4. **Update Step 6 `CATEGORY_SCENARIOS`:**
   - Align with corrected Step 5 categories
   - Ensure each category only includes modelstoffer that actually appear in that category

5. **Rerun Step 6:**
   - Verify scenario generation works correctly
   - Check all modelstoffer are represented

---

## FILES TO MODIFY:

1. `Kode/risikovurdering/refined_compound_analysis.py` (Step 5 categorization)
2. `Kode/tilstandsvurdering/step6_tilstandsvurdering.py` (Step 6 scenarios)

---

## CURRENT WORKAROUND (Friday):

For now, Step 6 is configured to work with the **current** Step 5 output:
- Accepts whatever categories Step 5 produces
- Generates scenarios based on those categories
- System functions, but categories may not match intended Delprojekt 3 grouping

**This works but needs to be corrected Monday for scientific accuracy!**
