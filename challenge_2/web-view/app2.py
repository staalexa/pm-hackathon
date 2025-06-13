import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# Use wide layout for full-width map
st.set_page_config(page_title='Issue Map Visualization', layout='wide')

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


# Get data and filter options
df_issues, categories, age_groups, genders = get_data()

# Multiselect filters
selected_categories = st.sidebar.multiselect('Category', options=['All'] + categories, default=['All'])
selected_ages = st.sidebar.multiselect('Age Group', options=['All'] + age_groups, default=['All'])
selected_genders = st.sidebar.multiselect('Gender', options=['All'] + genders, default=['All'])

# Textbox search for municipality
search_municipality = st.sidebar.text_input('Search Municipality')


# Filter function
@st.cache_data
def do_filter_data(categories, ages, genders):
    filtered = df_issues.copy()
    if 'All' not in categories:
        filtered = filtered[filtered['category'].isin(categories)]
    if 'All' not in ages:
        filtered = filtered[filtered['age_group'].isin(ages)]
    if 'All' not in genders:
        filtered = filtered[filtered['gender'].isin(genders)]
    return filtered


# Apply filters
temp_filtered = do_filter_data(selected_categories, selected_ages, selected_genders)

# Show matched descriptions if municipality search provided
if search_municipality:
    matched = temp_filtered[temp_filtered['municipality'].str.contains(search_municipality, case=False, na=False)]
    st.sidebar.markdown('### Matched Descriptions')
    if not matched.empty:
        for desc in matched['description']:
            st.sidebar.write(f'- {desc}')
    else:
        st.sidebar.write(f'No issues found for "{search_municipality}".')

# Final filtered issues for mapping
filtered_issues = temp_filtered.copy()

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

# Initialize folium map
m = folium.Map(location=[51.0, 10.0], zoom_start=6, tiles=None, control_scale=True)
folium.TileLayer('OpenStreetMap', name='World Map', overlay=True, control=False).add_to(m)

# Ensure full opacity
st.markdown(
    """
    <style>
        * { opacity: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# Aggregate and add layers
for layer_name, params in layers.items():
    gdf = gpd.read_file(params['shp_path']).to_crs('EPSG:4326')
    count_df = (
        filtered_issues
        .groupby(params['issues_col'])
        .size()
        .reset_index(name='issue_count')
    )
    merged = gdf.merge(
        count_df,
        left_on=params['admin_col'],
        right_on=params['issues_col'],
        how='left'
    )
    merged['issue_count'] = merged['issue_count'].fillna(0).astype(int)

    # Drop any datetime columns
    datetime_cols = merged.select_dtypes(include=['datetime64[ns]']).columns
    if len(datetime_cols) > 0:
        merged = merged.drop(columns=datetime_cols)

    # Create choropleth layer
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
    # Hide default legend
    m.get_root().html.add_child(folium.Element(
        """
        <style>
            .legend { display: none !important; }
        </style>
        """
    ))
    # Attach tooltip
    choropleth.geojson.add_child(
        folium.GeoJsonTooltip(
            fields=[params['admin_col'], 'issue_count'],
            aliases=[f'{params['admin_col']}:', 'Issues:'],
            localize=True,
            sticky=False
        )
    )

# Add layer control
event_layer = folium.LayerControl(collapsed=False, position='topright')
event_layer.add_to(m)

# Render the map full-width in the main area
st_folium(m, height=600, width=1000)
