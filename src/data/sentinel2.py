import ee

from src.data.gee_client import initialize_earth_engine


SENTINEL2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"


def mask_clouds(image):
    """
    Mask unsuitable Sentinel-2 pixels using the
    Scene Classification Layer (SCL).

    Retained classes:
        2  = Dark area pixels
        4  = Vegetation
        5  = Bare soil
        6  = Water

    Excluded classes:
        0  = No data
        1  = Saturated or defective
        3  = Cloud shadow
        7  = Unclassified
        8  = Medium-probability cloud
        9  = High-probability cloud
        10 = Cirrus
        11 = Snow or ice
    """

    scl = image.select("SCL")

    cloud_mask = (
        scl.neq(0)
        .And(scl.neq(1))
        .And(scl.neq(3))
        .And(scl.neq(7))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )

    return image.updateMask(cloud_mask)


def get_sentinel2_composite(
    geojson,
    start_date,
    end_date,
    cloud_percentage=30
):
    """
    Retrieve Sentinel-2 imagery for a selected seasonal
    date range and generate a cloud-masked median composite.

    Parameters
    ----------
    geojson : dict
        User-confirmed Polygon or MultiPolygon GeoJSON.

    start_date : str
        Inclusive start date in YYYY-MM-DD format.

    end_date : str
        Exclusive end date in YYYY-MM-DD format.

    cloud_percentage : int
        Maximum scene-level cloud percentage.

    Returns
    -------
    dict
        Composite imagery, NDVI, statistics and diagnostics.
    """

    initialize_earth_engine()

    if geojson is None:
        raise ValueError("No study-area GeoJSON provided.")

    if not start_date or not end_date:
        raise ValueError("Start date and end date are required.")

    if start_date >= end_date:
        raise ValueError("End date must be later than start date.")

    if not 0 <= cloud_percentage <= 100:
        raise ValueError("Cloud percentage must be between 0 and 100.")

    # Convert the confirmed GeoJSON to an Earth Engine geometry.
    study_area = ee.Geometry(geojson)

    # Retrieve Sentinel-2 imagery for the selected season.
    collection = (
        ee.ImageCollection(SENTINEL2_COLLECTION)
        .filterBounds(study_area)
        .filterDate(start_date, end_date)
        .filter(
            ee.Filter.lte(
                "CLOUDY_PIXEL_PERCENTAGE",
                cloud_percentage
            )
        )
    )

    image_count = collection.size().getInfo()

    if image_count == 0:
        raise ValueError(
            f"No Sentinel-2 images found between "
            f"{start_date} and {end_date}. "
            "Try another season or increase the cloud threshold."
        )

    # Apply SCL-based cloud and unsuitable-pixel masking.
    masked_collection = collection.map(mask_clouds)
    # Retrieve metadata for every selected Sentinel-2 image
    scene_details = masked_collection.map(
        lambda image: image.set(
            "acquisition_date",
            image.date().format("YYYY-MM-dd")
        )
    ).aggregate_array("system:index").getInfo()

    scene_dates = masked_collection.aggregate_array(
        "acquisition_date"
    ).getInfo()

    print("\n===== SENTINEL-2 IMAGE VALIDATION =====")

    for image_id, date in zip(scene_details, scene_dates):
        print(f"Image ID: {image_id} | Date: {date}")

    # Count scenes that contain at least one valid pixel
# within the selected study area after SCL masking.

    def has_valid_pixels(image):
        valid_count = (
            image.select("B8")
            .reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=study_area,
                scale=20,
                maxPixels=1e9,
                bestEffort=True
            )
            .get("B8")
        )

        return image.set(
            "has_valid_pixels",
            ee.Number(valid_count).gt(0)
        )


    checked_collection = masked_collection.map(has_valid_pixels)

    usable_image_count = (
        checked_collection
        .filter(ee.Filter.eq("has_valid_pixels", True))
        .size()
        .getInfo()
    )

    # Generate a median reflectance composite.
    composite = (
        masked_collection
        .select(["B2", "B3", "B4", "B8", "B11", "B12"])
        .median()
        .clip(study_area)
    )

    # Calculate NDVI from the median reflectance composite.
    ndvi = (
        composite
        .normalizedDifference(["B8", "B4"])
        .rename("NDVI")
        .clip(study_area)
    )

        # True-colour image: Red, Green, Blue
    rgb = composite.select(["B4", "B3", "B2"])

    # False-colour image: NIR, Red, Green
    false_colour = composite.select(["B8", "B4", "B3"])

    # NDVI image
    ndvi = composite.normalizedDifference(
        ["B8", "B4"]
    ).rename("NDVI")

    # ------------------------------------------
    # NDVI STATISTICS
    # ------------------------------------------

    ndvi_stats = ndvi.reduceRegion(
        reducer=(
            ee.Reducer.mean()
            .combine(
                ee.Reducer.median(),
                sharedInputs=True
            )
            .combine(
                ee.Reducer.minMax(),
                sharedInputs=True
            )
            .combine(
                ee.Reducer.count(),
                sharedInputs=True
            )
        ),
        geometry=study_area,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()

    mean_ndvi = ndvi_stats.get("NDVI_mean")

    # ------------------------------------------
    # SCL CLASSIFICATION DIAGNOSTIC
    # ------------------------------------------

    # Find the most frequent SCL class at each pixel
    # across the selected seasonal observations.
    scl_mode = (
        masked_collection
        .select("SCL")
        .mode()
        .rename("SCL")
    )

    # Calculate the distribution of modal SCL classes.
    scl_histogram = scl_mode.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=study_area,
        scale=20,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()

    # ------------------------------------------
    # NDVI EXCLUDING WATER-CLASSIFIED PIXELS
    # ------------------------------------------

    # Diagnostic only. This is not a forest mask.
    ndvi_without_water = ndvi.updateMask(
        scl_mode.neq(6)
    )

    land_ndvi_stats = ndvi_without_water.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=study_area,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()

    land_mean_ndvi = land_ndvi_stats.get("NDVI")

    # ------------------------------------------
    # IMAGE COVERAGE DIAGNOSTIC
    # ------------------------------------------

    valid_mask = composite.select("B8").mask()

    pixel_area = ee.Image.pixelArea()

    valid_area = (
        pixel_area
        .updateMask(valid_mask)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=study_area,
            scale=10,
            maxPixels=1e9,
            bestEffort=True
        )
        .get("area")
    )

    total_area = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=study_area,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    ).get("area")

    coverage_values = ee.Dictionary({
        "valid_area": valid_area,
        "total_area": total_area
    }).getInfo()

    valid_area_value = coverage_values.get("valid_area")
    total_area_value = coverage_values.get("total_area")

    if (
        valid_area_value is not None
        and total_area_value is not None
        and total_area_value > 0
    ):
        valid_coverage_percentage = (
            valid_area_value / total_area_value
        ) * 100
    else:
        valid_coverage_percentage = None

    # ------------------------------------------
    # RETURN RESULTS
    # ------------------------------------------

    return {
        "study_area": study_area,
        "composite": composite,
        "ndvi": ndvi,
        "usable_image_count": usable_image_count,
        "image_count": image_count,

        "mean_ndvi": mean_ndvi,
        "ndvi_stats": ndvi_stats,

        "scl_histogram": scl_histogram,
        "land_mean_ndvi": land_mean_ndvi,

        "valid_coverage_percentage": valid_coverage_percentage,

        "start_date": start_date,
        "end_date": end_date,
        "cloud_percentage": cloud_percentage,
        "rgb_image": rgb,
        "false_colour_image": false_colour,
        "ndvi_image": ndvi,
    }