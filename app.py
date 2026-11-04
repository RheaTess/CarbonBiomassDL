
import streamlit as st

from src.location.geocoding import search_location
from src.location.map_selector import display_map
from src.location.geometry import validate_polygon


# --------------------------------
# PAGE CONFIGURATION
# --------------------------------

st.set_page_config(
    page_title="ForestCarbonDL",
    page_icon="🌳",
    layout="wide",
)

st.title("🌳 ForestCarbonDL")
st.subheader(
    "AI-powered forest biomass and carbon monitoring"
)

st.write(
    "Select a forest or geographic area to begin analysis."
)


# --------------------------------
# SESSION STATE
# --------------------------------

defaults = {
    "latitude": 12.9716,
    "longitude": 77.5946,
    "location_name": "Bengaluru, Karnataka",
    "selected_geometry": None,
    "selected_area": None,
    "pending_geometry": None,
    "search_message": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------
# LOCATION SEARCH
# --------------------------------

st.header("1. Select a location")

search_tab, coordinate_tab = st.tabs(
    ["Search by location", "Enter coordinates"]
)

with search_tab:

    with st.form("location_search_form"):

        place_name = st.text_input(
            "Forest / Place Name",
            placeholder="Example: Bannerghatta National Park, Karnataka",
        )

        search_button = st.form_submit_button(
            "Search Location"
        )

    if search_button:

        try:
            result = search_location(place_name)

            if result:

                st.session_state.latitude = result["latitude"]
                st.session_state.longitude = result["longitude"]
                st.session_state.location_name = result["name"]

                # A new location requires a new boundary.
                st.session_state.selected_geometry = None
                st.session_state.selected_area = None

                st.success(
                    f"Location found: {result['name']}"
                )

                st.info(
                    "The map is centered on this location. "
                    "Draw its actual study boundary below."
                )

            else:
                st.error("Location not found. Try another search.")

        except (ValueError, RuntimeError) as error:
            st.error(str(error))


# --------------------------------
# COORDINATE INPUT
# --------------------------------

with coordinate_tab:

    with st.form("coordinate_form"):

        col1, col2 = st.columns(2)

        with col1:
            latitude = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state.latitude),
                format="%.6f",
            )

        with col2:
            longitude = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state.longitude),
                format="%.6f",
            )

        coordinate_button = st.form_submit_button(
            "Set Map Location"
        )

    if coordinate_button:

        st.session_state.latitude = latitude
        st.session_state.longitude = longitude
        st.session_state.location_name = "Custom coordinate location"

        st.session_state.selected_geometry = None
        st.session_state.selected_area = None

        st.success("Map center updated.")


# --------------------------------
# INTERACTIVE MAP
# --------------------------------

st.header("2. Draw the study area")

st.write(
    "Use the polygon or rectangle tool on the left side "
    "of the map to select the forest boundary."
)

st.caption(
    "The map center is only a reference point. "
    "The drawn polygon defines the analysis boundary."
)

map_data = display_map(
    latitude=st.session_state.latitude,
    longitude=st.session_state.longitude,
    zoom=11,
)

drawings = (
    map_data.get("all_drawings")
    if map_data
    else None
)

if drawings:

    latest_drawing = drawings[-1]

    geometry_data = latest_drawing.get("geometry")

    if geometry_data:

        st.session_state.pending_geometry = geometry_data



# --------------------------------
# VALIDATE AND CONFIRM
# --------------------------------

st.header("3. Validate and confirm boundary")

if st.session_state.get("pending_geometry"):

    st.info(
        "A drawing was detected. Click below to validate it."
    )

    if st.button("Validate and Confirm Study Area"):

        try:
            result = validate_polygon(
                st.session_state.pending_geometry
            )

            from shapely.geometry import mapping

            # Store the GeoJSON representation
            st.session_state.selected_geometry = mapping(
                result["geometry"]
            )

            # Store calculated area information
            st.session_state.selected_area = {
                "area_m2": result["area_m2"],
                "area_hectares": result["area_hectares"],
                "area_km2": result["area_km2"],
                "bounds": result["bounds"],
            }

            st.success("Study area successfully validated.")

        except ValueError as error:
            st.error(str(error))


# --------------------------------
# DEBUG: SELECTED GEOMETRY
# --------------------------------

st.subheader("Debug: Selected Geometry")

geojson = st.session_state.get("selected_geometry")

if geojson is not None:

    st.success("GeoJSON successfully stored in session state.")

    st.write("Geometry type:", geojson["type"])

    st.json(geojson)

    if geojson["type"] == "Polygon":
        st.write(
            "Number of coordinate pairs:",
            len(geojson["coordinates"][0])
        )

    elif geojson["type"] == "MultiPolygon":
        st.write(
            "Number of polygons:",
            len(geojson["coordinates"])
        )

else:
    st.warning(
        "No GeoJSON stored. Please draw and validate a boundary."
    )


# --------------------------------
# DISPLAY CONFIRMED AREA
# --------------------------------

if st.session_state.selected_area:

    st.header("4. Confirmed study area")

    area = st.session_state.selected_area

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Area (hectares)",
        f"{area['area_hectares']:,.2f}"
    )

    col2.metric(
        "Area (km²)",
        f"{area['area_km2']:,.4f}"
    )

    col3.metric(
        "Area (m²)",
        f"{area['area_m2']:,.2f}"
    )

    st.json(
        st.session_state.selected_geometry
    )

    st.success(
        "Your geographic boundary is ready for satellite analysis."
    )

    if st.button("Clear Selected Boundary"):

        st.session_state.selected_geometry = None
        st.session_state.selected_area = None
        st.session_state.pending_geometry = None

        st.rerun()

else:

    st.warning(
        "No confirmed study area yet. Draw and validate a polygon."
    )


# --------------------------------
# PROJECT STATUS
# --------------------------------

st.divider()

st.caption(
    "ForestCarbonDL | Day 2: Location selection and "
    "geographic boundary validation"
)
