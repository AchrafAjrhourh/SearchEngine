import asyncio
import os
import urllib.parse
import requests
import feedparser
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from googlenewsdecoder import gnewsdecoder

# Load environment variables
load_dotenv()

# --- CONSTANTS & CONFIG (24 HOURS) ---
NOW = datetime.now(timezone.utc)
TWENTY_FOUR_HOURS_AGO = NOW - timedelta(hours=24)
UNIX_24H_AGO = int(TWENTY_FOUR_HOURS_AGO.timestamp())
ISO_24H_AGO = TWENTY_FOUR_HOURS_AGO.isoformat()

# Keys
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def is_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

class EliteOSINTExtractor:
    def __init__(self, keywords_list, log_callback=None): 
        self.keywords = keywords_list
        self.log_callback = log_callback 
        self.main_kw = keywords_list[0] if keywords_list else ""
        
        self.aggregated_data = ""
        self.result_count = 0  
        self.max_results = 100  

        # --- THE FIX: Removed the [:2] limit ---
        # The engine will now search EVERY keyword listed in your entities.json
        self.search_queries = self.keywords

    def log(self, message):
        print(message) 
        if self.log_callback:
            self.log_callback(message)

    def _append_payload(self, platform, content, url, interactions, reach):
        if self.result_count >= self.max_results: return False

        payload = f"""
        [PLATFORM: {platform}]
        [URL: {url}]
        [INTERACTIONS/COMMENTS: {interactions}]
        [REACH/VIEWS: {reach}]
        [CONTENT: {content[:1500]}] 
        """
        self.result_count += 1
        self.log(f"[{self.result_count}/{self.max_results}] [PAYLOAD READY] -> {platform}")
        self.aggregated_data += payload
        return True

    # =========================================================
    # 1. RSS NEWS MEDIA
    # =========================================================
    async def fetch_news_media(self):
        for kw in self.search_queries:  
            if self.result_count >= self.max_results: break
            
            encoded_query = urllib.parse.quote(f'"{kw}"')
            
            # --- THE FIX: Changed when:12h to when:1d (Past 24 Hours) ---
            if is_arabic(kw):
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=ar&gl=MA&ceid=MA:ar"
            else:
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=fr&gl=MA&ceid=MA:fr"

            try:
                self.log(f"⏳ Calling RSS News for: '{kw}'...")
                feed = await asyncio.to_thread(feedparser.parse, rss_url)
                
                entries = feed.entries
                if entries:
                    self.log(f"✅ Found {len(entries)} RSS News articles for '{kw}'.")
                
                for item in entries:
                    if self.result_count >= self.max_results: break 
                    
                    title = item.title
                    google_url = item.link
                    try:
                        decoded = gnewsdecoder(google_url)
                        final_url = decoded["decoded_url"] if decoded.get("status") else google_url
                    except:
                        final_url = google_url

                    self.log(f"  🔗 [RSS News] Investigating: {final_url}")

                    jina_url = f"https://r.jina.ai/{final_url}"
                    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
                    try:
                        resp = await asyncio.to_thread(requests.get, jina_url, headers=headers, timeout=12)
                        full_text = resp.text if resp.status_code == 200 else title
                    except Exception:
                        full_text = title
                    
                    if not self._append_payload("News Media (RSS)", full_text[:2500], final_url, "N/A", "N/A"):
                        break
                    await asyncio.sleep(0.2) 
            except Exception as e:
                self.log(f"❌ RSS News Error: {e}")

    # =========================================================
    # 2. GOOGLE WEB SEARCH - SERPER BATCH ENGINE (MAX YIELD)
    # =========================================================
    async def fetch_serper_google(self):
        if not SERPER_API_KEY or self.result_count >= self.max_results: return
        
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # 1. Build the massive Batch Payload
        payload = []
        for kw in self.search_queries: 
            for lang in ["ar", "fr", "en"]:
                payload.append({
                    "q": kw,
                    "gl": "ma",          # Geo-locate to Morocco
                    "hl": lang,          # Search across Arabic, French, and English indexes
                    "tbs": "qdr:h12",    # --- THE FIX: Native Google filter for Past 12 hours ---
                    "num": 100           # MAXIMIZED: Pull top 100 results (DO NOT use 'page')
                })
        
        try:
            self.log(f"⏳ Calling Serper Batch Engine for {len(self.search_queries)} keywords across 3 languages...")
            
            # Send the entire list in one single request using json=payload
            resp = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=30)
            
            if resp.status_code != 200:
                self.log(f"🚨 API ERROR [Serper]: Code {resp.status_code} -> {resp.text}")
                return
                
            batch_data = resp.json()
            
            # 2. Extract and Deduplicate Results
            all_organic_results = []
            seen_links = set() # To prevent analyzing the same URL twice
            
            # Serper returns a list of dictionaries for batch requests
            if isinstance(batch_data, list):
                for query_response in batch_data:
                    all_organic_results.extend(query_response.get('organic', []))
            else:
                all_organic_results.extend(batch_data.get('organic', []))
                
            if not all_organic_results:
                self.log(f"⚠️ No Google results found in the batch.")
            else:
                self.log(f"✅ Found {len(all_organic_results)} raw Google results. Filtering duplicates...")

            # 3. Process the unique links
            for item in all_organic_results:
                if self.result_count >= self.max_results: break
                
                link = item.get('link')
                title = item.get('title', '')
                
                # Deduplication check
                if not link or link in seen_links: continue
                seen_links.add(link)
                
                self.log(f"  🔗 [Google] Investigating: {link}")
                
                # Fetch text via Jina AI
                jina_url = f"https://r.jina.ai/{link}"
                headers_jina = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
                try:
                    resp_jina = await asyncio.to_thread(requests.get, jina_url, headers=headers_jina, timeout=12)
                    full_text = resp_jina.text if resp_jina.status_code == 200 else title
                except:
                    full_text = title
                    
                if not self._append_payload("Google Web (Serper)", full_text[:2500], link, "N/A", "N/A"):
                    break
                await asyncio.sleep(0.2)
                
        except Exception as e:
            self.log(f"❌ Serper Batch Error: {e}")

    # =========================================================
    # DYNAMIC ORCHESTRATOR
    # =========================================================
    async def run_all(self):
        self.log(f"\n--- DEPLOYING UNIFIED OSINT ENGINE (MAX {self.max_results}) ---")
        tasks = []
        
        tasks.append(self.fetch_news_media())                  
        tasks.append(self._delayed_task(self.fetch_serper_google(), 1.5)) 
        
        await asyncio.gather(*tasks)
        self.log(f"--- EXTRACTION COMPLETE: FOUND {self.result_count} TOTAL SOURCES ---\n")
        return self.aggregated_data

    async def _delayed_task(self, coro, delay):
        await asyncio.sleep(delay)
        await coro

def execute_deep_social_extraction(keywords_list, log_callback=None):
    extractor = EliteOSINTExtractor(keywords_list, log_callback)
    return asyncio.run(extractor.run_all())
