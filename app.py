import streamlit as st
import logging
import json
import os
from config import setup_logging
from extractor import execute_deep_social_extraction
from summarizer import summarize_news

# Initialize background terminal logging
setup_logging()

# --- LOAD JSON DICTIONARY ---
if not os.path.exists("entities.json"):
    with open("entities.json", "w", encoding="utf-8") as f:
        json.dump({
            "entities": {
                "Mehdi Bensaïd": {"id": "MB", "keywords": ["مهدي بنسعيد", "Mehdi Bensaïd"]}
            },
            "scopes": {
                "Réseaux Sociaux (Social Media)": "RS",
                "Siaq I3lami / Politique (News & Web)": "PE"
            }
        }, f, ensure_ascii=False, indent=4)

with open("entities.json", "r", encoding="utf-8") as f:
    config_data = json.load(f)
    ENTITIES = config_data.get("entities", {})
    SCOPES = config_data.get("scopes", {})

# --- WEB PAGE CONFIGURATION ---
st.set_page_config(page_title="Global News Aggregator", page_icon="🌍", layout="centered")

st.title("🌍 Global AI News Aggregator")
st.markdown("Sélectionnez une cible et une portée de recherche pour générer le rapport.")
st.divider()

# --- SESSION STATE INITIALIZATION (Mobile Persistence) ---
if "last_searched" not in st.session_state:
    st.session_state.last_searched = ""
if "final_report" not in st.session_state:
    st.session_state.final_report = None

# --- USER INPUT ---
col1, col2 = st.columns(2)

with col1:
    options = ["-- Recherche personnalisée --"] + list(ENTITIES.keys())
    selected_id = st.selectbox("🕵️ Cible:", options)

with col2:
    selected_scope_display = st.selectbox("📡 Type de source (Scope):", list(SCOPES.keys()))
    scope_id = SCOPES[selected_scope_display]

if selected_id == "-- Recherche personnalisée --":
    custom_name = st.text_input("Ou tapez un nom libre:")
    target_keywords = [custom_name] if custom_name.strip() else []
    display_name = custom_name
    entity_id = "CUSTOM"
else:
    target_keywords = ENTITIES[selected_id]["keywords"]
    entity_id = ENTITIES[selected_id]["id"]
    display_name = selected_id

if st.button("Generate Briefing"):
    if not target_keywords:
        st.error("Veuillez entrer ou sélectionner un nom.")
    else:
        # Create the final composite ID (e.g. MB-RS or PAM-PE)
        composite_id = f"{entity_id}-{scope_id}"
        
        st.session_state.last_searched = f"{display_name}_{scope_id}"
        st.session_state.final_report = None 
        
        with st.spinner(f"🔍 Extraction [{scope_id}] pour '{display_name}'..."):
            # Pass the scope_id to the extractor!
            data = execute_deep_social_extraction(target_keywords, scope_id)
            
            if data:
                with st.spinner("🧠 IA en cours de synthèse (Génération du rapport)..."):
                    # Pass the composite ID to the summarizer!
                    report = summarize_news(display_name, composite_id, data)
                    st.session_state.final_report = report
            else:
                st.session_state.final_report = "EMPTY"

# --- PERSISTENT DISPLAY & WHATSAPP EXPORT ---
if st.session_state.last_searched == f"{display_name}_{scope_id}" and display_name != "":
    if st.session_state.final_report == "EMPTY":
        st.warning(f"Aucune donnée trouvée pour '{display_name}' dans la catégorie {scope_id}.")
    elif st.session_state.final_report:
        st.success(f"✅ Briefing Complete! (Filtre: {scope_id})")
        st.markdown("---")
        
        # Split the massive AI string into individual blocks using the horizontal rule
        blocks = st.session_state.final_report.split("---")
        
        for block in blocks:
            clean_block = block.strip()
            if clean_block:
                # 1. Show the beautiful rendered UI text
                st.markdown(clean_block)
                
                # 2. Format for WhatsApp (Convert **bold** to *bold*)
                whatsapp_ready_text = clean_block.replace("**", "*")
                
                # 3. Create the Copy Box
                with st.expander("📋 Copier pour WhatsApp"):
                    st.info("Cliquez sur l'icône de copie en haut à droite du bloc ci-dessous ↗️")
                    st.code(whatsapp_ready_text, language="markdown")
                
                # Add visual separation between the next news item
                st.markdown("---")
