
from src.data.biomass_selector import analyze_biomass


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
    for selection in (
        "GEDI L4A",
        "GEDI L4B",
        "Compare Both",
    ):
        print("\n" + "=" * 50)
        print("REQUESTED:", selection)

        result = analyze_biomass(
            geojson=study_area,
            selection=selection,
            purpose="area_estimate",
        )

        print("Actual:", result["actual_product"])
        print("Status:", result["status"])
        print("Fallback:", result["fallback_used"])
        print("Reason:", result["fallback_reason"])

        print(
            "Area-weighted biomass density:",
            result["area_biomass_density_Mg_ha"],
            "Mg/ha"
        )

        if result["l4a"]:
            print(
                "L4A quality samples:",
                result["l4a"]["quality_sample_count"]
            )

        if result["l4b"]:
            print(
                "L4B quality cells:",
                result["l4b"]["quality_cell_count"]
            )
            print(
                "L4B coverage:",
                result["l4b"]["quality_coverage_fraction"]
            )

        for message in result["messages"]:
            print("NOTE:", message)

        if result["errors"]:
            print("ERRORS:", result["errors"])
