"""
Report Generator for Groundwater Risk Assessment
================================================

Generates professional reports in two formats:
1. Clean terminal output (for quick review)
2. HTML report (for presentations/meetings)

Combines results from all workflow steps with focus on Step 5 risk assessment.
"""

import pandas as pd
import geopandas as gpd
import os
from datetime import datetime
from config import get_output_path, get_visualization_path
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium import plugins
import numpy as np
from .create_interactive_map import create_map

class ReportGenerator:
    """Generate professional reports from workflow results."""
    
    def __init__(self):
        """Initialize report generator and load data."""
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.data = {}
        self.stats = {}
        self._load_all_data()
        
    def _load_all_data(self):
        """Load all relevant data files from the workflow."""
        try:
            # Step 3 data - V1/V2 sites and GVFK polygons
            step3_sites_file = get_output_path('step3_v1v2_sites')
            if os.path.exists(step3_sites_file):
                self.data['step3_sites'] = gpd.read_file(step3_sites_file)
            
            step3_gvfks_file = get_output_path('step3_gvfk_polygons')
            if os.path.exists(step3_gvfks_file):
                self.data['step3_gvfks'] = gpd.read_file(step3_gvfks_file)
            
            # Step 4 data
            step4_file = get_output_path('step4_final_distances_for_risk_assessment')
            if os.path.exists(step4_file):
                self.data['step4'] = pd.read_csv(step4_file)
            
            # Step 5 general assessment
            general_file = get_output_path('step5_high_risk_sites')
            if os.path.exists(general_file):
                self.data['general'] = pd.read_csv(general_file)
            
            # Step 5 compound-specific
            compound_file = get_output_path('step5_compound_detailed_combinations')
            if os.path.exists(compound_file):
                self.data['compound'] = pd.read_csv(compound_file)
            
            # Calculate key statistics
            self._calculate_statistics()
            
        except Exception as e:
            print(f"Warning: Could not load all data files: {e}")
    
    def _calculate_statistics(self):
        """Calculate key statistics from loaded data."""
        # Step 3 statistics - count actual GVFKs with V1/V2 sites
        if 'step3_gvfks' in self.data:
            self.stats['step3_gvfk_count'] = len(self.data['step3_gvfks'])
        
        if 'step4' in self.data:
            self.stats['total_sites_analyzed'] = len(self.data['step4'])
        
        if 'general' in self.data:
            df = self.data['general']
            self.stats['general_sites'] = len(df)
            self.stats['general_gvfks'] = df['Closest_GVFK'].nunique() if 'Closest_GVFK' in df.columns else 0
            
        if 'compound' in self.data:
            df = self.data['compound']
            self.stats['compound_sites'] = df['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in df.columns else 0
            self.stats['compound_occurrences'] = len(df)
            self.stats['compound_gvfks'] = df['Closest_GVFK'].nunique() if 'Closest_GVFK' in df.columns else 0
            
            # Category breakdown
            if 'Qualifying_Category' in df.columns:
                category_counts = df['Qualifying_Category'].value_counts()
                self.stats['categories'] = category_counts.to_dict()
                
                # Sites per category
                category_sites = {}
                for cat in df['Qualifying_Category'].unique():
                    cat_data = df[df['Qualifying_Category'] == cat]
                    category_sites[cat] = cat_data['Lokalitet_ID'].nunique()
                self.stats['category_sites'] = category_sites
    
    def generate_terminal_report(self):
        """Generate clean, formatted terminal output."""
        print("\n" + "="*80)
        print(f"GROUNDWATER RISK ASSESSMENT - FINAL REPORT")
        print(f"Generated: {self.timestamp}")
        print("="*80)
        
        # Executive Summary
        print("\nðŸ“Š EXECUTIVE SUMMARY")
        print("-" * 40)
        print(f"STEP 4 | Sites with distances calculated: {self.stats.get('total_sites_analyzed', 'N/A'):,}")
        print(f"STEP 5a | High-risk sites (â‰¤500m): {self.stats.get('general_sites', 'N/A'):,}")
        print(f"STEP 5b | Compound-specific risk: {self.stats.get('compound_sites', 'N/A'):,}")
        
        # GVFK Cascade
        print("\nðŸ—ºï¸ GVFK FILTERING CASCADE BY WORKFLOW STEP")
        print("-" * 40)
        print(f"{'Step | Stage':<40} {'Count':<10} {'% of Total':<15}")
        print(f"{'â”€'*40} {'â”€'*10} {'â”€'*15}")
        # Get actual Step 3 count
        step3_count = self.stats.get('step3_gvfk_count', 490)  # fallback updated for branch-only site inclusion
        step3_percentage = step3_count / 2043 * 100
        
        print(f"{'STEP 1 | Total GVFKs in Denmark':<40} {'2,043':<10} {'100.0%':<15}")
        print(f"{'STEP 2 | With river contact':<40} {'593':<10} {'29.0%':<15}")
        print(f"{'STEP 3 | With V1/V2 sites + contact':<40} {f'{step3_count:,}':<10} {f'{step3_percentage:.1f}%':<15}")
        
        general_gvfks = self.stats.get('general_gvfks', 0)
        compound_gvfks = self.stats.get('compound_gvfks', 0)
        
        if general_gvfks > 0:
            print(f"{'STEP 5a | General assessment (500m)':<40} {general_gvfks:<10} {f'{general_gvfks/2043*100:.1f}%':<15}")
        if compound_gvfks > 0:
            print(f"{'STEP 5b | Compound-specific risk':<40} {compound_gvfks:<10} {f'{compound_gvfks/2043*100:.1f}%':<15}")
        
        # Compound Category Analysis
        if 'categories' in self.stats:
            print("\nðŸ§ª STEP 5b: COMPOUND CATEGORY BREAKDOWN")
            print("-" * 40)
            print(f"{'Category':<25} {'Occurrences':<15} {'Unique Sites':<15}")
            print(f"{'â”€'*25} {'â”€'*15} {'â”€'*15}")
            
            categories = self.stats['categories']
            category_sites = self.stats.get('category_sites', {})
            
            # Sort by occurrences
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            
            for cat, count in sorted_cats[:8]:  # Top 8
                sites = category_sites.get(cat, 0)
                print(f"{cat:<25} {count:<15,} {sites:<15,}")
            
            # Summary
            total_occur = sum(categories.values())
            total_sites = self.stats.get('compound_sites', 0)
            if total_sites > 0:
                avg_per_site = total_occur / total_sites
                print(f"\n{'TOTAL':<25} {total_occur:<15,} {total_sites:<15,}")
                print(f"Average substances/site: {avg_per_site:.1f}")
        
        # Key Findings
        print("\nâœ… KEY FINDINGS")
        print("-" * 40)
        
        if 'general_sites' in self.stats and 'compound_sites' in self.stats:
            reduction = self.stats['general_sites'] - self.stats['compound_sites']
            reduction_pct = (reduction / self.stats['general_sites']) * 100
            print(f"â€¢ {reduction:,} sites ({reduction_pct:.1f}%) excluded by compound-specific thresholds")
        
        if 'categories' in self.stats:
            top_cat = sorted_cats[0] if sorted_cats else ('Unknown', 0)
            print(f"â€¢ Most common category: {top_cat[0]} ({top_cat[1]:,} occurrences)")
        
        print(f"â€¢ Analysis complete with {len(self.stats.get('categories', {})):,} active categories")
        
        print("\n" + "="*80)
        print("END OF REPORT")
        print("="*80)
    
    def generate_html_report(self, output_path=None):
        """Generate professional HTML report for presentations."""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(get_output_path('workflow_summary')), 'risk_assessment_report.html')
        
        # Get Step 3 variables for HTML
        step3_count = self.stats.get('step3_gvfk_count', 490)  # fallback updated for branch-only site inclusion
        step3_percentage = step3_count / 2043 * 100
        
        html_content = f"""
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Groundwater Risk Assessment Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .timestamp {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            border-left: 5px solid #1e3c72;
        }}
        
        h2 {{
            color: #1e3c72;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #1e3c72;
            display: block;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: #1e3c72;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        .cascade-table {{
            margin-top: 20px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }}
        
        .key-findings {{
            background: #e8f5e9;
            border-left: 5px solid #4CAF50;
            padding: 20px;
            margin-top: 20px;
            border-radius: 8px;
        }}
        
        .key-findings ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .key-findings li {{
            padding: 8px 0;
            padding-left: 30px;
            position: relative;
        }}
        
        .key-findings li:before {{
            content: "âœ“";
            position: absolute;
            left: 0;
            color: #4CAF50;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ðŸ”¬ Groundwater Risk Assessment Report</h1>
            <div class="timestamp">Generated: {self.timestamp}</div>
        </header>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2>ðŸ“Š Executive Summary - Workflow Results</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('total_sites_analyzed', 0):,}</span>
                        <span class="stat-label">STEP 4<br>Sites with Distances</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('general_sites', 0):,}</span>
                        <span class="stat-label">STEP 5a<br>General Risk (â‰¤500m)</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('compound_sites', 0):,}</span>
                        <span class="stat-label">STEP 5b<br>Compound-Specific</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('compound_gvfks', 0):,}</span>
                        <span class="stat-label">STEP 5b<br>GVFKs at Risk</span>
                    </div>
                </div>
            </div>
            
            <!-- GVFK Cascade -->
            <div class="section">
                <h2>ðŸ—ºï¸ GVFK Filtering Cascade by Workflow Step</h2>
                <table class="cascade-table">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Description</th>
                            <th>Count</th>
                            <th>% of Total</th>
                            <th>Visual Progress</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>STEP 1</strong></td>
                            <td>Total GVFKs in Denmark (baseline)</td>
                            <td><strong>2,043</strong></td>
                            <td>100.0%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 100%">100%</div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>STEP 2</strong></td>
                            <td>GVFKs with river contact</td>
                            <td><strong>593</strong></td>
                            <td>29.0%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 29%">29%</div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>STEP 3</strong></td>
                            <td>GVFKs with V1/V2 sites + river contact</td>
                            <td><strong>{step3_count:,}</strong></td>
                            <td>{step3_percentage:.1f}%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {step3_percentage:.1f}%">{step3_percentage:.0f}%</div>
                                </div>
                            </td>
                        </tr>
"""
        
        # Add dynamic GVFK rows
        if self.stats.get('general_gvfks', 0) > 0:
            pct = self.stats['general_gvfks'] / 2043 * 100
            html_content += f"""
                        <tr>
                            <td><strong>STEP 5a</strong></td>
                            <td>GVFKs with sites â‰¤500m from river</td>
                            <td><strong>{self.stats['general_gvfks']:,}</strong></td>
                            <td>{pct:.1f}%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {pct:.1f}%">{pct:.0f}%</div>
                                </div>
                            </td>
                        </tr>
"""
        
        if self.stats.get('compound_gvfks', 0) > 0:
            pct = self.stats['compound_gvfks'] / 2043 * 100
            html_content += f"""
                        <tr>
                            <td><strong>STEP 5b</strong></td>
                            <td>GVFKs with compound-specific risk</td>
                            <td><strong>{self.stats['compound_gvfks']:,}</strong></td>
                            <td>{pct:.1f}%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {pct:.1f}%; background: linear-gradient(90deg, #FF5722, #FF9800);">{pct:.0f}%</div>
                                </div>
                            </td>
                        </tr>
"""
        
        html_content += """
                    </tbody>
                </table>
                <p style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 4px;">
                    <strong>Note on Step 4:</strong> Step 4 calculates distances from each of the 35,728 V1/V2 sites (from Step 3) to the nearest river segment with groundwater contact. 
                    This step doesn't filter GVFKs but provides the distance measurements needed for Step 5's risk assessment.
                </p>
            </div>
"""
        
        # Category breakdown
        if 'categories' in self.stats:
            html_content += """
            <!-- Compound Categories -->
            <div class="section">
                <h2>ðŸ§ª STEP 5b: Compound Category Analysis</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Threshold (m)</th>
                            <th>Occurrences</th>
                            <th>Unique Sites</th>
                            <th>Avg/Site</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            
            # Add threshold mapping
            thresholds = {
                'KLOREREDE_OPLÃ˜SNINGSMIDLER': 30,
                'BTXER': 50,  # Note: Benzen uses 200m threshold
                'PAH_FORBINDELSER': 200,
                'ANDRE': 500,
                'LOSSEPLADS': 500,
                # Legacy categories for compatibility
                'PAHER': 30,
                'PHENOLER': 100,
                'UORGANISKE_FORBINDELSER': 150,
                'POLARE': 300,
                'CHLORINATED_SOLVENTS': 500,
                'PESTICIDER': 500,
                'OTHER': 500
            }
            
            categories = self.stats['categories']
            category_sites = self.stats.get('category_sites', {})
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            
            for cat, count in sorted_cats[:8]:
                sites = category_sites.get(cat, 0)
                avg = count / sites if sites > 0 else 0
                threshold = thresholds.get(cat, 500)
                
                html_content += f"""
                        <tr>
                            <td><strong>{cat}</strong></td>
                            <td>{threshold}</td>
                            <td>{count:,}</td>
                            <td>{sites:,}</td>
                            <td>{avg:.1f}</td>
                        </tr>
"""
            
            html_content += """
                    </tbody>
                </table>
            </div>
"""
        
        # Key findings
        html_content += """
            <!-- Key Findings -->
            <div class="section">
                <h2>âœ… Key Findings</h2>
                <div class="key-findings">
                    <ul>
"""
        
        if 'general_sites' in self.stats and 'compound_sites' in self.stats:
            reduction = self.stats['general_sites'] - self.stats['compound_sites']
            reduction_pct = (reduction / self.stats['general_sites']) * 100
            html_content += f"""
                        <li>{reduction:,} sites ({reduction_pct:.1f}%) excluded by compound-specific thresholds</li>
"""
        
        if 'categories' in self.stats and sorted_cats:
            top_cat = sorted_cats[0]
            html_content += f"""
                        <li>Most common category: {top_cat[0]} ({top_cat[1]:,} occurrences)</li>
"""
        
        if 'compound_occurrences' in self.stats and 'compound_sites' in self.stats:
            avg = self.stats['compound_occurrences'] / self.stats['compound_sites']
            html_content += f"""
                        <li>Average substances per site: {avg:.1f}</li>
"""
        
        html_content += f"""
                        <li>Analysis complete with {len(self.stats.get('categories', {})):,} active categories</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>DTU MiljÃ¸ - Groundwater Risk Assessment Project</p>
            <p>Report generated by automated workflow analysis</p>
        </div>
    </div>
    
    {self._generate_step_by_step_sections()}
</body>
</html>
"""
        
        # Save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nâœ… HTML report generated: {output_path}")
        return output_path
    
    def _generate_step_by_step_sections(self):
        """Generate detailed step-by-step analysis sections with interactive plots."""
        sections = []
        
        # GVFK Progression Plot
        gvfk_plot = self._create_gvfk_progression_plot()
        
        # Step 3 Analysis
        step3_analysis = self._create_step3_analysis()
        
        # Step 4 Analysis
        step4_analysis = self._create_step4_analysis()
        
        # Step 5 Analysis
        step5_analysis = self._create_step5_analysis()
        
        return f"""
    <div style="background: white; margin-top: 40px; padding: 40px; border-top: 3px solid #1e3c72;">
        <h1 style="color: #1e3c72; text-align: center; margin-bottom: 40px; font-size: 2.2em;">ðŸ” Detailed Step-by-Step Analysis</h1>
        
        <!-- GVFK Progression Chart -->
        <div style="margin-bottom: 50px; background: #f8f9fa; padding: 30px; border-radius: 10px; border-left: 5px solid #1e3c72;">
            <h2 style="color: #1e3c72; margin-bottom: 20px; font-size: 1.8em;">ðŸ—ºï¸ GVFK Filtering Progression Through Workflow</h2>
            <p style="margin-bottom: 20px; color: #666;">Progressive reduction of Denmark's 2,043 groundwater bodies (GVFKs) through each workflow step.</p>
            {gvfk_plot}
        </div>
        
        <!-- Step 3 Analysis -->
        {step3_analysis}
        
        <!-- Step 4 Analysis -->
        {step4_analysis}
        
        <!-- Step 5 Analysis -->
        {step5_analysis}
    </div>
        """
    
    def _create_gvfk_progression_plot(self):
        """Create GVFK filtering progression visualization."""
        stages = ['Total GVFKs<br>(Denmark)', 'With River<br>Contact', 'With V1/V2<br>Sites', 'General Risk<br>(â‰¤500m)', 'Compound Risk<br>(Variable)']
        values = [2043, 593, self.stats.get('step3_gvfk_count', 432), 
                 self.stats.get('general_gvfks', 300), self.stats.get('compound_gvfks', 245)]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        fig = go.Figure(data=go.Bar(x=stages, y=values, marker_color=colors))
        fig.update_layout(
            title='GVFK Filtering Progression Through Workflow',
            xaxis_title='Workflow Stage',
            yaxis_title='Number of GVFKs',
            height=400,
            showlegend=False,
            font=dict(size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # Add percentage annotations
        for i, (stage, value) in enumerate(zip(stages, values)):
            if value > 0:  # Only add annotation if value exists
                pct = value / 2043 * 100
                fig.add_annotation(x=i, y=value + 20, text=f'{pct:.1f}%', 
                                 showarrow=False, font=dict(size=14, color='#1e3c72'))
        
        return fig.to_html(include_plotlyjs='cdn', div_id="gvfk_progression")
    
    def _create_step3_analysis(self):
        """Create Step 3 geographic filtering analysis."""
        # Get actual Step 3 data from loaded files
        step3_gvfks = len(self.data.get('step3_gvfks', []))
        step3_sites = self.data.get('step3_sites')
        
        # Get actual counts from Step 3 output
        if step3_sites is not None:
            total_sites = step3_sites['Lokalitet_'].nunique()  # Unique localities from Step 3
            total_combinations = len(step3_sites)  # Total site-GVFK combinations
        else:
            # Fallback to Step 4 data if Step 3 not available
            total_sites = len(self.data.get('step4', [])) if 'step4' in self.data else 35728
        
        # Create a simple flow chart showing the geographic filtering
        stages = ['Total V1/V2<br>Localities', 'In River-Contact<br>GVFKs']
        values = [40870, total_sites]  # From workflow output
        colors = ['#3498db', '#2ca02c']
        
        fig = go.Figure(data=go.Bar(x=stages, y=values, marker_color=colors))
        fig.update_layout(
            title='Step 3: Geographic Filtering by River-Contact GVFKs',
            xaxis_title='Filtering Stage',
            yaxis_title='Number of Sites',
            height=400,
            font=dict(size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # Add percentage annotation
        retention_pct = (total_sites / 40870) * 100 if 40870 > 0 else 0
        fig.add_annotation(x=1, y=total_sites + 1000, text=f'{retention_pct:.1f}% retained', 
                          showarrow=False, font=dict(size=14, color='#2ca02c'))
        
        geographic_chart = fig.to_html(include_plotlyjs='cdn', div_id="step3_geographic")
        
        return f"""
        <div style="margin-bottom: 50px; background: #f8f9fa; padding: 30px; border-radius: 10px; border-left: 5px solid #2ca02c;">
            <h2 style="color: #2ca02c; margin-bottom: 20px; font-size: 1.8em;">ðŸ“ Step 3: Geographic Filtering of V1/V2 Sites</h2>
            <p style="margin-bottom: 20px; color: #666;">
                Step 3 performs <strong>geographic filtering with enhanced site inclusion</strong>: it identifies V1/V2 contamination sites
                within GVFKs (groundwater bodies) that have river contact from Step 2. Sites are included if they have either documented
                substances OR branch/activity information, capturing more potentially risky sites than substance-only filtering.
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; align-items: center;">
                <div>
                    {geographic_chart}
                </div>
                <div>
                    <h3 style="color: #2ca02c; margin-bottom: 15px;">Geographic Filter Results</h3>
                    <ul style="color: #666; line-height: 1.8;">
                        <li><strong>Input:</strong> ~40,870 unique localities from V1+V2 datasets</li>
                        <li><strong>Geographic Filter:</strong> Keep only sites in river-contact GVFKs</li>
                        <li><strong>Output:</strong> {total_sites:,} unique localities in {step3_gvfks} GVFKs with river contact</li>
                        {"<li><strong>Site-GVFK Combinations:</strong> " + f"{total_combinations:,} total relationships</li>" if step3_sites is not None else ""}
                        <li><strong>Retention Rate:</strong> {retention_pct:.1f}% of original localities</li>
                    </ul>
                    <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #2ca02c;">
                        <strong>Enhanced Methodology:</strong> Step 3 now includes sites with documented substances OR sites with only
                        branch/activity information (e.g., landfills, gas stations). This "substance OR branch" approach captures
                        more potentially risky sites than the previous substance-only method. Contamination-based thresholds are applied in Step 5.
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _create_step4_analysis(self):
        """Create Step 4 distance calculation analysis."""
        if 'step4' not in self.data:
            return f"""
            <div style="margin-bottom: 50px; background: #f8f9fa; padding: 30px; border-radius: 10px; border-left: 5px solid #ff7f0e;">
                <h2 style="color: #ff7f0e; margin-bottom: 20px; font-size: 1.8em;">ðŸ“ Step 4: Distance Calculation</h2>
                <p style="color: #666;">Step 4 data not available for detailed analysis.</p>
            </div>
            """
        
        df = self.data['step4']
        
        # Create basic distance histogram without risk thresholds
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=df['Final_Distance_m'], nbinsx=50, name='All Sites', 
                                   marker_color='#ff7f0e', opacity=0.7))
        
        fig.update_layout(
            title='Distribution of Calculated Distances to Nearest River Segments',
            xaxis_title='Distance to Nearest River (meters)',
            yaxis_title='Number of Sites',
            height=400,
            font=dict(size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        distance_plot = fig.to_html(include_plotlyjs='cdn', div_id="step4_distance_histogram")
        
        # Create interactive map using existing functionality
        interactive_map = self._get_existing_interactive_map()
        
        # Create basic distance statistics (no risk interpretation)
        total_sites = len(df)
        valid_distances = df['Final_Distance_m'].dropna()
        sites_with_distances = len(valid_distances)
        median_dist = valid_distances.median() if len(valid_distances) > 0 else 0
        mean_dist = valid_distances.mean() if len(valid_distances) > 0 else 0
        min_dist = valid_distances.min() if len(valid_distances) > 0 else 0
        max_dist = valid_distances.max() if len(valid_distances) > 0 else 0
        
        return f"""
        <div style="margin-bottom: 50px; background: #f8f9fa; padding: 30px; border-radius: 10px; border-left: 5px solid #ff7f0e;">
            <h2 style="color: #ff7f0e; margin-bottom: 20px; font-size: 1.8em;">ðŸ“ Step 4: Distance Calculation</h2>
            <p style="margin-bottom: 20px; color: #666;">
                Step 4 calculates the minimum distance from each contamination site to the nearest river segment 
                within the same GVFK. These raw distance measurements provide the foundation for risk assessment in Step 5.
            </p>
            
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 30px;">
                <div>
                    {distance_plot}
                </div>
                <div>
                    <h3 style="color: #ff7f0e; margin-bottom: 15px;">Distance Calculation Results</h3>
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: bold; color: #ff7f0e;">Total Sites:</div>
                            <div style="font-size: 1.8em; color: #333;">{total_sites:,}</div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: bold; color: #ff7f0e;">With Valid Distances:</div>
                            <div style="font-size: 1.8em; color: #333;">{sites_with_distances:,}</div>
                            <div style="font-size: 0.9em; color: #666;">({sites_with_distances/total_sites*100:.1f}% success rate)</div>
                        </div>
                        <hr style="margin: 15px 0;">
                        <div style="margin-bottom: 10px;">
                            <strong>Minimum Distance:</strong> {min_dist:.0f}m
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Median Distance:</strong> {median_dist:.0f}m
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Mean Distance:</strong> {mean_dist:.0f}m
                        </div>
                        <div>
                            <strong>Maximum Distance:</strong> {max_dist:.0f}m
                        </div>
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #2196F3;">
                        <strong>Step 4 Purpose:</strong> This step only calculates distances. No risk thresholds or 
                        contamination filtering is applied. Risk assessment using these distances occurs in Step 5.
                    </div>
                </div>
            </div>
            
            <h3 style="color: #ff7f0e; margin-bottom: 15px; font-size: 1.4em;">ðŸ—ºï¸ Interactive Distance Visualization Map</h3>
            <p style="color: #666; margin-bottom: 15px;">
                Interactive map showing calculated distances between contamination sites and river segments.
                Red lines indicate the minimum distance per site used for risk assessment.
            </p>
            {interactive_map}
        </div>
        """
    
    def _create_step5_analysis(self):
        """Create Step 5 risk assessment analysis."""
        step5a_section = self._create_step5a_section()
        step5b_section = self._create_step5b_section()
        
        return f"""
        <div style="margin-bottom: 50px; background: #f8f9fa; padding: 30px; border-radius: 10px; border-left: 5px solid #d62728;">
            <h2 style="color: #d62728; margin-bottom: 20px; font-size: 1.8em;">âš ï¸ Step 5: Risk Assessment</h2>
            <p style="margin-bottom: 30px; color: #666;">
                Two complementary approaches to groundwater contamination risk assessment:
                <strong>General Assessment</strong> (conservative 500m universal threshold) and 
                <strong>Compound-Specific Assessment</strong> (literature-based variable thresholds by contamination type).
            </p>
            
            {step5a_section}
            {step5b_section}
        </div>
        """
    
    def _create_step5a_section(self):
        """Create Step 5a general assessment section."""
        general_sites = self.stats.get('general_sites', 0)
        general_gvfks = self.stats.get('general_gvfks', 0)
        
        return f"""
        <div style="background: white; padding: 25px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #d62728; margin-bottom: 15px; font-size: 1.5em;">ðŸš¨ Step 5a: General Risk Assessment (500m Universal Threshold)</h3>
            <p style="color: #666; margin-bottom: 20px;">
                Conservative approach: ALL sites within 500 meters of river stretches are considered high-risk, 
                regardless of contamination type.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                <div style="text-align: center; background: #fff5f5; padding: 20px; border-radius: 8px; border: 2px solid #d62728;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #d62728;">{general_sites:,}</div>
                    <div style="color: #666;">High-Risk Sites</div>
                </div>
                <div style="text-align: center; background: #fff5f5; padding: 20px; border-radius: 8px; border: 2px solid #d62728;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #d62728;">{general_gvfks:,}</div>
                    <div style="color: #666;">GVFKs at Risk</div>
                </div>
                <div style="text-align: center; background: #fff5f5; padding: 20px; border-radius: 8px; border: 2px solid #d62728;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #d62728;">500m</div>
                    <div style="color: #666;">Universal Threshold</div>
                </div>
            </div>
            
            <div style="background: #f8d7da; padding: 15px; border-radius: 8px; border-left: 4px solid #d62728;">
                <strong>Conservative Approach:</strong> This method assumes all contamination types have equal mobility 
                and provides the most precautionary risk assessment.
            </div>
        </div>
        """
    
    def _create_step5b_section(self):
        """Create Step 5b compound-specific assessment section."""
        if 'compound' not in self.data:
            return """
            <div style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="color: #9467bd; margin-bottom: 15px; font-size: 1.5em;">ðŸ§ª Step 5b: Compound-Specific Assessment</h3>
                <p style="color: #666;">Compound-specific data not available for detailed analysis.</p>
            </div>
            """
        
        df = self.data['compound']
        compound_sites = self.stats.get('compound_sites', 0)
        compound_gvfks = self.stats.get('compound_gvfks', 0)
        compound_occurrences = self.stats.get('compound_occurrences', 0)
        
        # Create category distribution chart
        category_counts = df['Qualifying_Category'].value_counts()
        
        fig1 = go.Figure(data=go.Bar(
            y=category_counts.index[:8],  # Top 8 categories
            x=category_counts.values[:8],
            orientation='h',
            marker_color='#9467bd',
            opacity=0.8
        ))
        
        fig1.update_layout(
            title='Top 8 Compound Categories by Occurrences',
            xaxis_title='Number of Occurrences',
            yaxis_title='Category',
            height=400,
            font=dict(size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        category_plot = fig1.to_html(include_plotlyjs='cdn', div_id="compound_categories")
        
        # Create sites per category chart
        category_sites_data = df.groupby('Qualifying_Category')['Lokalitet_ID'].nunique().sort_values(ascending=True)
        
        fig2 = go.Figure(data=go.Bar(
            x=category_sites_data.values[-8:],  # Top 8
            y=category_sites_data.index[-8:],
            orientation='h',
            marker_color='lightgreen',
            opacity=0.8
        ))
        
        fig2.update_layout(
            title='Top 8 Categories by Unique Sites',
            xaxis_title='Number of Unique Sites',
            yaxis_title='Category',
            height=400,
            font=dict(size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        sites_plot = fig2.to_html(include_plotlyjs='cdn', div_id="category_sites")
        
        return f"""
        <div style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #9467bd; margin-bottom: 15px; font-size: 1.5em;">ðŸ§ª Step 5b: Compound-Specific Risk Assessment</h3>
            <p style="color: #666; margin-bottom: 20px;">
                Literature-based approach using variable distance thresholds tailored to different contamination categories.
                Categories range from highly mobile compounds (30m threshold) to less mobile substances (500m threshold).
                <strong>Special case:</strong> Benzen within BTEX category uses 200m threshold instead of the standard 50m BTEX threshold.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                <div style="text-align: center; background: #f8f3ff; padding: 20px; border-radius: 8px; border: 2px solid #9467bd;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #9467bd;">{compound_sites:,}</div>
                    <div style="color: #666;">Unique Sites at Risk</div>
                </div>
                <div style="text-align: center; background: #f8f3ff; padding: 20px; border-radius: 8px; border: 2px solid #9467bd;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #9467bd;">{compound_occurrences:,}</div>
                    <div style="color: #666;">Total Occurrences</div>
                </div>
                <div style="text-align: center; background: #f8f3ff; padding: 20px; border-radius: 8px; border: 2px solid #9467bd;">
                    <div style="font-size: 2.2em; font-weight: bold; color: #9467bd;">{compound_occurrences/compound_sites:.1f}</div>
                    <div style="color: #666;">Avg Substances/Site</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px;">
                <div>
                    {category_plot}
                </div>
                <div>
                    {sites_plot}
                </div>
            </div>
            
            <div style="background: #e7e3ff; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #9467bd;">
                <strong>Refined Assessment:</strong> This approach excludes {self.stats.get('general_sites', 0) - compound_sites:,} sites 
                ({(self.stats.get('general_sites', 1) - compound_sites) / self.stats.get('general_sites', 1) * 100:.1f}%) that pose lower risk based on contaminant mobility characteristics.
            </div>
        </div>
        """
    
    def _get_existing_interactive_map(self):
        """Get or reference the existing interactive map from create_interactive_map.py"""
        # Check if the interactive map already exists
        map_path = get_output_path('interactive_distance_map')
        
        if os.path.exists(map_path):
            # Get relative path for embedding
            map_filename = os.path.basename(map_path)
            
            return f"""
            <div style="width: 100%; height: 600px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <iframe src="{map_filename}" style="width: 100%; height: 100%; border: none;" 
                        title="Interactive Distance Map"></iframe>
            </div>
            <div style="margin-top: 10px; padding: 15px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196F3;">
                <strong>Interactive Map Features:</strong> 
                â€¢ Click on site markers for detailed information 
                â€¢ Red lines show minimum distances (critical for risk assessment)
                â€¢ Orange lines show additional pathways through different GVFKs
                â€¢ Map shows ~1,000 representative sites across Denmark
            </div>
            """
        else:
            # Map doesn't exist - provide instructions
            return f"""
            <div style="height: 400px; border: 2px dashed #ccc; display: flex; align-items: center; justify-content: center; background: #f9f9f9; border-radius: 8px;">
                <div style="text-align: center; color: #666;">
                    <h4 style="color: #ff7f0e; margin-bottom: 15px;">ðŸ“ Interactive Map Available</h4>
                    <p>The interactive distance map is generated separately by the workflow.</p>
                    <p><strong>To view the map:</strong> Run the complete workflow to generate<br>
                    <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{map_path}</code></p>
                    <p><em>The map shows site locations, distances to rivers, and GVFK boundaries<br>
                    with interactive markers and distance lines.</em></p>
                </div>
            </div>
            """

def generate_reports():
    """Main function to generate all reports."""
    print("\nGenerating professional reports...")
    
    generator = ReportGenerator()
    
    # Generate terminal report
    generator.generate_terminal_report()
    
    # Generate HTML report
    html_path = generator.generate_html_report()
    
    print(f"\nReports generated successfully!")
    print(f"HTML report can be opened in browser: {html_path}")
    
    return generator

if __name__ == "__main__":
    generate_reports()
