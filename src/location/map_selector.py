
import folium

from folium.plugins import Draw
from streamlit_folium import st_folium


def display_map(
    latitude=12.9716,
    longitude=77.5946,
    zoom=10,
    key="forest_map",
):
    """
    Display an interactive map with polygon drawing.

    Returns the user's map interaction data.
    """

    forest_map = folium.Map(
        location=[latitude, longitude],
        zoom_start=zoom,
        control_scale=True,
        tiles="OpenStreetMap",
    )

    # Drawing controls
    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "polygon": True,
            "rectangle": True,
            "circle": False,
            "circlemarker": False,
            "marker": False,
        },
        edit_options={
            "edit": True,
            "remove": True,
        },
    ).add_to(forest_map)

    folium.Marker(
        [latitude, longitude],
        tooltip="Map center",
        icon=folium.Icon(color="green"),
    ).add_to(forest_map)

    map_data = st_folium(
        forest_map,
        height=550,
        use_container_width=True,
        returned_objects=["all_drawings"],
        key=key,
    )

    return map_data
