
import ee

from src.data.gee_client import initialize_earth_engine


GEDI_L4A_COLLECTION = "LARSE/GEDI/GEDI04_A_002_MONTHLY"

L4A_BANDS = [
    "agbd",
    "agbd_se",
    "agbd_pi_lower",
    "agbd_pi_upper",
    "algorithm_run_flag",
    "l2_quality_flag",
    "l4_quality_flag",
    "degrade_flag",
    "sensitivity",
    "predictor_limit_flag",
    "response_limit_flag",
    "lat_lowestmode",
    "lon_lowestmode",
]


def inspect_l4a_footprints(
    geojson,
    start_date="2019-04-01",
    end_date="2025-07-02",
    max_records=500,
):
    """
    Diagnose GEDI L4A availability and extract raster samples.

    Counts raw AGBD pixels separately from quality-filtered
    pixels. Does not claim raster samples are unique shots.
    """

    initialize_earth_engine()

    if not 1 <= max_records <= 5000:
        raise ValueError("max_records must be 1 to 5000")

    area = ee.Geometry(geojson)

    collection = (
        ee.ImageCollection(GEDI_L4A_COLLECTION)
        .filterBounds(area)
        .filterDate(start_date, end_date)
    )

    monthly_image_count = collection.size().getInfo()

    if monthly_image_count == 0:
        return {
            "status": "No monthly images found.",
            "monthly_image_count": 0,
            "raw_sample_count": 0,
            "quality_sample_count": 0,
            "returned_record_count": 0,
            "sample_mean_Mg_ha": None,
            "records": [],
        }

    def quality_mask(image):
        mask = (
            image.select("algorithm_run_flag").eq(1)
            .And(image.select("l2_quality_flag").eq(1))
            .And(image.select("l4_quality_flag").eq(1))
            .And(image.select("degrade_flag").eq(0))
            .And(image.select("agbd").gte(0))
        )

        return image.updateMask(mask)

    def add_counts(image):
        raw_count = image.select("agbd").reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=area,
            scale=25,
            maxPixels=10000000,
            tileScale=4,
        ).get("agbd")

        filtered = quality_mask(image)

        quality_count = filtered.select("agbd").reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=area,
            scale=25,
            maxPixels=10000000,
            tileScale=4,
        ).get("agbd")

        return image.set({
            "raw_count": ee.Number(
                ee.Algorithms.If(raw_count, raw_count, 0)
            ),
            "quality_count": ee.Number(
                ee.Algorithms.If(quality_count, quality_count, 0)
            ),
        })

    counted = collection.map(add_counts)

    counts = counted.aggregate_array("raw_count").getInfo()
    quality_counts = counted.aggregate_array(
        "quality_count"
    ).getInfo()

    raw_sample_count = int(sum(counts))
    quality_sample_count = int(sum(quality_counts))

    records = []

    if quality_sample_count > 0:

        # Only process months with quality-filtered data.
        available = counted.filter(
            ee.Filter.gt("quality_count", 0)
        )

        image_list = available.toList(available.size())
        available_count = available.size().getInfo()

        for i in range(available_count):
            if len(records) >= max_records:
                break

            image = ee.Image(image_list.get(i))
            filtered = quality_mask(image)

            # Only require AGBD to be present.
            # Ancillary masked bands must not discard
            # otherwise valid biomass observations.
            selected = filtered.select(L4A_BANDS)

            samples = selected.sample(
                region=area,
                scale=25,
                dropNulls=False,
                geometries=True,
                tileScale=4,
            ).filter(ee.Filter.notNull(["agbd"]))

            remaining = max_records - len(records)

            features = samples.limit(
                remaining
            ).getInfo().get("features", [])

            month = ee.Date(
                image.get("system:time_start")
            ).format("YYYY-MM-dd").getInfo()

            for feature in features:
                p = feature.get("properties", {})
                geometry = feature.get("geometry") or {}
                coords = geometry.get(
                    "coordinates", [None, None]
                )

                records.append({
                    "month": month,
                    "longitude": p.get(
                        "lon_lowestmode"
                    ) if p.get("lon_lowestmode") is not None
                    else coords[0],
                    "latitude": p.get(
                        "lat_lowestmode"
                    ) if p.get("lat_lowestmode") is not None
                    else coords[1],
                    "agbd": p.get("agbd"),
                    "agbd_se": p.get("agbd_se"),
                    "agbd_pi_lower": p.get(
                        "agbd_pi_lower"
                    ),
                    "agbd_pi_upper": p.get(
                        "agbd_pi_upper"
                    ),
                    "sensitivity": p.get(
                        "sensitivity"
                    ),
                    "predictor_limit_flag": p.get(
                        "predictor_limit_flag"
                    ),
                    "response_limit_flag": p.get(
                        "response_limit_flag"
                    ),
                })

    values = [
        float(record["agbd"])
        for record in records
        if record["agbd"] is not None
    ]

    sample_mean = (
        sum(values) / len(values)
        if values else None
    )

    if quality_sample_count > 0:
        status = "Quality-filtered L4A raster data available."
    elif raw_sample_count > 0:
        status = (
            "Raw L4A biomass data exists, "
            "but no samples passed quality filtering."
        )
    else:
        status = (
            "No raw L4A biomass raster samples "
            "found inside the selected polygon."
        )

    return {
        "product": "GEDI L4A",
        "status": status,
        "monthly_image_count": monthly_image_count,
        "raw_sample_count": raw_sample_count,
        "quality_sample_count": quality_sample_count,
        "returned_record_count": len(records),
        "truncated": quality_sample_count > max_records,
        "sample_mean_Mg_ha": sample_mean,
        "records": records,
        "warning": (
            "Raster sample counts are not necessarily "
            "unique GEDI footprints. The mean describes "
            "returned samples only, not the whole forest."
        ),
    }
