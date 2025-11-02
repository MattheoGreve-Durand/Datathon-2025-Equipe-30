import streamlit as st

# --- CONFIGURATION DE BASE ---
st.set_page_config(
    page_title="Analyse réglementaire",
    layout="wide",
)

# --- TITRE ET INTRO ---
st.title("Tableau d'analyse réglementaire des entreprises")
st.write("""
Bienvenue dans l’application d’analyse réglementaire.
Cette interface vous permet de :
- charger les données des entreprises (10-K),
- appliquer une loi ou directive,
- et afficher un score d’impact.
""")