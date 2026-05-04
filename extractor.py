import time
import logging
import urllib.parse
import feedparser
import requests
from googlenewsdecoder import gnewsdecoder

def fetch_real_news(figure_name):
    logging.info(f"Starting Google News RSS search for: '{figure_name}'...")
    raw_data = ""
    
    try:
        encoded_name = urllib.parse.quote(figure_name)
        rss_url = f"https://news.google.com/rss/search?q={encoded_name}+when:1d"
        
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            logging.warning("No recent news found in the RSS feed.")
            return None
            
        for index, entry in enumerate(feed.entries[:5]):
            google_url = entry.link
            title = entry.title
            pub_date = entry.published 
            
            logging.info(f"Found Article {index + 1}: {title}")
            
            # --- DECODE GOOGLE NEWS LINK ---
            try:
                decoded = gnewsdecoder(google_url)
                if decoded.get("status"):
                    final_url = decoded["decoded_url"]
                else:
                    final_url = google_url
            except Exception:
                final_url = google_url

            # --- JINA READER INTEGRATION ---
            logging.info("Reading full article content via Jina Reader...")
            jina_url = f"https://r.jina.ai/{final_url}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            
            try:
                response = requests.get(jina_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    full_article_text = response.text[:3000] 
                    logging.info("Successfully extracted article text.")
                else:
                    full_article_text = "Content could not be extracted. Rely on title: " + title
                    logging.warning(f"Jina failed to extract. Status Code: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                full_article_text = "Content could not be extracted due to timeout. Rely on title: " + title
                logging.error("Jina extraction timed out after 30 seconds.")
            except Exception as jina_error:
                full_article_text = "Content could not be extracted. Rely on title: " + title
                logging.error(f"Error connecting to Jina: {jina_error}")
            
            raw_data += f"[URL: {final_url}]\n[Date: {pub_date}]\n[Title: {title}]\nContent: {full_article_text}\n\n"
            time.sleep(2)
                
        logging.info("RSS & Extraction completed successfully.")
        return raw_data
        
    except Exception as e:
        logging.error(f"Failed to fetch news. Error: {e}")
        return None