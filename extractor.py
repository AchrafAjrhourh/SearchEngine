import time
import logging
import urllib.parse
import feedparser
import requests
import re # Added for language detection
from googlenewsdecoder import gnewsdecoder

def is_arabic(text):
    """Detects if a string contains Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text))

def fetch_real_news(figure_name):
    logging.info(f"Starting Google News search for: '{figure_name}'...")
    raw_data = ""
    
    try:
        encoded_name = urllib.parse.quote(figure_name)
        
        # --- SMART LOCALE DETECTION ---
        # If query is Arabic, we target the Morocco/Arabic edition
        if is_arabic(figure_name):
            # hl=ar (Arabic), gl=MA (Morocco), ceid=MA:ar (Morocco Arabic Edition)
            rss_url = f"https://news.google.com/rss/search?q={encoded_name}+when:1d&hl=ar&gl=MA&ceid=MA:ar"
            logging.info("Arabic detected. Using Morocco/Arabic news edition.")
        else:
            # Default to Global/English
            rss_url = f"https://news.google.com/rss/search?q={encoded_name}+when:1d&hl=en-US&gl=US&ceid=US:en"
            logging.info("Using Global/English news edition.")

        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            logging.warning(f"No news found in the RSS feed for {figure_name}.")
            return None
            
        for index, entry in enumerate(feed.entries[:5]):
            google_url = entry.link
            title = entry.title
            pub_date = entry.published 
            
            logging.info(f"Found Article {index + 1}: {title}")
            
            try:
                decoded = gnewsdecoder(google_url)
                final_url = decoded["decoded_url"] if decoded.get("status") else google_url
            except Exception:
                final_url = google_url

            logging.info("Reading full article content via Jina Reader...")
            jina_url = f"https://r.jina.ai/{final_url}"
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
            
            try:
                response = requests.get(jina_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    full_article_text = response.text[:3000] 
                else:
                    full_article_text = f"Snippet: {title}"
            except Exception:
                full_article_text = f"Snippet: {title}"
            
            raw_data += f"[URL: {final_url}]\n[Date: {pub_date}]\n[Title: {title}]\nContent: {full_article_text}\n\n"
            time.sleep(2)
                
        return raw_data
        
    except Exception as e:
        logging.error(f"Failed to fetch news. Error: {e}")
        return None
