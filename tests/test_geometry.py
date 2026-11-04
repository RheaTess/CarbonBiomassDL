
import pytest
from src.location.geometry import validate_polygon


def test_valid_polygon():
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 12.0],
            [77.01, 12.0],
            [77.01, 12.01],
            [77.0, 12.01],
            [77.0, 12.0],
        ]]
    }

    result = validate_polygon(geojson)

    print("\nArea in square metres:", result["area_m2"])
    print("Area in hectares:", result["area_hectares"])
    print("Area in square kilometres:", result["area_km2"])

    assert result["area_m2"] > 0
    assert result["area_hectares"] > 0
    assert result["area_km2"] > 0


def test_area_calculation_accuracy():
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 12.0],
            [77.01, 12.0],
            [77.01, 12.01],
            [77.0, 12.01],
            [77.0, 12.0],
        ]]
    }

    result = validate_polygon(geojson)

    # Approximate reference area for this rectangle.
    expected_area_m2 = 1_210_000

    assert result["area_m2"] == pytest.approx(
        expected_area_m2,
        rel=0.02
    )


def test_area_unit_conversion():
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 12.0],
            [77.01, 12.0],
            [77.01, 12.01],
            [77.0, 12.01],
            [77.0, 12.0],
        ]]
    }

    result = validate_polygon(geojson)

    assert result["area_hectares"] == pytest.approx(
        result["area_m2"] / 10000
    )

    assert result["area_km2"] == pytest.approx(
        result["area_m2"] / 1000000
    )


def test_invalid_self_intersecting_polygon():
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 12.0],
            [77.01, 12.01],
            [77.0, 12.01],
            [77.01, 12.0],
            [77.0, 12.0],
        ]]
    }

    with pytest.raises(ValueError):
        validate_polygon(geojson)


def test_invalid_geometry_type():
    geojson = {
        "type": "Point",
        "coordinates": [77.0, 12.0],
    }

    with pytest.raises(ValueError):
        validate_polygon(geojson)
