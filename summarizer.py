import logging
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_news(figure_name, raw_text, target_language):
    logging.info(f"Generating detailed summary and sentiment analysis in {target_language}...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Enhanced prompt for depth and sentiment
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a comprehensive briefing in {target_language} for each provided source.
    
    For every source, follow this EXACT structure (translate labels to {target_language}):
    
    ### 📰 [Publisher Name]
    * **Date:** [Date]
    * **Detailed Summary:** [Provide a deep, 3-5 sentence paragraph covering the 'who, what, where, why, and how'. Mention specific names, numbers, or quotes if available in the text.]
    * **Sentiment & Tone:** [Analyze the 'feeling' of the article. Is it Positive, Negative, or Neutral? Is the tone critical, supportive, objective, or sensationalist? Explain why in one sentence.]
    * **Source:** [Read Full Article](URL)
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Do not merge different news stories.
    2. NO HALLUCINATIONS: If the text provided is too short to give 3 sentences, do not invent details. 
    3. NO OUTSIDE KNOWLEDGE: Base everything strictly on the provided 'Content' field.
    4. ACCURACY: Use the exact URLs provided."""
    
    user_prompt = f"Here is the raw data for {figure_name}:\n{raw_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3 # Low temperature for higher factual accuracy
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "Error generating detailed summary."