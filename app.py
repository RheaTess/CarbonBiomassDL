
import streamlit as st

st.set_page_config(
    page_title="ForestCarbonDL",
    page_icon="🌳",
    layout="wide",
)

st.title("ForestCarbonDL")
st.subheader("AI-powered forest biomass and carbon monitoring")

st.write(
    "This application will analyze satellite observations, "
    "forest biomass, carbon stocks, and historical forest-cover changes."
)

st.info(
    "Day 1 setup: the application shell is ready. "
    "Geospatial analysis will be added after data-access verification."
)
