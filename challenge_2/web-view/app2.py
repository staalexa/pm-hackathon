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
@st.cache_data
def get_data():
    df_issues = pd.read_csv('../../data/challenge_2/complete_issues_data.csv')
    categories = sorted(df_issues['category'].dropna().unique().tolist())
    age_groups = sorted(df_issues['age_group'].dropna().unique().tolist())
    genders = sorted(df_issues['gender'].dropna().unique().tolist())
    return df_issues, categories, age_groups, genders

df_issues, categories, age_groups, genders = get_data()

selected_categories = st.sidebar.multiselect('Category', options=['All'] + categories, default=['All'])
selected_ages = st.sidebar.multiselect('Age Group', options=['All'] + age_groups, default=['All'])
selected_genders = st.sidebar.multiselect('Gender', options=['All'] + genders, default=['All'])

print("Here1")

@st.cache_data
def do_filter_data(selected_categories, selected_ages, selected_genders):
    filtered_issues = df_issues.copy()
    if 'All' not in selected_categories:
        filtered_issues = filtered_issues[filtered_issues['category'].isin(selected_categories)]
    # Age group filter
    if 'All' not in selected_ages:
        filtered_issues = filtered_issues[filtered_issues['age_group'].isin(selected_ages)]
    # Gender filter
    if 'All' not in selected_genders:
        filtered_issues = filtered_issues[filtered_issues['gender'].isin(selected_genders)]

    return filtered_issues

filtered_issues = do_filter_data(selected_categories, selected_ages, selected_genders)

print("Here2")

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

# Inject CSS once for full opacity
st.markdown(
    """
<style>
    * { opacity: 100% !important; }
</style>
""",
    unsafe_allow_html=True,
)

print("Here3")

# Process each layer and add to map
for layer_name, params in layers.items():
    # Load shapefile and reproject
    gdf = gpd.read_file(params['shp_path']).to_crs('EPSG:4326')

    # Aggregate issue counts by administrative unit
    count_df = (
        filtered_issues
        .groupby(params['issues_col'])
        .size()
        .reset_index(name='issue_count')
    )

    # Merge counts into GeoDataFrame
    merged = gdf.merge(
        count_df,
        left_on=params['admin_col'],
        right_on=params['issues_col'],
        how='left'
    )
    merged['issue_count'] = merged['issue_count'].fillna(0).astype(int)

    # Drop any datetime columns to avoid JSON serialization errors
    datetime_cols = merged.select_dtypes(include=['datetime64[ns]']).columns
    if len(datetime_cols) > 0:
        merged = merged.drop(columns=datetime_cols)

    # Create the Choropleth layer
    choropleth = folium.Choropleth(
        geo_data=merged.to_json(),
        name=layer_name,
        data=merged,
        columns=[params['admin_col'], 'issue_count'],
        key_on=f'feature.properties.{params['admin_col']}',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        overlay=True,
        control=True,
        show=(layer_name == 'States'),
        highlight=True
    ).add_to(m)

    # Hide default choropleth legend
    m.get_root().html.add_child(folium.Element("""
      <style>
        .legend { display: none !important; }
      </style>
    """))

    # Attach tooltip for interactivity
    choropleth.geojson.add_child(
        folium.GeoJsonTooltip(
            fields=[params['admin_col'], 'issue_count'],
            aliases=[f'{params['admin_col']}:', 'Issues:'],
            localize=True,
            sticky=False
        )
    )

# Add layer control
folium.LayerControl(collapsed=False, position='topright').add_to(m)

# Render map in Streamlit
st_data = st_folium(m, width=700, height=500)
