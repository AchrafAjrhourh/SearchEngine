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
    Your goal is to provide an executive intelligence briefing in French for the provided sources.
    
    ### 🛑 STRICT RELEVANCE FILTERING (CRITICAL):
    You must act as a ruthless Editor-in-Chief. You MUST DELETE AND SKIP the following types of content (Do NOT output a block for them):
    1. "Sidebar Noise" / Passing Mentions: If the MAIN SUBJECT is an unrelated topic (e.g., a football match, a foreign event, Minurso/Sahara general news) and the target is just caught in a sidebar or mentioned briefly, SKIP IT ENTIRELY.
    2. Empty/Vague Social Media: If a post or video has no actual content or context (e.g., "La vidéo date du 4 mai, mais aucun contenu spécifique n'est mentionné" or it's just random hashtags without meaning), SKIP IT ENTIRELY.
    
    ### 🟢 ANTI-SCRAPING EXCEPTION (Keep these):
    If a source is very short (e.g., just a Title) BUT the title itself is explicitly and primarily about "{figure_name}", you MUST PROCESS IT and write a 1-sentence summary.
    
    --- 
    
    ### OUTPUT FORMAT:
    For EACH source that passes the strict relevance filter, use EXACTLY this format. Keep the labels bolded. Separate each block with a horizontal rule (---).
    
    [Insert the raw, plain-text URL here]
    
    **Compte:** {figure_id}
    
    **Tonalité:** [MUST be exactly ONE word in French: Positive, Négative, or Neutre. No explanations.]
    
    **Viralité:** - RULE 1 (SOCIAL MEDIA & YOUTUBE): If the [PLATFORM] tag says YouTube, Facebook, Instagram, or if there are digits provided in the metadata, you MUST NOT estimate. Output the exact numbers provided. Example: "Moyenne (1500 Vues, 45 Commentaires)".
    - RULE 2 (NEWS WEBSITES): ONLY if the metadata explicitly says "N/A" (meaning it is a standard web article), you MUST ESTIMATE the traffic based on the publisher's notoriety. The number MUST be in the thousands. Output it like this: "Moyenne (~12 500 Vues estimées)".
    
    **Thématique:** [Provide a concise summary. ALL TEXT MUST BE IN FRENCH.]
    
    **Niveau de Risque:** [Assess the political/PR risk: 🟢 Faible, 🟡 Modéré, or 🔴 Élevé]
    
    **Action:** [Provide a short recommendation, e.g., "Aucune action requise (Bruit normal)", "À surveiller", "Nécessite une réponse", etc.]
    
    **Catégorisation:** [Provide 1 or 2 keywords classifying the context, e.g., Institutionnel, Gouvernement, Justice, Sport, Scandale, Vie de Parti, etc.]
    
    ---
    
    STRICT RULES:
    1. INDEPENDENT SECTIONS: Create a new formatted block ONLY for relevant sources.
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
         return f"Aucune actualité pertinente trouvée pour '{figure_name}' dans les articles traités."

    return "\n\n".join(final_results)
