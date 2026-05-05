import logging
import concurrent.futures
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def process_batch(figure_name, batch_text, system_prompt):
    """Processes a small chunk of data so the AI never gets overwhelmed or lazy."""
    try:
        response = client.chat.completions.create(
            # UPGRADED TO GPT-4o for maximum logic, obedience, and extraction capability
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Voici un lot de données brutes pour '{figure_name}':\n{batch_text}"}
            ],
            temperature=0.2,
            max_tokens=4096 # Maximum allowed output to prevent cutting off
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"AI Batch Error: {e}")
        return ""

def summarize_news(figure_name, raw_text):
    logging.info("Generating God Mode summary in French via Data Chunking...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a briefing in French for the provided sources. No matter what language the original source is in, translate and summarize everything into French.
    
    ### RELEVANCE GUARDRAIL:
    Check if the content is actually about "{figure_name}". If it is completely unrelated noise, ignore it. However, if the figure is mentioned or the context is relevant, you MUST process it.
    
    ### MANDATORY LOOP INSTRUCTION:
    You MUST output a separate block for EVERY SINGLE RELEVANT source provided in this batch. DO NOT SKIP ANY. Separate each block with a horizontal rule (---).
    
    For EACH relevant source, use EXACTLY this format. Keep the labels bolded.
    
    **Source:** [Insert the raw, plain-text URL here so it can be easily copied]
    
    **Tonalité:** [MUST be exactly ONE word in French: Positive, Négative, or Neutre. No explanations.]
    
    **Viralité:** - RULE 1 (SOCIAL MEDIA & YOUTUBE): If the [PLATFORM] tag says YouTube, Facebook, Instagram, or if there are digits provided in the metadata, you MUST NOT estimate. Output the exact numbers provided. Example: "Moyenne (1500 Vues, 45 Commentaires)" or "Élevée (32203 Réactions, 10898 Commentaires)".
    - RULE 2 (NEWS WEBSITES): ONLY if the metadata explicitly says "N/A" (meaning it is a standard web article), you MUST ESTIMATE the traffic. Guess a realistic, random number of readers based on the publisher's notoriety. The number MUST be in the thousands. Output it like this: "Moyenne (~12 500 Vues estimées)".
    
    **Thématique:** [If the source is a detailed news article, provide a deep 3-5 sentence summary. If the source is a short social media post, a concise 1-2 sentence summary is required. ALL TEXT MUST BE IN FRENCH.]
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Create a new formatted block for each article/post. Do not merge them.
    2. LANGUAGE: The entire output MUST be in French.
    3. TONALITÉ FORMAT: Strictly one word.
    """
    
    # 1. SPLIT THE RAW TEXT INTO INDIVIDUAL BLOCKS
    # This prevents the AI from hitting the output limit
    blocks = raw_text.split("[PLATFORM:")
    # Re-add the split string and remove empty spaces
    blocks = ["[PLATFORM:" + b for b in blocks if b.strip()]
    
    if not blocks:
        return f"Aucune actualité pertinente trouvée pour '{figure_name}'."

    # 2. GROUP INTO BATCHES OF 8 SOURCES
    batch_size = 8
    batches = ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]
    
    logging.info(f"Total sources found: {len(blocks)}. Processing in {len(batches)} batches...")

    # 3. PROCESS BATCHES CONCURRENTLY
    # This stitches all the AI outputs back together smoothly
    final_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # executor.map ensures the results stay in the correct order
        results = list(executor.map(lambda b: process_batch(figure_name, b, system_prompt), batches))
        
        for res in results:
            if res and len(res) > 10:
                final_results.append(res)

    if not final_results:
         return f"Aucune actualité pertinente trouvée pour '{figure_name}' dans les articles traités."

    # 4. RETURN THE MASSIVE STITCHED DASHBOARD
    return "\n\n".join(final_results)
