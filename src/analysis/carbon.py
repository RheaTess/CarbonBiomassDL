
def calculate_carbon_stock(
    biomass_density_Mg_ha,
    covered_area_ha,
    carbon_fraction=0.47,
):
    """
    Estimate aboveground biomass and carbon stock.

    Uses the GEDI L4B area-weighted biomass density
    and the area covered by usable GEDI grid cells.

    Returns None when required data is unavailable.
    """

    if biomass_density_Mg_ha is None:
        return None

    if covered_area_ha is None:
        return None

    density = float(biomass_density_Mg_ha)
    area = float(covered_area_ha)

    if density < 0:
        raise ValueError(
            "Biomass density cannot be negative."
        )

    if area <= 0:
        raise ValueError(
            "Covered area must be greater than zero."
        )

    if not 0 < carbon_fraction <= 1:
        raise ValueError(
            "Carbon fraction must be between 0 and 1."
        )

    total_biomass = density * area

    carbon_stock = total_biomass * carbon_fraction

    co2_equivalent = carbon_stock * (44 / 12)

    return {
        "biomass_density_Mg_ha": density,
        "covered_area_ha": area,
        "total_aboveground_biomass_Mg": total_biomass,
        "carbon_fraction": carbon_fraction,
        "aboveground_carbon_stock_Mg_C": carbon_stock,
        "co2_equivalent_Mg_CO2": co2_equivalent,
        "method": "GEDI L4B area-weighted biomass density",
        "note": (
            "Estimates apply only to the quality-covered "
            "area. GEDI L4B represents grid-level mean "
            "aboveground biomass density. Results are "
            "model-derived approximations, not direct "
            "carbon measurements."
        ),
    }
