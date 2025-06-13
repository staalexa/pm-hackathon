import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# Title
st.title('Issue Map Visualization')

# Sidebar filters
st.sidebar.header('Filters')

# Load issues data
issues_df = pd.read_csv('../../data/challenge_2/complete_issues_data.csv')

# Prepare filter options
categories = sorted(issues_df['category'].dropna().unique())
age_groups = sorted(issues_df['age_group'].dropna().unique())
categories = ['All'] + categories
age_groups = ['All'] + age_groups
selected_category = st.sidebar.selectbox('Category', categories)
selected_age = st.sidebar.selectbox('Age Group', age_groups)

# Filter data
filtered_df = issues_df.copy()
if selected_category != 'All':
    filtered_df = filtered_df[filtered_df['category'] == selected_category]
if selected_age != 'All':
    filtered_df = filtered_df[filtered_df['age_group'] == selected_age]

# Define shapefile layers
layers = {
    'Municipalities': {
        'shp_path': '../../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_GEM.shp',
        'admin_col': 'GEN',
        'issues_col': 'municipality'
    },
    'Districts': {
        'shp_path': '../../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_KRS.shp',
        'admin_col': 'GEN',
        'issues_col': 'district'
    },
    'States': {
        'shp_path': '../../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_LAN.shp',
        'admin_col': 'GEN',
        'issues_col': 'state'
    },
}

# Initialize folium map without default tiles
m = folium.Map(location=[51.0, 10.0], zoom_start=6, tiles=None, control_scale=True)
# Add world basemap
folium.TileLayer('OpenStreetMap', name='World Map', overlay=True, control=False).add_to(m)

# Add each administrative layer
for layer_name, params in layers.items():
    # Load shapefile and reproject
    gdf = gpd.read_file(params['shp_path']).to_crs('EPSG:4326')

    # Aggregate issue counts
    count_df = (
        filtered_df
        .groupby(params['issues_col'])
        .size()
        .reset_index(name='issue_count')
    )

    # Merge counts into geodataframe
    merged = gdf.merge(
        count_df,
        left_on=params['admin_col'],
        right_on=params['issues_col'],
        how='left'
    )
    merged['issue_count'] = merged['issue_count'].fillna(0).astype(int)

    # Choropleth overlay
    folium.Choropleth(
        geo_data=merged.to_json(),
        name=layer_name,
        data=merged,
        columns=[params['admin_col'], 'issue_count'],
        key_on=f'feature.properties.{params['admin_col']}',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=layer_name,
        overlay=True,
        control=True,
        show=(layer_name == 'States'),
        highlight=True
    ).add_to(m)

    # GeoJson with tooltip
    folium.GeoJson(
        merged,
        name=f'{layer_name} Info',
        tooltip=folium.GeoJsonTooltip(
            fields=[params['admin_col'], 'issue_count'],
            aliases=[f'{params['admin_col']}:', 'Issues:'],
            localize=True,
            sticky=False
        )
    ).add_to(m)

# Layer control
folium.LayerControl(collapsed=False, position='topright').add_to(m)

# Render map in Streamlit
st_data = st_folium(m, width=700, height=500)
