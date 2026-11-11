
import ee

from src.data.gee_client import initialize_earth_engine
from pyproj import CRS, Transformer
from shapely.geometry import shape, Polygon
from shapely.ops import transform as shapely_transform
from rasterio.transform import Affine, rowcol


GEDI_L4B_ASSET = "LARSE/GEDI/GEDI04_B_002"

# GEDI L4B bands required for biomass and quality inspection.
L4B_BANDS = [
    "MU",  # Mean above-ground biomass density (Mg/ha)
    "SE",  # Standard error
    "PE",  # Percentage error
    "V1",  # Variance component 1
    "V2",  # Variance component 2
    "NC",  # Number of unique GEDI tracks
    "NS",  # Number of high-quality waveforms
    "QF",  # Quality flag
    "PS",  # Prediction stratum
    "MI",  # Mode of inference
]


def get_gedi_l4b_image():
    """
    Load the GEDI L4B Version 2 image.

    L4B is a single multiband image, not a monthly ImageCollection.
    """
    initialize_earth_engine()

    image = ee.Image(GEDI_L4B_ASSET)

    return image.select(L4B_BANDS)


def inspect_gedi_l4b(geojson):
    """
    Inspect GEDI L4B grid cells within a supplied GeoJSON polygon.

    Samples pixels using the native projection of the MU band.
    Returns individual grid-cell sample records and summary metadata.

    Important:
    - Each sample represents a native GEDI L4B grid cell.
    - The sample geometry is the pixel-centre point.
    - This is not yet an area-weighted forest-only biomass estimate.
    """

    image = get_gedi_l4b_image()

    study_area = ee.Geometry(geojson)

    biomass_band = image.select("MU")
    native_projection = biomass_band.projection()

    # Sample at the native projection and resolution.
 # Expand the sampling region for diagnostic inspection only.
# This is NOT the forest biomass estimation boundary.
    diagnostic_region = study_area.buffer(2000)

    samples = image.sample(
        region=diagnostic_region,
        projection=native_projection,
        dropNulls=True,
        geometries=True,
        tileScale=4
    )

    sample_info = samples.getInfo()
    features = sample_info.get("features", [])

    records = []

    for feature in features:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        records.append({
            "longitude": (
                geometry.get("coordinates", [None, None])[0]
                if geometry else None
            ),
            "latitude": (
                geometry.get("coordinates", [None, None])[1]
                if geometry else None
            ),
            "MU": properties.get("MU"),
            "SE": properties.get("SE"),
            "PE": properties.get("PE"),
            "V1": properties.get("V1"),
            "V2": properties.get("V2"),
            "NC": properties.get("NC"),
            "NS": properties.get("NS"),
            "QF": properties.get("QF"),
            "PS": properties.get("PS"),
            "MI": properties.get("MI"),
        })

    # Retain only pixels with a valid biomass value.
    valid_records = [
        record for record in records
        if record["MU"] is not None
    ]

    # QF = 2 identifies pixels meeting the product's
    # Level 1 uncertainty requirement.
    quality_records = [
        record for record in valid_records
        if record["QF"] == 2
    ]

    return {
        "product": "GEDI L4B",
        "asset": GEDI_L4B_ASSET,
        "native_scale_m": biomass_band.projection()
            .nominalScale().getInfo(),
        "bands": L4B_BANDS,
        "sampled_pixel_count": len(records),
        "valid_biomass_pixel_count": len(valid_records),
        "quality_level_1_pixel_count": len(quality_records),
        "records": records,
        "quality_level_1_records": quality_records,
    }

def calculate_l4b_grid_overlap(geojson):
    """
    Calculate overlap between the study polygon and native
    GEDI L4B grid cells.

    Returns:
    - Intersecting grid-cell records
    - Overlap area per cell
    - QF=2 area-weighted MU diagnostic

    This does not apply a forest-cover mask.
    """

    image = get_gedi_l4b_image()
    mu_projection = image.select("MU").projection()

    
# GEDI L4B Version 2 uses the EASE-Grid 2.0
# Global equal-area projection (EPSG:6933).
#
# These affine parameters come from the native
# projection metadata returned by Earth Engine.

    native_crs = "EPSG:6933"

    native_transform = [
        1000.8950233496674,   # Pixel width
        0.0,                  # X shear
        -17367530.4451615,   # X origin
        0.0,                  # Y shear
        -1000.8950233496674,  # Pixel height
        7314540.8306386,     # Y origin
    ]

    crs = CRS.from_user_input(native_crs)

    affine = Affine(*native_transform)

    print("GEDI native CRS:", native_crs)
    print("GEDI native transform:", native_transform)


    to_native = Transformer.from_crs(
        "EPSG:4326", crs, always_xy=True
    )
    from_native = Transformer.from_crs(
        crs, "EPSG:4326", always_xy=True
    )

    study_polygon = shape(geojson)

    if not isinstance(study_polygon, Polygon):
        raise ValueError("A Polygon GeoJSON is required.")

    if not study_polygon.is_valid or study_polygon.is_empty:
        raise ValueError("The study polygon is invalid.")

    projected_polygon = shapely_transform(
        to_native.transform, study_polygon
    )

    # Diagnostic sampling includes nearby pixel centres.
    # This buffer is NOT included in overlap calculations.
    sampling_region = ee.Geometry(geojson).buffer(2000)

    samples = image.sample(
        region=sampling_region,
        projection=mu_projection,
        dropNulls=True,
        geometries=True,
        tileScale=4,
    )

    features = samples.getInfo().get("features", [])

    intersecting_cells = []
    visited = set()

    for feature in features:
        properties = feature.get("properties", {})
        coordinates = feature["geometry"]["coordinates"]

        longitude, latitude = coordinates[:2]

        x, y = to_native.transform(longitude, latitude)

        grid_row, grid_col = rowcol(affine, x, y)

        cell_id = (int(grid_row), int(grid_col))

        if cell_id in visited:
            continue

        visited.add(cell_id)

        # Build the native grid-cell polygon from
        # the exact raster affine transformation.
        corners = [
            affine * (grid_col, grid_row),
            affine * (grid_col + 1, grid_row),
            affine * (grid_col + 1, grid_row + 1),
            affine * (grid_col, grid_row + 1),
        ]

        cell_polygon = Polygon(corners)

        intersection = projected_polygon.intersection(
            cell_polygon
        )

        if intersection.is_empty or intersection.area <= 0:
            continue

        overlap_area_m2 = intersection.area
        overlap_area_ha = overlap_area_m2 / 10000.0

        mu = properties.get("MU")
        qf = properties.get("QF")
        se = properties.get("SE")

        if mu is None:
            continue

        # Geographic outline for optional map display.
        cell_wgs84 = shapely_transform(
            from_native.transform, cell_polygon
        )

        intersecting_cells.append({
            "grid_row": int(grid_row),
            "grid_col": int(grid_col),
            "MU_Mg_ha": float(mu),
            "SE_Mg_ha": float(se) if se is not None else None,
            "QF": qf,
            "NC": properties.get("NC"),
            "NS": properties.get("NS"),
            "overlap_area_m2": overlap_area_m2,
            "overlap_area_ha": overlap_area_ha,
            "cell_boundary_geojson": cell_wgs84.__geo_interface__,
        })

    # Use only cells meeting the GEDI L4B
    # Level 1 uncertainty requirement.
    quality_cells = [
        cell for cell in intersecting_cells
        if cell["QF"] == 2
    ]

    covered_area_ha = sum(
        cell["overlap_area_ha"]
        for cell in quality_cells
    )

    weighted_mu = None

    if covered_area_ha > 0:
        weighted_mu = sum(
            cell["MU_Mg_ha"] * cell["overlap_area_ha"]
            for cell in quality_cells
        ) / covered_area_ha

    study_area_ha = projected_polygon.area / 10000.0

    coverage_fraction = (
        covered_area_ha / study_area_ha
        if study_area_ha > 0 else 0.0
    )

    return {
        "product": "GEDI L4B",
        "native_crs": crs.to_string(),
        "study_area_ha": study_area_ha,
        "intersecting_cell_count": len(intersecting_cells),
        "quality_cell_count": len(quality_cells),
        "quality_covered_area_ha": covered_area_ha,
        "quality_coverage_fraction": min(
            coverage_fraction, 1.0
        ),
        "weighted_MU_Mg_ha": weighted_mu,
        "intersecting_cells": intersecting_cells,
        "note": (
            "Area-weighted L4B grid estimate. "
            "Not forest-only biomass; no forest mask applied."
        ),
    }

