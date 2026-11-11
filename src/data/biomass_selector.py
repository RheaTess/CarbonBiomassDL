
from src.data.gedi_l4a import inspect_l4a_footprints
from src.data.gedi_l4b import calculate_l4b_grid_overlap


OPTIONS = ("GEDI L4A", "GEDI L4B", "Compare Both")


def analyze_biomass(
    geojson,
    selection="Compare Both",
    purpose="area_estimate",
):
    """
    Select GEDI biomass products with transparent fallback.

    purpose:
        "area_estimate" - Prefer L4B for gridded area analysis.
        "observations"  - Allow L4A footprint-level results.

    L4A sample means are never treated as forest-wide estimates.
    """

    if selection not in OPTIONS:
        raise ValueError(f"Invalid selection: {selection}")

    if purpose not in ("area_estimate", "observations"):
        raise ValueError(f"Invalid purpose: {purpose}")

    results = {
        "requested_product": selection,
        "purpose": purpose,
        "actual_product": None,
        "fallback_used": False,
        "fallback_reason": None,
        "status": "unavailable",
        "area_biomass_density_Mg_ha": None,
        "l4a": None,
        "l4b": None,
        "errors": {},
        "messages": [],
    }

    def load_l4a():
        if results["l4a"] is None:
            try:
                results["l4a"] = inspect_l4a_footprints(
                    geojson
                )
            except Exception as exc:
                results["errors"]["GEDI L4A"] = str(exc)
        return results["l4a"]

    def load_l4b():
        if results["l4b"] is None:
            try:
                results["l4b"] = calculate_l4b_grid_overlap(
                    geojson
                )
            except Exception as exc:
                results["errors"]["GEDI L4B"] = str(exc)
        return results["l4b"]

    def l4a_available():
        data = load_l4a()
        return (
            data is not None
            and data.get("quality_sample_count", 0) > 0
        )

    def l4b_available():
        data = load_l4b()
        return (
            data is not None
            and data.get("quality_cell_count", 0) > 0
            and data.get("weighted_MU_Mg_ha") is not None
            and data.get("quality_covered_area_ha", 0) > 0
        )

    def use_l4a():
        results["actual_product"] = "GEDI L4A"
        results["status"] = "observations_available"
        results["messages"].append(
            "L4A quality-filtered observations are available. "
            "Their sample mean is not a forest-wide biomass estimate."
        )

    def use_l4b():
        data = load_l4b()

        results["actual_product"] = "GEDI L4B"
        results["status"] = "grid_estimate_available"
        results["area_biomass_density_Mg_ha"] = (
            data["weighted_MU_Mg_ha"]
        )
        results["messages"].append(
            "L4B provides an area-weighted grid estimate. "
            "It includes forest and non-forest biomass and "
            "assumes each grid-cell mean represents its "
            "intersecting portion."
        )

    if selection == "GEDI L4A":
        if l4a_available():
            use_l4a()

            if purpose == "area_estimate":
                results["messages"].append(
                    "L4A observations alone do not establish "
                    "a representative area-wide estimate."
                )

                if l4b_available():
                    use_l4b()
                    results["fallback_used"] = True
                    results["fallback_reason"] = (
                        "L4A has observations but no validated "
                        "area-wide estimator. Using L4B for "
                        "the requested area-level result."
                    )
        elif l4b_available():
            use_l4b()
            results["fallback_used"] = True
            results["fallback_reason"] = (
                "No usable L4A observations were found. "
                "L4B was used instead."
            )

    elif selection == "GEDI L4B":
        if l4b_available():
            use_l4b()
        elif l4a_available():
            use_l4a()
            results["fallback_used"] = True
            results["fallback_reason"] = (
                "No usable L4B grid estimate was found. "
                "L4A observations are shown instead; "
                "no area-wide estimate is available."
            )

    else:
        has_l4a = l4a_available()
        has_l4b = l4b_available()

        if has_l4a and has_l4b:
            use_l4b()
            results["actual_product"] = "GEDI L4A + GEDI L4B"
            results["status"] = "comparison_available"
            results["messages"].append(
                "L4A and L4B are not independent measurements. "
                "Do not average their biomass estimates."
            )
        elif has_l4b:
            use_l4b()
            results["messages"].append(
                "Only GEDI L4B is available for comparison."
            )
        elif has_l4a:
            use_l4a()
            results["messages"].append(
                "Only GEDI L4A observations are available."
            )

    if results["actual_product"] is None:
        if results["errors"]:
            results["status"] = "processing_error"
            results["messages"].append(
                "Biomass availability could not be fully "
                "determined because processing failed."
            )
        else:
            results["messages"].append(
                "GEDI observations are not available "
                "for this area."
            )

    return results
