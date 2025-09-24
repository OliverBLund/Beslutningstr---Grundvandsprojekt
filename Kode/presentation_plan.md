# Presentation Plan: V1/V2 Groundwater Contamination Risk Assessment

## Overview
**Project**: "Decision Tree for Groundwater Impact on Surface Water"
**Focus**: Risk Assessment Phase (Steps 1-5) with Landfill Override Innovation
**Target**: 15-20 slides for technical presentation

---

## Slide Structure

### **1. Introduction & Project Context (2-3 slides)**

**Slide 1: Project Overview**
- Project title: "Decision Tree for Groundwater Impact on Surface Water"
- Collaboration: DTU Environment, GEUS, Danish EPA
- Objective: Systematic nationwide screening for contamination risk
- Focus: **Risk Assessment Phase** (Steps 1-5) completed

**Slide 2: Methodology Overview**
- Visual: Flow diagram showing 5-step workflow
- Two-phase approach: Risk Assessment → Future State Assessment
- Automated, scalable methodology for nationwide application

### **2. Data Foundation (1 slide)**

**Slide 3: Data Sources**
- 2,043 Danish groundwater bodies (GVFK)
- 44,509 V1/V2 contaminated sites from DK-jord database
- River network with groundwater contact mapping
- Literature-based compound mobility thresholds

### **3. Step-by-Step Results (5 slides)**

**Slide 4: Step 1 - Baseline Establishment**
- Total: 2,043 groundwater bodies in Denmark
- Visual: Map of all Danish GVFK

**Slide 5: Step 2 - River Contact Identification**
- Filtering: 2,043 → 593 GVFK with river contact (29.0%)
- Visual: Map showing GVFK with/without river contact
- Key insight: Only relevant for contamination transport

**Slide 6: Step 3 - Contaminated Sites Location**
- Input: 219,237 total site records → 35,728 unique sites with active contamination
- In relevant GVFK: 35,728 sites across 491 GVFK (82.8% of river-contact GVFK)
- Visual: Bar chart showing V1 vs V2 vs Both distribution

**Slide 7: Step 4 - Distance Analysis**
- Distance calculation: 35,728 sites → 69,627 site-GVFK combinations
- Results: Average 3,116m, Median 1,368m to nearest river
- Visual: Distance distribution histogram + map showing closest distances

**Slide 8: Step 5 Overview - Risk Thresholds**
- Two-tier assessment approach:
  - General screening: Universal 500m threshold
  - Compound-specific: Literature-based category thresholds
- Visual: Table showing all compound categories and thresholds

### **4. Key Innovation: Landfill Override System (3-4 slides)**

**Slide 9: Landfill Override Concept**
- Problem: Landfill sites need compound-specific stricter thresholds
- Solution: Two-phase classification system
- Visual: Flowchart showing normal → landfill override workflow

**Slide 10: Landfill Threshold Comparison**
- Visual: **NEW** - Comparison table/chart showing:
  - Normal thresholds vs Landfill-specific thresholds
  - Representative compounds for each category
  - Override status (stricter/looser/none)

**Slide 11: Landfill Override Results**
- 705 combinations reclassified to LOSSEPLADS categories
- 367 combinations removed (failed stricter thresholds)
- Visual: **NEW** - Before/after category distribution chart

**Slide 12: Landfill Override Impact by Category**
- Breakdown by compound category:
  - UORGANISKE_FORBINDELSER: 299 overrides (50m threshold)
  - BTXER: 191 overrides (70m threshold)
  - PESTICIDER: 114 overrides (180m MCPP threshold)
  - KLOREREDE_OPLØSNINGSMIDLER: 63 overrides (100m threshold)
  - PHENOLER: 38 overrides (35m threshold)
- Visual: **NEW** - Horizontal bar chart showing override counts

### **5. Final Results & Impact (3-4 slides)**

**Slide 13: Overall Results Summary**
- General Assessment: 4,156 high-risk sites (500m threshold)
- Compound-Specific: 2,013 high-risk sites (4,235 combinations)
- Geographic impact: 232 affected GVFK (11.4% of all Danish GVFK)
- Visual: **NEW** - Summary infographic with key numbers

**Slide 14: Geographic Distribution**
- **NEW**: Map showing:
  - All GVFK in gray
  - River-contact GVFK in blue
  - High-risk GVFK in red/orange
  - Different intensities for number of high-risk sites

**Slide 15: Category Distribution Analysis**
- Final compound category breakdown with counts
- Multi-substance site statistics
- Visual: Pie chart + stacked bar showing category distribution

### **6. Research Validation & Quality Assurance (2-3 slides)**

**Slide 16: Method Validation**
- Comprehensive testing of landfill override logic
- Verification of threshold compliance (0 violations found)
- Multi-substance site handling validation
- Edge case testing completed

**Slide 17: Additional Research Insights**
- Compound categorization refinement (425 substances mapped)
- LOSSEPLADS category optimization (180m→100m, perkolat focus)
- Missing combinations analysis (367 correctly removed)

### **7. Conclusion & Next Steps (1-2 slides)**

**Slide 18: Project Impact & Future Work**
- Systematic risk identification: 2,013 priority sites identified
- Reduction: From 35,728 total sites → 2,013 high-priority (94% reduction)
- Next phase: Quantitative state assessment with GEUS
- Integration with DK-model for flux calculations

---

## Visualization Requirements

### **Existing Visualizations (from step5_visualizations.py):**
✅ Available:
1. Distance distribution histograms
2. Category distribution pie/bar charts
3. Multi-substance analysis charts
4. GVFK impact summaries

### **New Visualizations Needed:**
🆕 To Create:
1. **Workflow diagram** - 5-step process flow
2. **Landfill threshold comparison table/chart** - Normal vs landfill thresholds
3. **Geographic impact map** - GVFK status with high-risk overlay
4. **Landfill override impact chart** - Before/after category changes
5. **Summary infographic** - Key numbers and percentages
6. **Method validation summary** - Testing results overview

### **Design Standards:**
- **Color Palette**: Professional blue/amber/green scheme
- **Font**: Arial/DejaVu Sans, consistent sizing
- **Format**: High-resolution (300 DPI) for presentation
- **Style**: Clean, minimal, publication-ready
- **Branding**: DTU logo integration where appropriate

---

## Data Sources for Visualizations

### **Input Files:**
- `step5_compound_detailed_combinations.csv` - Final risk assessment results
- `step4_final_distances_for_risk_assessment.csv` - Distance analysis
- Various GVFK shapefiles from each step
- Landfill override statistics from Step 5 terminal output

### **Key Statistics to Visualize:**
- **Overall**: 2,043 → 593 → 491 → 232 GVFK (funnel analysis)
- **Sites**: 35,728 → 2,013 high-risk (94.4% reduction)
- **Landfill**: 705 overrides, 367 removals
- **Categories**: 9 compound categories with specific thresholds
- **Geographic**: 232 affected GVFK across Denmark

---

## Implementation Strategy

### **Phase 1: Code Cleanup**
1. Standardize `step5_visualizations.py` with professional styling
2. Clean up `selected_visualizations.py` for consistency
3. Create unified color palette and styling functions

### **Phase 2: New Visualizations**
1. Create presentation-specific visualization functions
2. Generate all required new plots
3. Ensure consistent formatting and high quality

### **Phase 3: Integration**
1. Test all visualizations for clarity and impact
2. Generate final presentation-ready image files
3. Create visualization index/catalog

---

## Success Metrics

### **Technical Quality:**
- All visualizations render at 300 DPI
- Consistent color scheme and typography
- Clear, readable labels and legends
- Professional appearance suitable for technical presentation

### **Content Coverage:**
- Complete workflow documentation (Steps 1-5)
- Landfill override innovation clearly explained
- Key results and impact quantified
- Method validation and quality assurance demonstrated

### **Presentation Impact:**
- Clear story progression from methodology to results
- Strong visual support for technical concepts
- Compelling demonstration of systematic approach
- Clear connection to practical environmental impact