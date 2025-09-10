"""
Report Generator for Groundwater Risk Assessment
================================================

Generates professional reports in two formats:
1. Clean terminal output (for quick review)
2. HTML report (for presentations/meetings)

Combines results from all workflow steps with focus on Step 5 risk assessment.
"""

import pandas as pd
import os
from datetime import datetime
from config import get_output_path, get_visualization_path

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
        print("\n📊 EXECUTIVE SUMMARY")
        print("-" * 40)
        print(f"STEP 4 | Sites with distances calculated: {self.stats.get('total_sites_analyzed', 'N/A'):,}")
        print(f"STEP 5a | High-risk sites (≤500m): {self.stats.get('general_sites', 'N/A'):,}")
        print(f"STEP 5b | Compound-specific risk: {self.stats.get('compound_sites', 'N/A'):,}")
        
        # GVFK Cascade
        print("\n🗺️ GVFK FILTERING CASCADE BY WORKFLOW STEP")
        print("-" * 40)
        print(f"{'Step | Stage':<40} {'Count':<10} {'% of Total':<15}")
        print(f"{'─'*40} {'─'*10} {'─'*15}")
        print(f"{'STEP 1 | Total GVFKs in Denmark':<40} {'2,043':<10} {'100.0%':<15}")
        print(f"{'STEP 2 | With river contact':<40} {'593':<10} {'29.0%':<15}")
        print(f"{'STEP 3 | With V1/V2 sites + contact':<40} {'432':<10} {'21.1%':<15}")
        
        general_gvfks = self.stats.get('general_gvfks', 0)
        compound_gvfks = self.stats.get('compound_gvfks', 0)
        
        if general_gvfks > 0:
            print(f"{'STEP 5a | General assessment (500m)':<40} {general_gvfks:<10} {f'{general_gvfks/2043*100:.1f}%':<15}")
        if compound_gvfks > 0:
            print(f"{'STEP 5b | Compound-specific risk':<40} {compound_gvfks:<10} {f'{compound_gvfks/2043*100:.1f}%':<15}")
        
        # Compound Category Analysis
        if 'categories' in self.stats:
            print("\n🧪 STEP 5b: COMPOUND CATEGORY BREAKDOWN")
            print("-" * 40)
            print(f"{'Category':<25} {'Occurrences':<15} {'Unique Sites':<15}")
            print(f"{'─'*25} {'─'*15} {'─'*15}")
            
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
        print("\n✅ KEY FINDINGS")
        print("-" * 40)
        
        if 'general_sites' in self.stats and 'compound_sites' in self.stats:
            reduction = self.stats['general_sites'] - self.stats['compound_sites']
            reduction_pct = (reduction / self.stats['general_sites']) * 100
            print(f"• {reduction:,} sites ({reduction_pct:.1f}%) excluded by compound-specific thresholds")
        
        if 'categories' in self.stats:
            top_cat = sorted_cats[0] if sorted_cats else ('Unknown', 0)
            print(f"• Most common category: {top_cat[0]} ({top_cat[1]:,} occurrences)")
        
        print(f"• Analysis complete with {len(self.stats.get('categories', {})):,} active categories")
        
        print("\n" + "="*80)
        print("END OF REPORT")
        print("="*80)
    
    def generate_html_report(self, output_path=None):
        """Generate professional HTML report for presentations."""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(get_output_path('workflow_summary')), 'risk_assessment_report.html')
        
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
            content: "✓";
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
            <h1>🔬 Groundwater Risk Assessment Report</h1>
            <div class="timestamp">Generated: {self.timestamp}</div>
        </header>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2>📊 Executive Summary - Workflow Results</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('total_sites_analyzed', 0):,}</span>
                        <span class="stat-label">STEP 4<br>Sites with Distances</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{self.stats.get('general_sites', 0):,}</span>
                        <span class="stat-label">STEP 5a<br>General Risk (≤500m)</span>
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
                <h2>🗺️ GVFK Filtering Cascade by Workflow Step</h2>
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
                            <td><strong>432</strong></td>
                            <td>21.1%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 21.1%">21%</div>
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
                            <td>GVFKs with sites ≤500m from river</td>
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
                    <strong>Note on Step 4:</strong> Step 4 calculates distances from each of the 16,934 V1/V2 sites (from Step 3) to the nearest river segment with groundwater contact. 
                    This step doesn't filter GVFKs but provides the distance measurements needed for Step 5's risk assessment.
                </p>
            </div>
"""
        
        # Category breakdown
        if 'categories' in self.stats:
            html_content += """
            <!-- Compound Categories -->
            <div class="section">
                <h2>🧪 STEP 5b: Compound Category Analysis</h2>
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
                'PAHER': 30,
                'BTXER': 50,
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
                <h2>✅ Key Findings</h2>
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
            <p>DTU Miljø - Groundwater Risk Assessment Project</p>
            <p>Report generated by automated workflow analysis</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ HTML report generated: {output_path}")
        return output_path

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