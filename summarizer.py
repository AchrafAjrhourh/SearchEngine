import logging
import concurrent.futures
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def process_batch(figure_name, batch_text, system_prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Voici un lot de données brutes pour '{figure_name}':\n{batch_text}"}
            ],
            temperature=0.2,
            max_tokens=4096 
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"AI Batch Error: {e}")
        return ""

def summarize_news(figure_name, figure_id, raw_text):
    logging.info("Generating God Mode summary in French via Data Chunking...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a briefing in French for the provided sources. No matter what language the original source is in, translate and summarize everything into French.
    
    ### 🛑 RELEVANCE FILTERING (CRITICAL):
    You must act as a strict Editor-in-Chief. Many news websites include the target's name ("{figure_name}") in sidebars, "read more" widgets, or ads. 
    - If the MAIN SUBJECT of the article is an unrelated topic (e.g., a football match, a foreign event, unrelated general news) and the target is just mentioned in passing or in a sidebar, you MUST SKIP IT ENTIRELY. Do not output a block for it.
    - If it is a social media post that doesn't actually talk about the figure, SKIP IT.
    
    ### 🟢 ANTI-SCRAPING EXCEPTION (DO NOT SKIP THESE):
    If a source is very short (e.g., just a Title or a 1-sentence snippet), but that specific title/snippet IS directly about "{figure_name}", you MUST PROCESS IT and write a 1-sentence summary. Do not skip valid news just because it is short.
    
    --- 
    
    ### OUTPUT FORMAT:
    For EACH source that passes the relevance filter, use EXACTLY this format. Keep the labels bolded. Separate each block with a horizontal rule (---).
    
    **Source:** [Insert the raw, plain-text URL here so it can be easily copied]
    
    **ID:** {figure_id}
    
    **Tonalité:** [MUST be exactly ONE word in French: Positive, Négative, or Neutre. No explanations.]
    
    **Viralité:** - RULE 1 (SOCIAL MEDIA & YOUTUBE): If the [PLATFORM] tag says YouTube, Facebook, Instagram, or if there are digits provided in the metadata, you MUST NOT estimate. Output the exact numbers provided. Example: "Moyenne (1500 Vues, 45 Commentaires)".
    - RULE 2 (NEWS WEBSITES): ONLY if the metadata explicitly says "N/A" (meaning it is a standard web article), you MUST ESTIMATE the traffic based on the publisher's notoriety. The number MUST be in the thousands. Output it like this: "Moyenne (~12 500 Vues estimées)".
    
    **Thématique:** [Provide a summary. If it's a detailed article, write 3-5 sentences. If it's very short, write a 1-sentence summary based on whatever text is available. ALL TEXT MUST BE IN FRENCH.]
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Create a new formatted block for EVERY valid source.
    2. LANGUAGE: The entire output MUST be in French.
    3. TONALITÉ FORMAT: Strictly one word.
    """
    
    blocks = raw_text.split("[PLATFORM:")
    blocks = ["[PLATFORM:" + b for b in blocks if b.strip()]
    
    if not blocks:
        return f"Aucune actualité pertinente trouvée pour '{figure_name}'."

    batch_size = 8
    batches = ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]
    
    logging.info(f"Total sources found: {len(blocks)}. Processing in {len(batches)} batches...")

    final_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda b: process_batch(figure_name, b, system_prompt), batches))
        
        for res in results:
            if res and len(res) > 10:
                final_results.append(res)

    if not final_results:
         return f"Aucune actualité trouvée pour '{figure_name}' dans les articles traités."

    return "\n\n".join(final_results)
