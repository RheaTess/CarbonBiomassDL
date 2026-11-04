
from shapely.geometry import shape
from shapely.validation import explain_validity
from pyproj import Geod


# WGS84 ellipsoid for geodesic area calculations
geod = Geod(ellps="WGS84")


def validate_polygon(geojson_geometry):
    """
    Validate a GeoJSON Polygon or MultiPolygon.

    Returns:
        Shapely geometry if valid.

    Raises:
        ValueError if invalid.
    """

    try:
        polygon = shape(geojson_geometry)
    except Exception as error:
        raise ValueError(
            f"Unable to read polygon: {error}"
        )

    if polygon.geom_type not in (
        "Polygon",
        "MultiPolygon",
    ):
        raise ValueError(
            "Please draw a polygon or rectangle."
        )

    if polygon.is_empty:
        raise ValueError("The selected polygon is empty.")

    if not polygon.is_valid:
        reason = explain_validity(polygon)
        raise ValueError(
            f"Invalid polygon: {reason}"
        )

    min_lon, min_lat, max_lon, max_lat = polygon.bounds

    if (
        min_lon < -180
        or max_lon > 180
        or min_lat < -90
        or max_lat > 90
    ):
        raise ValueError(
            "Coordinates are outside valid geographic ranges."
        )

    if polygon.area <= 0:
        raise ValueError(
            "The selected polygon has zero area."
        )

    area_m2, _ = geod.geometry_area_perimeter(polygon)

    area_m2 = abs(area_m2)

    if area_m2 <= 0:
        raise ValueError("Unable to calculate area.")

    area_hectares = area_m2 / 10000
    area_km2 = area_m2 / 1000000

    return {
        "geometry": polygon,
        "area_m2": area_m2,
        "area_hectares": area_hectares,
        "area_km2": area_km2,
        "bounds": polygon.bounds,
    }
