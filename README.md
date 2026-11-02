
# ForestCarbonDL

An AI-assisted geospatial application for forest biomass estimation,
carbon-stock analysis, historical forest-cover change, and baseline forecasting.

## Technology

- Python
- Streamlit
- Google Earth Engine
- Sentinel-2 and Landsat
- NASA GEDI biomass products
- GeoPandas, Shapely, and Rasterio
- Pandas, NumPy, Plotly, and scikit-learn

## Project status

Day 1: Project setup and data-access verification.

## Scientific limitations

Satellite vegetation indices are not direct biomass measurements.
GEDI biomass estimates have spatial and temporal coverage limitations.
Forecasts will be produced only when sufficient comparable observations
are available.

## Local setup

Create and activate a Python virtual environment, install dependencies
from requirements.txt, configure Earth Engine access, and run:

python -m streamlit run app.py
