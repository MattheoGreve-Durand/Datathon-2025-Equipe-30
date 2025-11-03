import streamlit as st
import pandas as pd
from functions import functions
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Tok Tok Investissement", page_icon="📈", layout="centered")

# --- CUSTOM STYLES ---
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: #e5e5e5;
            font-family: 'Inter', 'Segoe UI', system-ui;
        }

        .main {
            padding: 3rem 2rem;
            max-width: 900px;
            margin: auto;
        }

        h1 {
            font-size: 2.2rem !important;
            text-align: center;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 2rem;
        }

        .stTextInput>div>div>input {
            background-color: #1e1e1e;
            color: #e5e5e5;
            border: 1px solid #333;
            border-radius: 0.6rem;
            padding: 0.75rem 1rem;
            outline: none;
            box-shadow: none;
        }

        .stTextInput>div>div>input:focus {
            border: 1px solid #444 !important;
            box-shadow: none !important;
            outline: none !important;
        }

        section[data-testid="stFileUploader"] {
            background-color: #1e1e1e;
            border: 1px dashed #444;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
            color: #999;
        }

        div.stButton {
            text-align: center;
        }

        div.stButton>button {
            background-color: #343541;
            color: white;
            border: none;
            border-radius: 0.5rem;
            padding: 0.8rem 2rem;
            font-weight: 500;
            transition: background-color 0.2s ease;
            width: auto;
        }

        div.stButton>button:hover {
            background-color: #565869;
        }

        section[data-testid="stFileUploader"] label {
            color: #ccc !important;
            font-size: 0.95rem;
        }

        .custom-label {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.2rem;
            font-size: 1rem;
            color: #e5e5e5;
        }

        div[data-baseweb="select"] {
            width: fit-content !important;
        }

        /* Style des badges dans la table */
        .badge {
            padding: 0.3rem 0.8rem;
            border-radius: 0.5rem;
            color: white;
            font-weight: 500;
            font-size: 0.9rem;
        }
        .badge-tres-haut { background-color: #c0392b; }
        .badge-haut { background-color: #e74c3c; }
        .badge-moyen { background-color: #e67e22; }
        .badge-bas { background-color: #27ae60; }

        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 1rem;
        }
        th {
            background-color: #181a1f;
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        td {
            padding: 0.75rem;
            border-bottom: 1px solid #333;
        }
        tr:nth-child(even) {
            background-color: #1a1d22;
        }
        tr:nth-child(odd) {
            background-color: #111317;
        }
    </style>
""", unsafe_allow_html=True)

# --- APP CONTENT ---
st.title("📈 Tok Tok Investissement")

user_prompt = st.text_input(" ", placeholder="Demande des conseils sur les entreprises du S&P500", label_visibility="collapsed")

# 
user_porfolio = st.text_input(" ", placeholder="Ajoutez votre porfolio S&P500", label_visibility="collapsed")

# Liste déroulante
st.markdown("<p class='custom-label'>Choisissez votre horizon d’investissement :</p>", unsafe_allow_html=True)
investment_horizon = st.selectbox(
    " ",
    ["Court terme", "Moyen terme", "Long terme"],
    index=1,
    label_visibility="collapsed"
)

# Upload de fichier
st.markdown("<p style='margin-top: 2rem; margin-bottom: 0.5rem; font-weight:600;'>Déposez la loi :</p>", unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Ajouter un fichier",
    type=["xml", "pdf", "html", "xhtml", "doc", "docx", "json", "csv", "txt"],
    label_visibility="collapsed"
)

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

# --- ACTION ---
if st.button("Tok me"):
    if uploaded_file is not None:
        with st.spinner("⏳ Analyse du fichier en cours..."):
            try:
                law_resume = getLawInformations(uploaded_file)
                results = functions.getTop10(law_resume, investment_horizon)

                # Convertir le dictionnaire en DataFrame
                df = pd.DataFrame.from_dict(results, orient="index")
                df.index.name = "Entreprise"
                df.reset_index(inplace=True)

                # Renommer les colonnes
                df.rename(columns={
                    "score_final": "Exposition globale",
                    "impact_temporiel": "Impact temporel"
                }, inplace=True)

                # Ajouter la "Note ajustée" selon le score_final
                def note_from_score(score):
                    if score >= 5:
                        return '<span class="badge badge-tres-haut">Très élevée</span>'
                    elif score >= 4.3:
                        return '<span class="badge badge-haut">Élevée</span>'
                    elif score >= 3.8:
                        return '<span class="badge badge-moyen">Modérée</span>'
                    else:
                        return '<span class="badge badge-bas">Faible</span>'

                df["Note ajustée"] = df["Exposition globale"].apply(note_from_score)
                df["Horizon choisi"] = investment_horizon

                # Réorganiser les colonnes
                df = df[["Entreprise", "Exposition globale", "Impact temporel", "Note ajustée", "Horizon choisi"]]

                # Afficher la table stylisée
                st.success("✅ Analyse terminée avec succès !")
                st.markdown("### Résultat de l’analyse :")
                st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

                # Récupérer les graphes correspondants
                spiderCharts = functions.getSpiderCharts(results.keys(), law_resume)

                # --- Affichage direct de tous les graphes ---
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📊 Graphes radar par entreprise :")

                for entreprise in df["Entreprise"]:
                    st.image(spiderCharts[entreprise], caption=f"Graphe radar de {entreprise}")
                    st.markdown("<hr style='border:1px solid #333;'>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Erreur lors du traitement : {e}")
    else:
        st.warning("⚠️ Veuillez d’abord importer un fichier avant de continuer.")