import logging
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_news(figure_name, raw_text, target_language):
    logging.info(f"Generating strictly formatted summary in {target_language}...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a briefing in {target_language} for the provided sources.
    
    ### RELEVANCE GUARDRAIL:
    Check if the content is actually about "{figure_name}". If it is unrelated noise, ignore it completely.
    
    ### MANDATORY LOOP INSTRUCTION:
    You MUST output a separate block for EVERY SINGLE RELEVANT source provided in the raw data. Do not stop after the first one. Separate each block with a horizontal rule (---).
    
    For EACH relevant source, use EXACTLY this format. Translate the labels "Source", "Tonalité", "Viralité", and "Thématique" into {target_language}. Keep the labels bolded.
    
    **Source:** [Insert the raw, plain-text URL here so it can be easily copied]
    
    **Tonalité:** [MUST be exactly ONE word translated into {target_language}: Positive, Negative, or Neutral. No explanations.]
    
    **Viralité:** [Calculate reach based STRICTLY on the [INTERACTIONS/COMMENTS] and [REACH/VIEWS] metadata tags provided for the source. Output a phrase in {target_language} such as "Élevée (15 000 Vues, 400 Commentaires)" or "Faible (0 Vues)". Do not guess; use the exact numbers provided.]
    
    **Thématique:** [Provide a deep, 3-5 sentence paragraph summary covering the 'who, what, where, why, and how' based ONLY on the text.]
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: You must create a new formatted block for each relevant article.
    2. NO HALLUCINATIONS: Do not invent details or precise traffic numbers.
    3. LANGUAGE: The entire output (including the labels) MUST be in {target_language}.
    4. TONALITÉ FORMAT: The Tonalité must be strictly one word, nothing else.
    """
    
    user_prompt = f"Here is the raw data collected for the search query '{figure_name}':\n{raw_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 # Strictly low temperature
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or len(result) < 10:
            return f"No highly relevant detailed news found for '{figure_name}' in the processed articles."
            
        return result
        
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "Error generating detailed summary."
