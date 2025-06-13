from flask import Flask, render_template
import folium

app = Flask(__name__)

@app.route('/')
def index():
    # Create a Folium map centered on Berlin
    m = folium.Map(location=[52.52, 13.405], zoom_start=12, tiles='CartoDB positron')
    # Example marker
    folium.Marker(
        [52.52, 13.405],
        popup='Berlin',
        tooltip='Click for more'
    ).add_to(m)

    # Render the map as HTML string
    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)