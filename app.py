import streamlit as st
import logging
from config import setup_logging
from extractor import execute_deep_social_extraction
from summarizer import summarize_news

# Initialize background terminal logging
setup_logging()

# --- WEB PAGE CONFIGURATION ---
st.set_page_config(page_title="Global News Aggregator", page_icon="🌍", layout="centered")

st.title("🌍 Global AI News Aggregator")
st.markdown("Search for any public figure to get an AI-summarized briefing of their latest news across the globe in the last 48 hours. Output is standardized in French.")

st.divider()

# --- USER INPUT ---
# 1. Figure Name Input
figure_name = st.text_input("🕵️ Enter the name of the figure:")

if st.button("Generate Briefing"):
    if figure_name.strip() == "":
        st.error("Please enter a name.")
    else:
        # Step 1: Data Extraction
        with st.spinner(f"🔍 Deploying God Mode OSINT extractors across Web, YouTube, Facebook, and Instagram for '{figure_name}'..."):
            live_data = execute_deep_social_extraction(figure_name)
        
        if live_data:
            with st.spinner(f"🧠 AI is synthesizing and translating all global data into French..."):
                # We removed the output_language variable. It natively defaults to French now.
                final_summary = summarize_news(figure_name, live_data)
            
            # Step 3: Display the Final Output
            st.success("✅ Briefing Complete!")
            st.markdown(final_summary) 
        else:
            st.warning(f"Aucune actualité récente trouvée pour '{figure_name}' au cours des 48 dernières heures.")
