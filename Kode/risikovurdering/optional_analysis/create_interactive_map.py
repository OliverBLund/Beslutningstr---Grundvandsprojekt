"""
Interactive map creation for groundwater contamination distance analysis.

This module creates interactive folium maps showing GVFK polygons, V1/V2 sites,
river segments, and distance connections with minimum distances highlighted.
"""

import folium
import geopandas as gpd
import os
from shapely.ops import nearest_points
from config import get_output_path



def create_map(v1v2_with_distances, rivers_with_contact, valid_results, gvfk_polygons):
    """
    Create an interactive map showing GVFK polygons, V1/V2 sites, river segments, and distance connections.
    Handles one-to-many site-GVFK relationships with minimum distances highlighted.
    
    Args:
        v1v2_with_distances (GeoDataFrame): V1/V2 sites with distance data
        rivers_with_contact (GeoDataFrame): River segments with contact
        valid_results (DataFrame): Distance calculation results
        gvfk_polygons (GeoDataFrame): GVFK polygon geometries
    """
    print("Creating interactive map...")
    
    # Convert to WGS84 for web mapping
    v1v2_web = v1v2_with_distances.to_crs('EPSG:4326')
    rivers_web = rivers_with_contact.to_crs('EPSG:4326')
    gvfk_web = gvfk_polygons.to_crs('EPSG:4326')
    
    print(f"Using {len(valid_results)} site-GVFK combinations for visualization")
    
    if v1v2_web.empty:
        print("No valid sites for mapping")
        return
            
    # Get bounds for map centering
    bounds = v1v2_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create folium map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add GVFK polygons to map first (as background)
    sampled_gvfks = set(v1v2_web['Navn'].unique())
    relevant_gvfk_web = gvfk_web[gvfk_web['Navn'].isin(sampled_gvfks)]
    
    print(f"Adding {len(relevant_gvfk_web)} GVFK polygons for visualization")
    
    for idx, gvfk in relevant_gvfk_web.iterrows():
        gvfk_name = gvfk.get('Navn', 'Unknown')
        
        popup_text = f"""
        <b>GVFK Polygon</b><br>
        <b>GVFK:</b> {gvfk_name}<br>
        <b>Type:</b> Groundwater Body
        """
        
        folium.GeoJson(
            gvfk.geometry.__geo_interface__,
            style_function=lambda x: {
                'fillColor': 'lightgray',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.3
            },
            popup=folium.Popup(popup_text, max_width=200)
        ).add_to(m)
    
    # Add V1/V2 sites to map (group by site to avoid overlapping identical geometries)
    unique_sites = v1v2_web.drop_duplicates(subset=['Lokalitet_'])
    
    for idx, site in unique_sites.iterrows():
        site_id = site['Lokalitet_']
        site_type = site.get('Lokalitete', 'Unknown')
        
        # Get all GVFKs for this site and their distances
        site_data = v1v2_web[v1v2_web['Lokalitet_'] == site_id]
        site_gvfks = sorted(list(set(site_data['Navn'].tolist())))  # Remove duplicates and sort
        site_distances = sorted(site_data['Distance_m'].dropna().tolist())  # Sort distances
        
        # Get minimum distance information
        min_distance = site_data['Min_Dist_m'].iloc[0] if 'Min_Dist_m' in site_data.columns and not site_data['Min_Dist_m'].isna().all() else None
        
        # Color by site type
        if 'V1 og V2' in site_type:
            color = 'purple'
        elif 'V1' in site_type:
            color = 'red'
        elif 'V2' in site_type:
            color = 'blue'
        else:
            color = 'gray'
        
        # Create enhanced popup with site info
        min_dist_text = f"{min_distance:.1f}m" if min_distance is not None else "N/A"
        
        if site_distances:
            distance_range_text = f"{site_distances[0]:.1f}m - {site_distances[-1]:.1f}m"
        else:
            distance_range_text = "N/A"
            
        popup_text = f"""
        <b>Site ID:</b> {site_id}<br>
        <b>Type:</b> {site_type}<br>
        <b>Associated GVFKs:</b> {len(site_gvfks)}<br>
        <b>GVFK Names:</b> {', '.join(site_gvfks[:3])}{('...' if len(site_gvfks) > 3 else '')}<br>
        <b>Distance Range:</b> {distance_range_text}<br>
        <b><span style="color: red;">MINIMUM Distance:</span></b> <b>{min_dist_text}</b>
        """
        
        # Add polygon to map
        folium.GeoJson(
            site.geometry.__geo_interface__,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': color,
                'weight': 2,
                'fillOpacity': 0.7
            },
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)
    
    # Add river segments for the same GVFKs
    sampled_gvfks = set(v1v2_web['Navn'].unique())
    relevant_rivers = rivers_web[rivers_web['GVForekom'].isin(sampled_gvfks)]
    
    print(f"Adding {len(relevant_rivers)} river segments for visualization")
    
    for idx, river in relevant_rivers.iterrows():
        gvfk = river.get('GVForekom', 'Unknown')
        
        popup_text = f"""
        <b>River Segment</b><br>
        <b>GVFK:</b> {gvfk}<br>
        <b>Contact:</b> {river.get('Kontakt', 'Unknown')}
        """
        
        folium.GeoJson(
            river.geometry.__geo_interface__,
            style_function=lambda x: {
                'color': 'darkblue',
                'weight': 3,
                'opacity': 0.8
            },
            popup=folium.Popup(popup_text, max_width=200)
        ).add_to(m)
    
    # Add distance lines - show ALL distances with minimum highlighted
    print("Adding distance connection lines...")
    
    # Separate minimum and non-minimum distances
    min_distance_results = valid_results[valid_results['Is_Min_Distance'] == True].copy()
    non_min_distance_results = valid_results[valid_results['Is_Min_Distance'] == False].copy()
    
    print(f"Total distance calculations to show: {len(valid_results)}")
    print(f"- Minimum distances (highlighted): {len(min_distance_results)}")
    print(f"- Non-minimum distances (lighter): {len(non_min_distance_results)}")
    
    # Process ALL distance calculations (both minimum and non-minimum)
    all_distances_to_show = valid_results.copy()
    
    for idx, result in all_distances_to_show.iterrows():
        lokalitet_id = result['Lokalitet_ID']
        gvfk = result['GVFK']
        distance = result['Distance_to_River_m']
        is_minimum = result['Is_Min_Distance']
        
        # Get the site geometry for this specific combination
        site_combo = v1v2_web[
            (v1v2_web['Lokalitet_'] == lokalitet_id) & 
            (v1v2_web['Navn'] == gvfk)
        ]
        
        if site_combo.empty:
            continue
            
        site_geom = site_combo.iloc[0].geometry
        
        # Find the closest river segment in the same GVFK
        matching_rivers = relevant_rivers[relevant_rivers['GVForekom'] == gvfk]
        
        if not matching_rivers.empty:
            min_distance_calc = float('inf')
            closest_point_on_site = None
            closest_point_on_river = None
            
            for _, river in matching_rivers.iterrows():
                # Calculate closest points between site and river
                distance_calc = site_geom.distance(river.geometry)
                if distance_calc < min_distance_calc:
                    min_distance_calc = distance_calc
                    
                    # Get closest points
                    closest_points = nearest_points(site_geom, river.geometry)
                    closest_point_on_site = closest_points[0]
                    closest_point_on_river = closest_points[1]
            
            # Add line connecting closest points
            if closest_point_on_site and closest_point_on_river:
                line_coords = [
                    [closest_point_on_site.y, closest_point_on_site.x],
                    [closest_point_on_river.y, closest_point_on_river.x]
                ]
                
                # Style based on whether this is the minimum distance
                if is_minimum:
                    # Highlight minimum distances
                    line_color = 'red'
                    line_weight = 3
                    line_opacity = 1.0
                    popup_prefix = "<b>â­ MINIMUM DISTANCE</b>"
                    label_style = 'font-size: 10pt; color: red; font-weight: bold; background-color: white; padding: 2px; border: 1px solid red;'
                    label_text = f'{distance:.0f}m MIN'
                else:
                    # Non-minimum distances (lighter styling)
                    line_color = 'orange'
                    line_weight = 1
                    line_opacity = 0.6
                    popup_prefix = "Additional Distance"
                    label_style = 'font-size: 8pt; color: orange; background-color: white; padding: 1px; border: 1px solid orange;'
                    label_text = f'{distance:.0f}m'
                
                folium.PolyLine(
                    line_coords,
                    color=line_color,
                    weight=line_weight,
                    opacity=line_opacity,
                    popup=f"{popup_prefix}<br>Lokalitet: {lokalitet_id}<br>GVFK: {gvfk}<br>Distance: {distance:.1f}m"
                ).add_to(m)
                
                # Add distance label at midpoint (only for minimum distances to avoid clutter)
                if is_minimum:
                    mid_lat = (line_coords[0][0] + line_coords[1][0]) / 2
                    mid_lon = (line_coords[0][1] + line_coords[1][1]) / 2
                    
                    folium.Marker(
                        location=[mid_lat, mid_lon],
                        icon=folium.DivIcon(
                            html=f'<div style="{label_style}">{label_text}</div>',
                            icon_size=(60, 20),
                            icon_anchor=(30, 10)
                        )
                    ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 320px; height: 200px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 10px">
    <b>Legend</b><br>
    <i class="fa fa-square" style="color:lightgray"></i> GVFK Polygons<br>
    <i class="fa fa-circle" style="color:red"></i> V1 Sites<br>
    <i class="fa fa-circle" style="color:blue"></i> V2 Sites<br>
    <i class="fa fa-circle" style="color:purple"></i> V1 & V2 Sites<br>
    <i class="fa fa-minus" style="color:darkblue"></i> River Segments<br>
    <i class="fa fa-minus" style="color:red"></i> <b>â­ MINIMUM Distance Lines</b><br>
    <i class="fa fa-minus" style="color:orange"></i> Additional Distance Lines<br>
    <small><b>Red lines:</b> Shortest pathway per site (critical for risk)<br>
    <b>Orange lines:</b> Other pathways through different GVFKs<br>
    Showing ~1000 sites across Denmark with ALL calculations.</small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    map_path = get_output_path('interactive_distance_map')
    m.save(map_path)
    print(f"Interactive map saved to: {map_path}")
    print(f"Open the file in a web browser to explore the distance calculations!") 
