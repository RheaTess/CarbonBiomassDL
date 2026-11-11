
from src.data.gedi_l4a import inspect_l4a_footprints


study_area = {
    "type": "Polygon",
    "coordinates": [[
        [77.737155, 12.947077],
        [77.737155, 12.950255],
        [77.744129, 12.950255],
        [77.744129, 12.947077],
        [77.737155, 12.947077],
    ]]
}


if __name__ == "__main__":
    result = inspect_l4a_footprints(
        geojson=study_area,
        start_date="2019-04-01",
        end_date="2025-07-02",
        max_records=500,
    )

    print("\n========== GEDI L4A DIAGNOSTICS ==========")

    for key in [
        "status",
        "monthly_image_count",
        "raw_sample_count",
        "quality_sample_count",
        "returned_record_count",
        "truncated",
        "sample_mean_Mg_ha",
        "warning",
    ]:
        print(f"{key}: {result.get(key)}")

    print("\n========== FIRST 10 RECORDS ==========")

    for record in result["records"][:10]:
        print(record)
