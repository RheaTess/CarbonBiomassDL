
from src.analysis.carbon import calculate_carbon_stock


if __name__ == "__main__":

    result = calculate_carbon_stock(
        biomass_density_Mg_ha=15.3497,
        covered_area_ha=509.1154,
        carbon_fraction=0.47,
    )

    print("\n========== DAY 5: CARBON ESTIMATION ==========")

    for key, value in result.items():
        print(f"{key}: {value}")

    assert result["total_aboveground_biomass_Mg"] > 0
    assert result["aboveground_carbon_stock_Mg_C"] > 0

    print("\nCarbon calculation test passed.")
