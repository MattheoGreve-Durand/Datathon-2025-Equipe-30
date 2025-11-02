import streamlit as st
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
            max-width: 700px;
            margin: auto;
        }

        h1 {
            font-size: 2.2rem !important;
            text-align: center;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 2rem;
        }

        /* Champ texte */
        .stTextInput>div>div>input {
            background-color: #1e1e1e;
            color: #e5e5e5;
            border: 1px solid #333;
            border-radius: 0.6rem;
            padding: 0.75rem 1rem;
            outline: none;
            box-shadow: none;
        }

        /* Empêcher le contour rouge/orange au focus */
        .stTextInput>div>div>input:focus {
            border: 1px solid #444 !important;
            box-shadow: none !important;
            outline: none !important;
        }

        /* File uploader */
        section[data-testid="stFileUploader"] {
            background-color: #1e1e1e;
            border: 1px dashed #444;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
            color: #999;
        }

        /* Centrage du bouton */
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

        /* Label pour la liste déroulante */
        .custom-label {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.2rem;
            font-size: 1rem;
            color: #e5e5e5;
        }

        /* Liste déroulante réduite */
        div[data-baseweb="select"] {
            width: fit-content !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- APP CONTENT ---
st.title("📈 Tok Tok Investissement")

user_prompt = st.text_input("", placeholder="Demande des conseils sur les entreprises du S&P500")

# Liste déroulante
st.markdown("<p class='custom-label'>Choisissez votre horizon d’investissement :</p>", unsafe_allow_html=True)
investment_horizon = st.selectbox(
    "",
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

# Bouton
if st.button("Tok me"):
    if uploaded_file is not None:
        with st.spinner("⏳ Analyse du fichier en cours..."):
            try:
                law_resume = getLawInformations(uploaded_file)
                top10Entreprises, _ = functions.getTop10(law_resume, investment_horizon)
                st.success("✅ Analyse terminée avec succès !")
                st.markdown("### Résultat de l’analyse :")
                st.write(top10Entreprises)
                st.markdown(f"📊 **Horizon sélectionné :** {investment_horizon}")
            except Exception as e:
                st.error(f"❌ Erreur lors du traitement : {e}")
    else:
        st.warning("⚠️ Veuillez d’abord importer un fichier avant de continuer.")
