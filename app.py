import streamlit as st
import logging
from config import setup_logging
from extractor import fetch_real_news
from summarizer import summarize_news

# Initialize background terminal logging
setup_logging()

# --- WEB PAGE CONFIGURATION ---
st.set_page_config(page_title="Global News Aggregator", page_icon="🌍", layout="centered")

st.title("🌍 Global AI News Aggregator")
st.markdown("Search for any public figure to get an AI-summarized briefing of their latest news across the globe in the last 24 hours.")

st.divider()

# --- USER INPUT ---
# 1. Figure Name Input
figure_name = st.text_input("🕵️ Enter the name of the figure:")

# 2. Language Dropdown Menu
output_language = st.selectbox(
    "🗣️ Select Output Language:",
    ("English", "Arabic", "French", "Spanish")
)

if st.button("Generate Briefing"):
    if figure_name.strip() == "":
        st.error("Please enter a name.")
    else:
        with st.spinner(f"🔍 Searching for '{figure_name}'..."):
            live_data = fetch_real_news(figure_name)
        
        if live_data:
            with st.spinner(f"🧠 AI is synthesizing the articles into {output_language}..."):
                # We now pass the selected output_language to our function!
                final_summary = summarize_news(figure_name, live_data, output_language)
            
            # Step 3: Display the Final Output
            st.success("✅ Briefing Complete!")
            
            # If Arabic is selected, we align the text to the right for proper RTL reading
            if output_language == "Arabic":
                st.markdown(f"<div dir='rtl' style='text-align: right;'>{final_summary}</div>", unsafe_allow_html=True)
            else:
                st.markdown(final_summary) 
        else:
            # FIX: Ensure this says figure_name, not a hardcoded name!
            st.warning(f"No recent breaking news found for '{figure_name}' in the last 24 hours.")
