import asyncio
import os
import urllib.parse
import requests
import feedparser
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from googlenewsdecoder import gnewsdecoder
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# --- CONSTANTS & CONFIG (UPGRADED TO 48 HOURS) ---
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
    def __init__(self, target_figure):
        self.target_figure = target_figure
        self.aggregated_data = ""

    def _append_payload(self, platform, content, url, interactions, reach):
        payload = f"""
        [PLATFORM: {platform}]
        [URL: {url}]
        [INTERACTIONS/COMMENTS: {interactions}]
        [REACH/VIEWS: {reach}]
        [CONTENT: {content[:1500]}] 
        """
        print(f"\n[PAYLOAD READY] -> {platform} | Interactions: {interactions} | Reach: {reach}")
        self.aggregated_data += payload

    # =========================================================
    # CROSS-API INTERCEPTORS
    # =========================================================
    async def _process_web_link(self, url, title, snippet):
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
        try:
            resp = await asyncio.to_thread(requests.get, jina_url, headers=headers, timeout=15)
            full_text = resp.text if resp.status_code == 200 else snippet
        except:
            full_text = snippet
        self._append_payload("Google Mega Web", full_text, url, "N/A", "N/A")

    async def _process_ig_link(self, url, title):
        if not RAPID_API_KEY or not RAPID_HOST_IG: return
        details_url = f"https://{RAPID_HOST_IG}/get_media_data.php"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_IG}
        try:
            resp = await asyncio.to_thread(requests.get, details_url, headers=headers, params={"reel_post_code_or_url": url, "type": "post"})
            data = resp.json()
            likes = data.get('data', {}).get('like_count', 0)
            comments = data.get('data', {}).get('comment_count', 0)
            self._append_payload("Instagram (via Mega)", title, url, f"{likes} Likes, {comments} Commentaires", "N/A")
        except:
            self._append_payload("Instagram (via Mega)", title, url, "N/A", "N/A")

    async def _process_fb_link(self, url, title):
        if not RAPID_API_KEY or not RAPID_HOST_FB: return
        fb_match = re.search(r'(?:posts/|fbid=|v=|/p/|videos/)([0-9]+)', url)
        if not fb_match:
            self._append_payload("Facebook (via Mega)", title, url, "N/A", "N/A")
            return
        post_id = fb_match.group(1)
        details_url = f"https://{RAPID_HOST_FB}/post/reactions"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_FB}
        try:
            resp = await asyncio.to_thread(requests.get, details_url, headers=headers, params={"post_id": post_id, "reaction_type": "like"})
            data = resp.json()
            likes = data.get('count', len(data.get('results', [])))
            self._append_payload("Facebook (via Mega)", title, url, f"{likes} Réactions", "N/A")
        except:
            self._append_payload("Facebook (via Mega)", title, url, "N/A", "N/A")

    # =========================================================
    # 1. RSS NEWS MEDIA (Maximum Web Extraction)
    # =========================================================
    async def fetch_news_media(self):
        encoded_name = urllib.parse.quote(self.target_figure)
        if is_arabic(self.target_figure):
            rss_url = f"https://news.google.com/rss/search?q={encoded_name}+when:2d&hl=ar&gl=MA&ceid=MA:ar"
        else:
            rss_url = f"https://news.google.com/rss/search?q={encoded_name}+when:2d&hl=en-US&gl=US&ceid=US:en"

        try:
            print(f"⏳ Calling Google RSS News (Unlimited 48h)...")
            feed = await asyncio.to_thread(feedparser.parse, rss_url)
            
            for item in feed.entries:
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
                
                # Appending with a larger character limit for web articles
                self._append_payload("News Media (RSS)", full_text[:2500], final_url, "N/A", "N/A")
                await asyncio.sleep(0.2) 
        except Exception as e:
            print(f"❌ RSS News Error: {e}")

    # =========================================================
    # 2. GOOGLE MEGA SEARCH (Fixed JSON Parsing for Deep Web)
    # =========================================================
    async def fetch_google_mega(self):
        if not RAPID_API_KEY: return
        url = f"https://{RAPID_HOST_GOOGLE}/search"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_GOOGLE}
        languages = ['ar', 'fr', 'en']
        
        for lang in languages:
            try:
                await asyncio.sleep(1)
                if lang == 'ar' and is_arabic(self.target_figure):
                    translated_name = self.target_figure
                else:
                    translator = GoogleTranslator(source='auto', target=lang)
                    translated_name = await asyncio.to_thread(translator.translate, self.target_figure)
                
                if lang == 'ar': dorked_query = f"{translated_name} المغرب OR site:.ma"
                elif lang == 'fr': dorked_query = f"{translated_name} Maroc OR site:.ma"
                else: dorked_query = f"{translated_name} Morocco OR site:.ma"

                print(f"⏳ Calling Google Mega Search | Lang: {lang.upper()} | Query: {dorked_query}")
                
                params = {"q": dorked_query, "gl": "ma", "hl": lang, "tbs": "sbd:1,qdr:d2", "autocorrect": "true", "num": "30", "page": "1"}
                
                resp = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
                data = resp.json()
                
                # --- THE FIX: Broadening the JSON search to catch the web articles ---
                results = data.get('organic_results', data.get('organic', data.get('items', data.get('results', data.get('data', [])))))
                
                for item in results:
                    link = item.get('url', item.get('link', ''))
                    title = item.get('title', '')
                    snippet = item.get('description', item.get('snippet', ''))
                    
                    if not link: continue
                    if 'instagram.com' in link:
                        await self._process_ig_link(link, snippet)
                    elif 'facebook.com' in link:
                        await self._process_fb_link(link, snippet)
                    elif 'youtube.com' in link:
                        continue # Skip to avoid duplicating our direct YT extraction
                    else:
                        await self._process_web_link(link, title, snippet)
                    await asyncio.sleep(0.3) 
            except Exception as e:
                print(f"❌ Google Mega Error ({lang}): {e}")

    # =========================================================
    # 3. YOUTUBE (48 Hours - NO LIMITS)
    # =========================================================
    async def fetch_youtube(self):
        if not YT_API_KEY: return
        query = urllib.parse.quote(self.target_figure)
        # maxResults=50 pulls the absolute maximum allowed per API call
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&publishedAfter={ISO_48H_AGO.replace('+00:00', 'Z')}&type=video&key={YT_API_KEY}&maxResults=50"
        try:
            print(f"⏳ Calling YouTube API (Unlimited 48h)...")
            response = await asyncio.to_thread(requests.get, url)
            data = response.json()
            
            # NO SLICE LIMITS
            for item in data.get('items', []):
                video_id = item['id']['videoId']
                stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YT_API_KEY}"
                stats_resp = await asyncio.to_thread(requests.get, stats_url)
                stats = stats_resp.json()['items'][0]['statistics']
                comments = stats.get('commentCount', '0')
                views = stats.get('viewCount', '0')
                self._append_payload("YouTube", item['snippet']['title'], f"https://youtu.be/{video_id}", comments, views)
        except Exception as e:
            print(f"❌ YouTube Error: {e}")

    # =========================================================
    # 4. INSTAGRAM (48 Hours - NO LIMITS)
    # =========================================================
    async def fetch_instagram(self):
        RAPID_HOST_IG = os.getenv("RAPIDAPI_HOST_INSTAGRAM")
        if not RAPID_API_KEY or not RAPID_HOST_IG: return
        search_url = f"https://{RAPID_HOST_IG}/search_hashtag.php"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_IG}
        hashtag = self.target_figure.replace(" ", "")
        try:
            print(f"⏳ Calling Instagram Search API for #{hashtag} (Unlimited 48h)...")
            response = await asyncio.to_thread(requests.get, search_url, headers=headers, params={"hashtag": hashtag})
            data = response.json()
            edges = data.get('posts', {}).get('edges', [])
            
            # NO COUNT LIMITS
            for edge in edges:
                node = edge.get('node', {})
                timestamp = node.get('taken_at_timestamp', 0)
                # 48 HOUR FILTER
                if timestamp > 0 and timestamp < UNIX_48H_AGO: continue 
                
                shortcode = node.get('shortcode', '')
                if not shortcode: continue
                url = f"https://www.instagram.com/p/{shortcode}/"
                text = "IG Post"
                caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                if caption_edges: text = caption_edges[0].get('node', {}).get('text', 'IG Post')
                likes = node.get('edge_liked_by', {}).get('count', 0)
                comments = node.get('edge_media_to_comment', {}).get('count', 0)
                self._append_payload("Instagram", text, url, f"{likes} Likes, {comments} Commentaires", "N/A")
        except Exception as e:
            print(f"❌ Instagram Crash Error: {e}")

    # =========================================================
    # 5. FACEBOOK (48 Hours - NO LIMITS)
    # =========================================================
    async def fetch_facebook(self):
        RAPID_HOST_FB = os.getenv("RAPIDAPI_HOST_FACEBOOK")
        if not RAPID_API_KEY or not RAPID_HOST_FB: return
        search_url = f"https://{RAPID_HOST_FB}/search/global"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_FB}
        # Start date upgraded to 48 Hours ago
        params = {"query": self.target_figure, "recent_posts": "true", "start_date": FORTY_EIGHT_HOURS_AGO.strftime('%Y-%m-%d'), "end_date": NOW.strftime('%Y-%m-%d')}
        try:
            print(f"⏳ Calling Facebook Global API for {self.target_figure} (Unlimited 48h)...")
            response = await asyncio.to_thread(requests.get, search_url, headers=headers, params=params)
            data = response.json()
            
            # NO SLICE LIMITS
            posts = data.get('results', data.get('data', []))
            
            for post in posts:
                text = post.get('message', post.get('text', '')) 
                url = post.get('url', 'Facebook Search Result')
                if not text: continue
                likes = post.get('reactions_count', post.get('likes', 0))
                comments = post.get('comments_count', post.get('comments', 0))
                shares = post.get('reshare_count', post.get('shares', 0))
                self._append_payload("Facebook", text, url, f"{likes} Réactions, {comments} Commentaires", f"{shares} Partages")
        except Exception as e:
            print(f"❌ Facebook Crash Error: {e}")

    # =========================================================
    # ORCHESTRATION 
    # =========================================================
    async def _delayed_task(self, coro, delay):
        await asyncio.sleep(delay)
        await coro

    async def run_all(self):
        print("\n--- DEPLOYING GOD MODE OSINT EXTRACTORS (48H / UNLIMITED) ---")
        
        await asyncio.gather(
            self.fetch_news_media(),                             
            self.fetch_youtube(),                                
            self._delayed_task(self.fetch_facebook(), 1.5),      
            self._delayed_task(self.fetch_instagram(), 3.0),     
            self._delayed_task(self.fetch_google_mega(), 4.5)    
        )
        print("--- OSINT EXTRACTION COMPLETE ---\n")
        return self.aggregated_data

def execute_deep_social_extraction(figure_name):
    extractor = EliteOSINTExtractor(figure_name)
    return asyncio.run(extractor.run_all())
