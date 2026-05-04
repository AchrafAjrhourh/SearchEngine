import logging
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_news(figure_name, raw_text, target_language):
    logging.info(f"Generating detailed summary and sentiment analysis for {figure_name}...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # We added a "Relevance Check" to the system prompt
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a comprehensive briefing in {target_language} for each provided source.
    
    ### RELEVANCE GUARDRAIL:
    Before summarizing a source, check if the content is actually about "{figure_name}" or mentions them in a meaningful context. 
    - If the content is "noise" (e.g., a list of unrelated trending headlines like Trump, sports, or weather that has nothing to do with the figure), ignore it and do NOT output a section for it.
    - If the figure is mentioned, even if they are not the only subject, provide the summary.
    
    For every RELEVANT source, follow this structure (translate labels to {target_language}):
    
    ### 📰 [Publisher Name]
    * **Date:** [Date]
    * **Detailed Summary:** [Provide a deep, 3-5 sentence paragraph covering the 'who, what, where, why, and how'. Mention specific names, numbers, or quotes.]
    * **Sentiment & Tone:** [Analyze the 'feeling'. Is it Positive, Negative, or Neutral? Is the tone critical, supportive, objective, or sensationalist? Explain why in one sentence.]
    * **Source:** [Read Full Article](URL)
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Do not merge different news stories.
    2. NO HALLUCINATIONS: Do not invent details. Base everything STRICTLY on the 'Content' field.
    3. LANGUAGE: The entire output (headings and body) MUST be in {target_language}.
    """
    
    user_prompt = f"Here is the raw data collected for the search query '{figure_name}':\n{raw_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 # Lowered temperature even more for stricter fact-checking
        )
        # Clean up any potential AI chatter
        result = response.choices[0].message.content.strip()
        
        if not result or len(result) < 10:
            return f"No highly relevant detailed news found for '{figure_name}' in the processed articles."
            
        return result
        
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "Error generating detailed summary."
