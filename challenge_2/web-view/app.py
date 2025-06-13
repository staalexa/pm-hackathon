from flask import Flask, render_template, request
import folium
import geopandas as gpd
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    selected_category = request.args.get('category', default='')
    selected_age = request.args.get('age', default='')
    # 0) define your shapefile layers and join columns
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
        # 'Boundary Lines': {
        #     'shp_path': '../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_LI.shp',
        #     'admin_col': 'GEN',
        #     'issues_col': 'district'
        # },
        # 'Government Districts': {
        #     'shp_path': '../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_RBZ.shp',
        #     'admin_col': 'GEN',
        #     'issues_col': 'government district'
        # },
        # 'Countries': {
        #     'shp_path': '../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_STA.shp',
        #     'admin_col': 'GEN',
        #     'issues_col': 'country'
        # },
        # 'Administrative Associations': {
        #     'shp_path': '../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_VWG.shp',
        #     'admin_col': 'GEN',
        #     'issues_col': 'district'
        # },
        # add more layers (RBZ, LI, etc.) here if you like
    }

    # 1) load your issues data
    issues_df = pd.read_csv('../../data/challenge_2/complete_issues_data.csv')
    categories = sorted(issues_df['category'].dropna().unique())
    age_groups = sorted(issues_df['age_group'].dropna().unique())

    if selected_category:
        issues_df = issues_df.loc[issues_df['category'] == selected_category]
    if selected_age:
        issues_df = issues_df.loc[issues_df['age_group'] == selected_age]


    # # 2) build map with a single base-layer
    # m = folium.Map(
    #     location=[51.0, 10.0],
    #     zoom_start=6,
    #     tiles='OpenStreetMap',
    #     control_scale=True
    # )
    # 2) build an empty map (no default tiles)
    m = folium.Map(
        location=[51.0, 10.0],
        zoom_start=6,
        tiles=None,
        control_scale=True
    )

    # 3) add a single, always-on world basemap (not shown in layer control)
    folium.TileLayer(
        'OpenStreetMap',
        name='World Map',
        overlay=True,  # so it doesn't compete as a base-layer
        control=False  # so it never shows up in the layer list
    ).add_to(m)

    # 3) for each admin-level, merge counts & add as a togglable overlay
    for layer_name, params in layers.items():
        # load & reproject
        gdf = gpd.read_file(params['shp_path']).to_crs("EPSG:4326")

        # count & merge
        count_df = (
            issues_df
            .groupby(params['issues_col'])
            .size()
            .reset_index(name='issue_count')
        )
        gdf = gdf.merge(
            count_df,
            left_on=params['admin_col'],
            right_on=params['issues_col'],
            how='left'
        )

        # clean
        gdf['issue_count'] = gdf['issue_count'].fillna(0).astype(int)
        gdf = gdf[[params['admin_col'], 'issue_count', 'geometry']]

        # choropleth overlay
        folium.Choropleth(
            geo_data=gdf.to_json(),
            name=layer_name,
            data=gdf,
            columns=[params['admin_col'], 'issue_count'],
            key_on=f'feature.properties.{params["admin_col"]}',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=layer_name,
            overlay=False,
            control=True,
            show=(layer_name == "States"),
            highlight=True

        ).add_to(m)

        # Count issues per state
        issues_per_state = (
            issues_df.groupby('state')
            .size()
            .reset_index(name='issue_count')
        )

        states = gpd.read_file(
            "../../vg5000_12-31.gk3.shape.ebenen/vg5000_ebenen_1231/VG5000_LAN.shp"
        ).to_crs("EPSG:4326")


        # Merge
        states_with_data = states.merge(
            issues_per_state,
            left_on='GEN',
            right_on='state',
            how='left'
        )

        datetime_cols = states_with_data.select_dtypes(['datetime64[ns]']).columns
        states_for_map = states_with_data.drop(columns=datetime_cols)[['GEN', 'issue_count', 'geometry']]
        states_for_map['issue_count'] = states_for_map['issue_count'].fillna(0).astype(int)

        folium.features.GeoJson(
            states_for_map,
            name='State Info',
            tooltip=folium.features.GeoJsonTooltip(
                fields=['GEN', 'issue_count'],
                aliases=['State:', 'Issues:'],
                localize=True
            )
        ).add_to(m)


    # 4) final layer control (only your overlays will appear)
    folium.LayerControl(collapsed=False, position='topright').add_to(m)

    # Render the map as HTML string
    map_html = m._repr_html_()
    return render_template(
            'index.html',
            map_html=map_html,
            categories=categories,
            age_groups=age_groups,
            selected_category=selected_category
        )

if __name__ == '__main__':
    app.run(debug=True)