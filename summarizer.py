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
        # --- THE FIX: We now print the exact OpenAI error to your terminal! ---
        print(f"🚨 OpenAI API Error: {e}") 
        logging.error(f"AI Batch Error: {e}")
        return ""

def summarize_news(figure_name, figure_id, raw_text):
    logging.info("Generating God Mode summary in French via Data Chunking...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    base_id = figure_id.split("-")[0] if "-" in figure_id else figure_id
    
    system_prompt = f"""You are an expert news analyst operating on {current_date}. 
    Your goal is to provide a highly detailed executive intelligence briefing in French for the provided sources.
    
    ### 🟢 INCLUSION RULES (CRITICAL):
    1. Secondary Mentions ARE ALLOWED: If the target's name "{figure_name}" appears ANYWHERE in the main body of the article or social post, YOU MUST PROCESS IT.
    2. Do NOT skip an article just because the target is a secondary subject or part of a list.

    ### 🛑 EXCLUSION RULES:
    1. SKIP ONLY IF the name is completely absent from the main text (e.g., it only appears in a sidebar of unrelated links, a footer, or a navigation menu).
    2. Empty/Vague Social Media: If a post has no actual context (e.g., "La vidéo date du 4 mai, mais aucun contenu spécifique n'est mentionné"), SKIP IT ENTIRELY.
    
    --- 
    
    ### OUTPUT FORMAT:
    For EACH source that passes the rules, use EXACTLY this format. Keep the labels bolded. Separate each block with a horizontal rule (---).
    
    [Insert the raw, plain-text URL here]
    
    **Compte:** [CRITICAL RULE: Look at the URL. If the URL contains 'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'tiktok.com', 'youtube.com', or 'youtu.be', output EXACTLY "{base_id}-RS". For all other websites, output EXACTLY "{base_id}-PS".]
    
    **Tonalité:** [MUST be exactly ONE word in French: Positive, Négative, or Neutre. No explanations.]
    
    **Viralité:** - RULE 1 (SOCIAL MEDIA & YOUTUBE): If the URL is a social network, output the exact numbers provided in the metadata if any, or "Moyenne" if missing.
    - RULE 2 (NEWS WEBSITES): ONLY if it is a standard web article, you MUST ESTIMATE the traffic based on the publisher's notoriety. Example: "Moyenne (~12 500 Vues estimées)".
    
    **Thématique:** [CRITICAL: You MUST write a DETAILED and IN-DEPTH paragraph of at least 4 to 6 sentences. Thoroughly explain the context, the core message, what the figure is doing, and the implications. DO NOT be brief! ALL TEXT MUST BE IN FRENCH.]
    
    **Niveau de Risque:** [Assess the political/PR risk: 🟢 Faible, 🟡 Modéré, or 🔴 Élevé]
    
    **Action:** [Provide a short recommendation, e.g., "Aucune action requise (Bruit normal)", "À surveiller", "Nécessite une réponse", etc.]
    
    **Catégorisation:** [Provide 1 or 2 keywords classifying the context, e.g., Institutionnel, Gouvernement, Justice, Sport, Scandale, Vie de Parti, etc.]
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Create a new formatted block ONLY for relevant sources.
    2. LANGUAGE: The entire output MUST be in French.
    3. TONALITÉ FORMAT: Strictly one word.
    4. THÉMATIQUE LENGTH: Must be detailed and comprehensive (4-6 sentences minimum).
    """
    
    blocks = raw_text.split("[PLATFORM:")
    blocks = ["[PLATFORM:" + b for b in blocks if b.strip()]
    
    if not blocks:
        return "NO_RELEVANT_DATA"

    batch_size = 8
    batches = ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]
    
    logging.info(f"Total sources found: {len(blocks)}. Processing in {len(batches)} batches...")

    final_results = []
    # --- THE FIX: Lowered max_workers from 5 to 2 to prevent OpenAI Rate Limits ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda b: process_batch(figure_name, b, system_prompt), batches))
        
        for res in results:
            if res and len(res) > 10:
                final_results.append(res)

    if not final_results:
         return "NO_RELEVANT_DATA"

    return "\n\n".join(final_results)
