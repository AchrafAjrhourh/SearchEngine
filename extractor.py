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

# --- CONSTANTS & CONFIG (48 HOURS) ---
NOW = datetime.now(timezone.utc)
FORTY_EIGHT_HOURS_AGO = NOW - timedelta(days=2)
UNIX_48H_AGO = int(FORTY_EIGHT_HOURS_AGO.timestamp())
ISO_48H_AGO = FORTY_EIGHT_HOURS_AGO.isoformat()

# Keys
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
RAPID_API_KEY = os.getenv("RAPIDAPI_KEY")
RAPID_HOST_IG = os.getenv("RAPIDAPI_HOST_INSTAGRAM")
RAPID_HOST_FB = os.getenv("RAPIDAPI_HOST_FACEBOOK")
RAPID_HOST_GOOGLE = os.getenv("RAPIDAPI_HOST_GOOGLE", "google-search-master-mega.p.rapidapi.com")

def is_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

class EliteOSINTExtractor:
    def __init__(self, keywords_list, scope_id):
        self.keywords = keywords_list
        self.scope_id = scope_id # "RS" or "PE"
        self.main_kw = keywords_list[0] if keywords_list else ""
        
        self.aggregated_data = ""
        self.result_count = 0  
        self.max_results = 50  

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
        print(f"[{self.result_count}/{self.max_results}] [PAYLOAD READY] -> {platform}")
        self.aggregated_data += payload
        return True

    # =========================================================
    # CROSS-API INTERCEPTORS
    # =========================================================
    async def _process_web_link(self, url, title, snippet):
        if self.result_count >= self.max_results: return
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
        try:
            resp = await asyncio.to_thread(requests.get, jina_url, headers=headers, timeout=15)
            full_text = resp.text if resp.status_code == 200 else snippet
        except:
            full_text = snippet
        self._append_payload("Google Mega Web", full_text, url, "N/A", "N/A")

    # =========================================================
    # 1. RSS NEWS MEDIA (PE ONLY) - FIXED
    # =========================================================
    async def fetch_news_media(self):
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            
            encoded_query = urllib.parse.quote(f'"{kw}"')
            if is_arabic(kw):
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=ar&gl=MA&ceid=MA:ar"
            else:
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=fr&gl=MA&ceid=MA:fr"

            try:
                print(f"⏳ Calling RSS News for: '{kw}'...")
                feed = await asyncio.to_thread(feedparser.parse, rss_url)
                
                # --- NEW LOGGING LOGIC ---
                entries = feed.entries
                if not entries:
                    print(f"⚠️ No RSS News found for '{kw}'.")
                else:
                    print(f"✅ Found {len(entries)} RSS News articles for '{kw}'.")
                
                for item in entries:
                    if self.result_count >= self.max_results: break 
                    
                    title = item.title
                    google_url = item.link
                    try:
                        decoded = gnewsdecoder(google_url)
                        final_url = decoded["decoded_url"] if decoded.get("status") else google_url
                    except:
                        final_url = google_url

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
                print(f"❌ RSS News Error: {e}")

    # =========================================================
    # 2. GOOGLE MEGA SEARCH (PE ONLY) - FIXED
    # =========================================================
    async def fetch_google_mega(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        url = f"https://{RAPID_HOST_GOOGLE}/search"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_GOOGLE}
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            try:
                dork = f'"{kw}" (Maroc OR المغرب OR site:.ma)'
                lang = "ar" if is_arabic(kw) else "fr"
                
                print(f"⏳ Calling Google Mega Search | Dork: {dork[:50]}...")
                
                params = {"q": dork, "gl": "ma", "hl": lang, "tbs": "sbd:1,qdr:d2", "autocorrect": "true", "num": "15", "page": "1"}
                resp = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
                data = resp.json()
                results = data.get('organic_results', data.get('results', data.get('items', [])))
                
                # --- NEW LOGGING LOGIC ---
                if not results:
                    print(f"⚠️ No Google Mega results found for '{kw}'.")
                else:
                    print(f"✅ Found {len(results)} Google Mega results for '{kw}'.")
                
                for item in results:
                    if self.result_count >= self.max_results: break
                    link = item.get('url', item.get('link', ''))
                    if not link: continue
                    
                    if 'instagram.com' in link or 'facebook.com' in link or 'youtube.com' in link: 
                        continue 
                    else: 
                        await self._process_web_link(link, item.get('title', ''), item.get('snippet', ''))
                    await asyncio.sleep(0.3) 
            except Exception as e:
                print(f"❌ Google Mega Error: {e}")

    # =========================================================
    # 3. YOUTUBE (RS ONLY) - FIXED
    # =========================================================
    async def fetch_youtube(self):
        if not YT_API_KEY or self.result_count >= self.max_results: return
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            query = urllib.parse.quote(f'"{kw}"')
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&publishedAfter={ISO_48H_AGO.replace('+00:00', 'Z')}&type=video&key={YT_API_KEY}&maxResults=25"
            try:
                print(f"⏳ Calling YouTube API for '{kw}'...")
                response = await asyncio.to_thread(requests.get, url)
                data = response.json()
                items = data.get('items', [])
                
                # --- NEW LOGGING LOGIC ---
                if not items:
                    print(f"⚠️ No YouTube videos found for '{kw}'.")
                else:
                    print(f"✅ Found {len(items)} YouTube videos for '{kw}'.")

                for item in items:
                    if self.result_count >= self.max_results: break
                    video_id = item['id']['videoId']
                    stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YT_API_KEY}"
                    stats_resp = await asyncio.to_thread(requests.get, stats_url)
                    stats = stats_resp.json()['items'][0]['statistics']
                    self._append_payload("YouTube", item['snippet']['title'], f"https://youtu.be/{video_id}", stats.get('commentCount', '0'), stats.get('viewCount', '0'))
            except Exception as e:
                print(f"❌ YouTube Error: {e}")

    # =========================================================
    # 4. INSTAGRAM (RS ONLY)
    # =========================================================
    async def fetch_instagram(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_IG}/search_hashtag.php"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_IG}
        try:
            hashtag = self.main_kw.replace(" ", "")
            print(f"⏳ Calling Instagram for #{hashtag}...")
            response = await asyncio.to_thread(requests.get, search_url, headers=headers, params={"hashtag": hashtag})
            edges = response.json().get('posts', {}).get('edges', [])
            
            # --- NEW LOGGING LOGIC ---
            if not edges:
                print(f"⚠️ No Instagram posts found for #{hashtag}.")
            else:
                print(f"✅ Found {len(edges)} Instagram posts for #{hashtag}.")

            for edge in edges:
                if self.result_count >= self.max_results: break
                node = edge.get('node', {})
                if node.get('taken_at_timestamp', 0) < UNIX_48H_AGO: continue 
                url = f"https://www.instagram.com/p/{node.get('shortcode')}/"
                cap = node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', 'IG Post')
                self._append_payload("Instagram", cap, url, f"{node.get('edge_liked_by', {}).get('count', 0)} Likes", "N/A")
        except Exception as e:
            print(f"❌ Instagram Error: {e}")

    # =========================================================
    # 5. FACEBOOK (RS ONLY)
    # =========================================================
    async def fetch_facebook(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_FB}/search/global"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_FB}
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            params = {"query": f'"{kw}"', "recent_posts": "true", "start_date": FORTY_EIGHT_HOURS_AGO.strftime('%Y-%m-%d'), "end_date": NOW.strftime('%Y-%m-%d')}
            try:
                print(f"⏳ Calling Facebook for '{kw}'...")
                response = await asyncio.to_thread(requests.get, search_url, headers=headers, params=params)
                posts = response.json().get('results', [])
                
                # --- NEW LOGGING LOGIC ---
                if not posts:
                    print(f"⚠️ No Facebook posts found for '{kw}'.")
                else:
                    print(f"✅ Found {len(posts)} Facebook posts for '{kw}'.")

                for post in posts:
                    if self.result_count >= self.max_results: break
                    text = post.get('message', post.get('text', ''))
                    if not text: continue
                    self._append_payload("Facebook", text, post.get('url'), f"{post.get('reactions_count', 0)} Réactions", f"{post.get('reshare_count', 0)} Partages")
            except Exception as e:
                print(f"❌ Facebook Error: {e}")

    # =========================================================
    # DYNAMIC ORCHESTRATOR
    # =========================================================
    async def run_all(self):
        print(f"\n--- DEPLOYING OSINT EXTRACTORS | SCOPE: {self.scope_id} (MAX {self.max_results}) ---")
        tasks = []
        
        if self.scope_id == "PE":
            tasks.append(self.fetch_news_media())
            tasks.append(self._delayed_task(self.fetch_google_mega(), 1.5))
        elif self.scope_id == "RS":
            tasks.append(self.fetch_youtube())
            tasks.append(self._delayed_task(self.fetch_facebook(), 1.5))
            tasks.append(self._delayed_task(self.fetch_instagram(), 3.0))
        
        await asyncio.gather(*tasks)
        print(f"--- EXTRACTION COMPLETE: FOUND {self.result_count} TOTAL SOURCES ---\n")
        return self.aggregated_data

    async def _delayed_task(self, coro, delay):
        await asyncio.sleep(delay)
        await coro

def execute_deep_social_extraction(keywords_list, scope_id):
    extractor = EliteOSINTExtractor(keywords_list, scope_id)
    return asyncio.run(extractor.run_all())
