# ForestCarbonDL

**AI-Powered Forest Biomass Monitoring and Carbon Stock Estimation**

ForestCarbonDL is a location-based application that uses Google Earth Engine, Sentinel-2 and GEDI satellite products to analyze vegetation, retrieve aboveground biomass observations and estimate carbon stocks.

## Implemented Features (Days 1–5)

- Location search using OpenStreetMap Nominatim
- Interactive map and polygon boundary selection
- Polygon validation and area calculation
- Sentinel-2 imagery retrieval and NDVI analysis
- GEDI L4A footprint-level biomass observations
- GEDI L4B gridded biomass analysis
- GEDI product selection, comparison and fallback handling
- Aboveground biomass and carbon-stock calculation module

**Current development status:** The carbon calculation module has passed its standalone test. Full Streamlit carbon integration and L4A carbon-density display remain to be completed.

## Technology Stack

- Python
- Streamlit
- Google Earth Engine
- Sentinel-2
- GEDI L4A and L4B
- Folium
- Shapely
- GeoPandas / geospatial utilities where applicable

## Setup

1. Clone the repository.
2. Create a Python virtual environment.
3. Install dependencies using `pip install -r requirements.txt`.
4. Authenticate with Google Earth Engine using `earthengine authenticate`.
5. Create a `.env` file using `.env.example`.
6. Run `streamlit run app.py`.

## Remaining Development

- Finish carbon-stock UI integration and validation
- Day 6: Historical vegetation and forest-cover change analysis
- Day 7: Biomass forecasting
- Day 8: Chatbot and workflow automation
- Day 9: Testing and validation
- Day 10: Final application and documentation

## Scientific Notes

GEDI L4A provides sampled biomass-density observations. GEDI L4B provides gridded biomass-density estimates. Carbon-stock calculations are model-derived approximations and must account for spatial coverage.

Sentinel-2 NDVI is currently used for vegetation monitoring, not as a direct biomass estimator.
