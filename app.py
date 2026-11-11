
import datetime
from src.data.biomass_selector import analyze_biomass

import streamlit as st

from src.location.geocoding import search_location
from src.location.map_selector import display_map
from src.location.geometry import validate_polygon
from src.data.sentinel2 import get_sentinel2_composite
from src.analysis.carbon import calculate_carbon_stock


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
    "sentinel2_result": None,
    "biomass_result": None,
    "biomass_geometry": None,
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

        if not place_name.strip():
            st.warning("Please enter a location name.")

        else:
            try:
                result = search_location(place_name)

                if result:

                    st.session_state.latitude = result["latitude"]
                    st.session_state.longitude = result["longitude"]
                    st.session_state.location_name = result["name"]

                    # A new location requires a new boundary.
                    st.session_state.selected_geometry = None
                    st.session_state.selected_area = None
                    st.session_state.pending_geometry = None
                    st.session_state.sentinel2_result = None
                    st.session_state.biomass_result = None
                    st.session_state.biomass_geometry = None

                    st.success(
                        f"Location found: {result['name']}"
                    )

                    st.info(
                        "The map is centered on this location. "
                        "Draw its actual study boundary below."
                    )

                else:
                    st.error(
                        "Location not found. Try another search."
                    )

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
        st.session_state.pending_geometry = None
        st.session_state.sentinel2_result = None

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

            # Store the GeoJSON representation.
            st.session_state.selected_geometry = mapping(
                result["geometry"]
            )

            # Store calculated area information.
            st.session_state.selected_area = {
                "area_m2": result["area_m2"],
                "area_hectares": result["area_hectares"],
                "area_km2": result["area_km2"],
                "bounds": result["bounds"],
            }

            # A new boundary requires a new satellite analysis.
            st.session_state.sentinel2_result = None

            st.success(
                "Study area successfully validated."
            )

        except ValueError as error:
            st.error(str(error))


# --------------------------------
# DEBUG: SELECTED GEOMETRY
# --------------------------------

st.subheader("Debug: Selected Geometry")

geojson = st.session_state.get("selected_geometry")

if geojson is not None:

    st.success(
        "GeoJSON successfully stored in session state."
    )

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

    st.success(
        "Your geographic boundary is ready for satellite analysis."
    )

    if st.button("Clear Selected Boundary"):

        st.session_state.selected_geometry = None
        st.session_state.selected_area = None
        st.session_state.pending_geometry = None
        st.session_state.sentinel2_result = None

        st.rerun()

else:

    st.warning(
        "No confirmed study area yet. Draw and validate a polygon."
    )


# --------------------------------
# SEASON DEFINITIONS
# --------------------------------

SEASONS = {
    "Winter": ("01-01", "03-01"),
    "Pre-monsoon": ("03-01", "06-01"),
    "Monsoon": ("06-01", "10-01"),
    "Post-monsoon": ("10-01", "01-01"),
}


# --------------------------------
# SENTINEL-2 ANNUAL / SEASONAL ANALYSIS
# --------------------------------

st.divider()

st.header("5. Sentinel-2 Satellite Analysis")

if st.session_state.selected_geometry is not None:

    analysis_type = st.radio(
        "Select analysis type",
        options=["Annual", "Seasonal"],
        index=1,
        horizontal=True,
        key="sentinel2_analysis_type",
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_year = st.selectbox(
            "Select analysis year",
            options=list(range(2017, 2027)),
            index=7,
            key="sentinel2_year",
        )

    selected_season = None

    if analysis_type == "Seasonal":

        with col2:
            selected_season = st.selectbox(
                "Select season",
                options=list(SEASONS.keys()),
                key="sentinel2_season",
            )

    cloud_threshold = st.slider(
        "Maximum image cloud percentage",
        min_value=0,
        max_value=100,
        value=30,
        key="sentinel2_cloud_threshold",
    )

    # Build date range based on analysis type.
    if analysis_type == "Annual":

        start_date = f"{selected_year}-01-01"
        end_date = f"{selected_year + 1}-01-01"

        analysis_label = f"Annual {selected_year}"

    else:

        start_suffix, end_suffix = SEASONS[selected_season]

        start_date = f"{selected_year}-{start_suffix}"

        if selected_season == "Post-monsoon":
            end_date = f"{selected_year + 1}-{end_suffix}"
        else:
            end_date = f"{selected_year}-{end_suffix}"

        analysis_label = f"{selected_season} {selected_year}"

    # Do not request observations from future dates.
    today = datetime.date.today()

    requested_start = datetime.date.fromisoformat(start_date)
    requested_end = datetime.date.fromisoformat(end_date)

    actual_end = min(
        requested_end,
        today + datetime.timedelta(days=1),
    )

    if requested_start > today:

        st.warning(
            "The selected analysis period has not started yet. "
            "Choose an earlier year or season."
        )

    else:

        is_partial_period = actual_end < requested_end

        if is_partial_period:

            st.warning(
                f"This is an incomplete {analysis_type.lower()} period. "
                f"Available date range: {start_date} to "
                f"{actual_end.isoformat()} (end date excluded)."
            )

        else:

            st.info(
                f"Selected period: {start_date} to {end_date} "
                f"(end date excluded)."
            )

        actual_end_date = actual_end.isoformat()

        button_label = (
            "Run Annual Satellite Analysis"
            if analysis_type == "Annual"
            else "Run Seasonal Satellite Analysis"
        )

        if st.button(
            button_label,
            disabled=requested_start >= actual_end,
        ):

            with st.spinner(
                "Retrieving and processing Sentinel-2 imagery..."
            ):

                try:

                    result = get_sentinel2_composite(
                        geojson=st.session_state.selected_geometry,
                        start_date=start_date,
                        end_date=actual_end_date,
                        cloud_percentage=cloud_threshold,
                    )

                    result["year"] = selected_year
                    result["analysis_type"] = analysis_type
                    result["season"] = selected_season
                    result["is_partial_period"] = is_partial_period

                    st.session_state.sentinel2_result = result

                    st.success(
                        f"{analysis_type} Sentinel-2 analysis completed!"
                    )

                except Exception as error:

                    st.error(
                        f"Satellite retrieval failed: {error}"
                    )

else:

    st.warning(
        "Please confirm a study boundary before "
        "retrieving satellite imagery."
    )


# --------------------------------
# DISPLAY ANNUAL / SEASONAL RESULTS
# --------------------------------

if st.session_state.sentinel2_result is not None:

    result = st.session_state.sentinel2_result

    if result.get("analysis_type") == "Annual":

        result_heading = f"Annual {result['year']} Results"

    else:

        result_heading = (
            f"{result.get('season', 'Seasonal')} "
            f"{result['year']} Results"
        )

    st.divider()

    st.subheader(result_heading)

    st.write(
        f"Observation period: {result['start_date']} "
        f"to {result['end_date']} (end date excluded)"
    )

    if result.get("is_partial_period"):

        st.warning(
            "These results cover only part of the selected period."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Images retrieved",
        result["image_count"],
    )

    col2.metric(
        "Mean NDVI",
        (
            f"{result['mean_ndvi']:.4f}"
            if result["mean_ndvi"] is not None
            else "Unavailable"
        ),
    )

    col3.metric(
        "Valid pixel coverage",
        (
            f"{result['valid_coverage_percentage']:.2f}%"
            if result["valid_coverage_percentage"] is not None
            else "Unavailable"
        ),
    )

    st.write(
        "Maximum scene cloud percentage:",
        f"{result['cloud_percentage']}%",
    )

    # --------------------------------
    # NDVI DIAGNOSTICS
    # --------------------------------

    st.subheader("NDVI Diagnostic Results")

    st.write("NDVI statistics:")
    st.json(result["ndvi_stats"])

    st.write("SCL land-cover classification histogram:")
    st.json(result["scl_histogram"])

    st.metric(
        "Mean NDVI excluding water-classified pixels",
        (
            f"{result['land_mean_ndvi']:.4f}"
            if result["land_mean_ndvi"] is not None
            else "Unavailable"
        ),
    )

    

    st.caption(
        "The water-excluded NDVI is a diagnostic only. "
        "It must not be interpreted as forest-only NDVI."
    )


# --------------------------------
# GEDI BIOMASS ANALYSIS
# --------------------------------

import json

st.divider()

st.header("6. GEDI Biomass Analysis")

st.write(
    "Estimate aboveground biomass density using "
    "NASA GEDI L4A and L4B products."
)

geometry = st.session_state.get("selected_geometry")
area_info = st.session_state.get("selected_area")

if geometry is None:

    st.warning(
        "Please select and confirm a study boundary "
        "before running GEDI biomass analysis."
    )

else:

    geometry_key = json.dumps(
        geometry,
        sort_keys=True,
    )

    if (
        st.session_state.biomass_geometry
        != geometry_key
    ):
        st.session_state.biomass_result = None
        st.session_state.biomass_geometry = geometry_key

    if area_info:
        st.metric(
            "Selected study area",
            f"{area_info['area_hectares']:.4f} ha",
        )

    st.subheader("Select GEDI Product")

    selected_product = st.selectbox(
        "Biomass data source",
        options=[
            "GEDI L4A",
            "GEDI L4B",
            "Compare Both",
        ],
        index=2,
        key="gedi_product",
    )

    purpose_value = "observations"

    if st.button(
        "Run GEDI Biomass Analysis",
        type="primary",
    ):

        with st.spinner(
            "Retrieving GEDI biomass observations..."
        ):

            try:

                biomass_result = analyze_biomass(
                    geojson=geometry,
                    selection=selected_product,
                    purpose=purpose_value,
                )

                st.session_state.biomass_result = (
                    biomass_result
                )

                if biomass_result["status"] == "processing_error":
                    st.error(
                        "GEDI processing encountered an error."
                    )

                elif biomass_result["status"] == "unavailable":
                    st.warning(
                        "GEDI observations are not available "
                        "for this area."
                    )

                else:
                    st.success(
                        "GEDI biomass analysis completed."
                    )

            except Exception as error:

                st.session_state.biomass_result = None

                st.error(
                    f"GEDI analysis failed: {error}"
                )

    # --------------------------------
    # DISPLAY BIOMASS RESULTS
    # --------------------------------

    biomass_result = st.session_state.biomass_result

    # Avoid showing results for outdated settings.
    if biomass_result is not None:

        if (
            biomass_result["requested_product"]
            != selected_product
            or biomass_result["purpose"]
            != purpose_value
        ):

            biomass_result = None

            st.info(
                "Analysis settings changed. "
                "Run GEDI analysis again to update."
            )

    if biomass_result is not None:

        st.divider()

        st.subheader("GEDI Analysis Results")

        col1, col2 = st.columns(2)

        col1.write(
            "**Requested product:** "
            + biomass_result["requested_product"]
        )

        col2.write(
            "**Product used:** "
            + str(
                biomass_result["actual_product"]
                or "Unavailable"
            )
        )

        if biomass_result["fallback_used"]:

            st.warning(
                "Automatic product fallback applied."
            )

            st.info(
                biomass_result["fallback_reason"]
            )

        status = biomass_result["status"]

        if status == "processing_error":

            st.error(
                "Processing failed. GEDI data availability "
                "could not be determined reliably."
            )

        elif status == "unavailable":

            st.warning(
                "GEDI observations are not available "
                "for this area."
            )

        else:

            density = biomass_result.get(
                "area_biomass_density_Mg_ha"
            )

            if density is not None:

                st.subheader(
                    "Area-weighted Biomass Density"
                )

                st.metric(
                    "GEDI L4B Mean AGBD",
                    f"{density:.4f} Mg/ha",
                )

                st.caption(
                    "This is a coarse-resolution, "
                    "area-weighted GEDI L4B grid estimate. "
                    "It includes forest and non-forest areas. "
                    "A forest mask has not yet been applied."
                )

            # --------------------------------
            # GEDI L4A RESULTS
            # --------------------------------

            l4a = biomass_result.get("l4a")

            if l4a is not None:

                st.subheader(
                    "GEDI L4A Footprint-level Analysis"
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Raw raster samples",
                    l4a.get("raw_sample_count", 0),
                )

                c2.metric(
                    "Quality-filtered samples",
                    l4a.get(
                        "quality_sample_count", 0
                    ),
                )

                sample_mean = l4a.get(
                    "sample_mean_Mg_ha"
                )

                c3.metric(
                    "Sample Mean AGBD",
                    (
                        f"{sample_mean:.4f} Mg/ha"
                        if sample_mean is not None
                        else "Unavailable"
                    ),
                )

                st.caption(
                    "L4A sample statistics describe the "
                    "returned raster samples only. "
                    "They are not a representative "
                    "forest-wide biomass estimate."
                )

                records = l4a.get("records", [])

                if records:

                    with st.expander(
                        "View GEDI L4A observation records"
                    ):

                        st.dataframe(
                            records,
                            use_container_width=True,
                        )

            # --------------------------------
            # GEDI L4B RESULTS
            # --------------------------------

            l4b = biomass_result.get("l4b")

            if l4b is not None:

                st.subheader(
                    "GEDI L4B Gridded Biomass Analysis"
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Intersecting quality cells",
                    l4b.get(
                        "quality_cell_count", 0
                    ),
                )

                coverage = l4b.get(
                    "quality_coverage_fraction"
                )

                c2.metric(
                    "Quality-grid coverage",
                    (
                        f"{coverage * 100:.2f}%"
                        if coverage is not None
                        else "Unavailable"
                    ),
                )

                covered_area = l4b.get(
                    "quality_covered_area_ha"
                )

                c3.metric(
                    "Quality-covered area",
                    (
                        f"{covered_area:.4f} ha"
                        if covered_area is not None
                        else "Unavailable"
                    ),
                )

                st.caption(
                    "Quality-grid coverage measures how "
                    "much of the study polygon intersects "
                    "L4B QF=2 grid cells. It does not "
                    "represent forest-cover percentage."
                )

            # --------------------------------
            # METHODOLOGY AND LIMITATIONS
            # --------------------------------

            with st.expander(
                "Methodology and limitations"
            ):

                for message in biomass_result.get(
                    "messages", []
                ):
                    st.write("- " + message)

        if biomass_result.get("errors"):

            with st.expander(
                "GEDI processing diagnostics"
            ):
                st.json(
                    biomass_result["errors"]
                )

                # ============================================================
# SECTION 7: ABOVEGROUND BIOMASS AND CARBON STOCK
# ============================================================

st.header("7. Aboveground Biomass and Carbon Stock")

biomass_result = st.session_state.get("biomass_result")

if biomass_result is None:
    st.info(
        "Run GEDI Biomass Analysis first to calculate "
        "aboveground biomass and carbon stock."
    )

else:
    l4b = biomass_result.get("l4b")

    if not isinstance(l4b, dict):
        st.warning(
            "GEDI L4B results are unavailable. "
            "Carbon stock cannot be calculated."
        )

    else:
        density = l4b.get("weighted_MU_Mg_ha")
        covered_area = l4b.get("quality_covered_area_ha")

        if density is None or covered_area is None:
            st.warning(
                "Insufficient quality-filtered GEDI L4B "
                "data for carbon stock estimation."
            )

        else:
            carbon_fraction = st.slider(
                "Carbon fraction",
                min_value=0.40,
                max_value=0.55,
                value=0.47,
                step=0.01,
                help=(
                    "Fraction of dry aboveground biomass "
                    "assumed to be carbon."
                ),
            )

            carbon_result = calculate_carbon_stock(
                biomass_density_Mg_ha=density,
                covered_area_ha=covered_area,
                carbon_fraction=carbon_fraction,
            )

            if carbon_result is not None:

                st.subheader("Estimated Biomass and Carbon")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Aboveground Biomass",
                    f"{carbon_result['total_aboveground_biomass_Mg']:,.2f} Mg",
                )

                col2.metric(
                    "Carbon Stock",
                    f"{carbon_result['aboveground_carbon_stock_Mg_C']:,.2f} Mg C",
                )

                col3.metric(
                    "CO₂ Equivalent",
                    f"{carbon_result['co2_equivalent_Mg_CO2']:,.2f} Mg CO₂",
                )

                col4, col5 = st.columns(2)

                col4.metric(
                    "GEDI Covered Area",
                    f"{covered_area:,.2f} ha",
                )

                col5.metric(
                    "Biomass Density",
                    f"{density:,.2f} Mg/ha",
                )

                st.info(carbon_result["note"])

                st.caption(
                    "Carbon estimates are derived from "
                    "GEDI L4B biomass density and quality-covered "
                    "area. CO₂ equivalent represents carbon-stock "
                    "mass expressed as CO₂, not annual emissions "
                    "or sequestration."
                )



# --------------------------------
# PROJECT STATUS
# --------------------------------

st.divider()

st.caption(
    "ForestCarbonDL | Day 5: Sentinel-2 vegetation analysis "
    "and GEDI L4A/L4B biomass estimation"
)
