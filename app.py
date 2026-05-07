import streamlit as st
import logging
import json
import os
import re  
from config import setup_logging
from extractor import execute_deep_social_extraction
from summarizer import summarize_news
from st_copy_to_clipboard import st_copy_to_clipboard
from exporter import generate_docx, generate_pdf

# Initialize background terminal logging
setup_logging()

# --- LOAD JSON DICTIONARY ---
if not os.path.exists("entities.json"):
    with open("entities.json", "w", encoding="utf-8") as f:
        json.dump({
            "entities": {
                "Mehdi Bensaïd": {"id": "MB", "keywords": ["مهدي بنسعيد", "Mehdi Bensaïd"]}
            }
        }, f, ensure_ascii=False, indent=4)

with open("entities.json", "r", encoding="utf-8") as f:
    config_data = json.load(f)
    ENTITIES = config_data.get("entities", {})

# --- WEB PAGE CONFIGURATION ---
st.set_page_config(page_title="Global News Aggregator", page_icon="🌍", layout="centered")

st.title("🌍 Global AI News Aggregator")
st.markdown("Sélectionnez ou tapez une cible pour générer le rapport d'intelligence.")
st.divider()

# --- SESSION STATE INITIALIZATION (Mobile Persistence) ---
if "last_searched" not in st.session_state:
    st.session_state.last_searched = ""
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "docx_data" not in st.session_state:
    st.session_state.docx_data = None
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None

# --- USER INPUT ---
options = ["-- Recherche personnalisée --"] + list(ENTITIES.keys())
selected_id = st.selectbox("🕵️ Cible:", options)

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
        st.session_state.last_searched = display_name
        st.session_state.final_report = None 
        
        # 1. Create a "Terminal" placeholder
        log_container = st.empty()
        log_messages = []

        # 2. Define the callback function to update the UI
        def update_log(msg):
            log_messages.append(msg)
            log_container.code("\n".join(log_messages))

        with st.spinner(f"🔍 Extraction globale en cours pour '{display_name}'..."):
            # Cleaned up: No more scope_id or modifiers
            data = execute_deep_social_extraction(target_keywords, log_callback=update_log)
            
            if data:
                with st.spinner("🧠 IA en cours de synthèse..."):
                    report = summarize_news(display_name, entity_id, data)
                    st.session_state.final_report = report
                    
                    # 🚀 MOBILE FIX: Generate files exactly ONCE and store them in memory!
                    st.session_state.docx_data = generate_docx(report, display_name)
                    st.session_state.pdf_data = generate_pdf(report, display_name)
            else:
                st.session_state.final_report = "EMPTY"

        # 4. CRITICAL: Clear the logs once finished
        log_container.empty()

# --- PERSISTENT DISPLAY & EXPORTS ---
if st.session_state.last_searched == display_name and display_name != "":
    if st.session_state.final_report == "EMPTY":
        st.warning(f"Aucune donnée trouvée pour '{display_name}' dans les dernières 12 heures.")
    elif st.session_state.final_report:
        st.success("✅ Briefing Complete !")
        
        # ==========================================
        # ⬇️ THE NEW EXPORT BUTTONS (MOBILE OPTIMIZED) ⬇️
        # ==========================================
        st.markdown("### 📥 Exporter le Rapport")
        col_docx, col_pdf = st.columns(2)
        
        with col_docx:
            if st.session_state.docx_data:
                st.download_button(
                    label="📄 Télécharger en DOCX",
                    data=st.session_state.docx_data,
                    file_name=f"Briefing_{display_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
        with col_pdf:
            if st.session_state.pdf_data:
                st.download_button(
                    label="📕 Télécharger en PDF",
                    data=st.session_state.pdf_data,
                    file_name=f"Briefing_{display_name}.pdf",
                    mime="application/pdf"
                )
            
        st.markdown("---")
        # ==========================================
        
        # Split the massive AI string into individual blocks using the horizontal rule
        blocks = st.session_state.final_report.split("---")
        
        for idx, block in enumerate(blocks):
            clean_block = block.strip()
            if clean_block:
                
                # ==========================================
                # 🛠️ THE NEW TAB FIX (MOBILE SCROLL SAVER)
                # ==========================================
                # This finds the URL and wraps it in HTML so it forces a new tab
                ui_block = re.sub(
                    r'(\*\*Source:\*\*\s*)(https?://[^\s]+)', 
                    r'\1<a href="\2" target="_blank" rel="noopener noreferrer">\2</a>', 
                    clean_block
                )
                
                # 1. Show the UI text (with HTML enabled for the new tab link)
                st.markdown(ui_block, unsafe_allow_html=True)
                
                # 2. Format for WhatsApp (Using the ORIGINAL block so the URL stays raw for WhatsApp previews!)
                whatsapp_ready_text = clean_block.replace("**", "*")
                
                # 3. The Magic 1-Click Copy Button
                st_copy_to_clipboard(
                    text=whatsapp_ready_text, 
                    before_copy_label="📋 Copier pour WhatsApp", 
                    after_copy_label="✅ Copié!", 
                    key=f"copy_btn_{idx}"
                )
                
                st.markdown("---")
