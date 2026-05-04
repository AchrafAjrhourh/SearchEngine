import logging
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

# Initialize the OpenAI client using the key from config.py
client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_news(figure_name, raw_text, target_language):
    logging.info(f"Sending raw text to OpenAI for independent summarization in {target_language}...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # We update the prompt to enforce the chosen language dynamically
    system_prompt = f"""You are a multilingual news summarizer operating on {current_date}. 
    You must process the provided news data and summarize EACH source independently in {target_language}.
    
    For every source in the raw data, create a distinct section formatted exactly like this. (Translate the labels like 'Date', 'Summary', and 'Source' into {target_language}):
    
    ### 📰 [Extract Publisher Name from Content]
    * **Date:** [Date]
    * **Summary:** [Write a 1-2 sentence summary of this specific news item based ONLY on the text]
    * **Source:** [Read Full Article](URL)
    
    ---
    
    STRICT RULES:
    1. Do NOT combine the summaries. Keep them 100% separate.
    2. You must use the EXACT URLs and Dates provided in the raw data.
    3. Do not inject outside knowledge, outdated titles, or pre-trained data. Base your summary STRICTLY and ONLY on the provided text."""
    
    user_prompt = f"Here is the raw breaking news data from the last 24 hours about {figure_name}:\n{raw_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        logging.info("AI successfully generated the independent summaries.")
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Failed to connect to OpenAI. Error: {e}")
        return "An error occurred while generating the summary."