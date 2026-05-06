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

# # FORTY_EIGHT_HOURS_AGO = NOW - timedelta(days=2)
# UNIX_48H_AGO = int(FORTY_EIGHT_HOURS_AGO.timestamp())
# ISO_48H_AGO = FORTY_EIGHT_HOURS_AGO.isoformat()

TWELVE_HOURS_AGO = NOW - timedelta(hours=12)
UNIX_12H_AGO = int(TWELVE_HOURS_AGO.timestamp())
ISO_12H_AGO = TWELVE_HOURS_AGO.isoformat()

# Keys
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
RAPID_API_KEY = os.getenv("RAPIDAPI_KEY")
RAPID_HOST_IG = os.getenv("RAPIDAPI_HOST_INSTAGRAM")
RAPID_HOST_FB = os.getenv("RAPIDAPI_HOST_FACEBOOK")
RAPID_HOST_GOOGLE = os.getenv("RAPIDAPI_HOST_GOOGLE", "google-search-master-mega.p.rapidapi.com")

# --- FIXED: Matching exact .env variable names with bulletproof fallbacks ---
RAPID_HOST_TWITTER = os.getenv("RAPID_HOST_TWITTER", "twitter-api45.p.rapidapi.com")
RAPID_HOST_TIKTOK = os.getenv("RAPID_HOST_TIKTOK", "tiktok-api23.p.rapidapi.com")

def is_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

class EliteOSINTExtractor:
    def __init__(self, keywords_list, scope_id, log_callback=None): 
        self.keywords = keywords_list
        self.scope_id = scope_id
        self.log_callback = log_callback 
        self.main_kw = keywords_list[0] if keywords_list else ""
        
        self.aggregated_data = ""
        self.result_count = 0  
        
        # --- THE FIX: 15 max for Web/News, 50 max for Social Media ---
        self.max_results = 15 if self.scope_id == "PE" else 50  

    # Helper to print to terminal AND Streamlit UI
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
            # if is_arabic(kw):
            #     rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=ar&gl=MA&ceid=MA:ar"
            # else:
            #     rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=fr&gl=MA&ceid=MA:fr"

            if is_arabic(kw):
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:12h&hl=ar&gl=MA&ceid=MA:ar"
            else:
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:12h&hl=fr&gl=MA&ceid=MA:fr"

            try:
                self.log(f"⏳ Calling RSS News for: '{kw}'...")
                feed = await asyncio.to_thread(feedparser.parse, rss_url)
                
                entries = feed.entries
                if not entries:
                    self.log(f"⚠️ No RSS News found for '{kw}'.")
                else:
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
                
                self.log(f"⏳ Calling Google Mega Search | Dork: {dork[:50]}...")
                
                # params = {"q": dork, "gl": "ma", "hl": lang, "tbs": "sbd:1,qdr:d2", "autocorrect": "true", "num": "15", "page": "1"}

                params = {"q": dork, "gl": "ma", "hl": lang, "tbs": "sbd:1,qdr:h12", "autocorrect": "true", "num": "15", "page": "1"}

                resp = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
                
                # --- API HEALTH/QUOTA CHECK ---
                if resp.status_code != 200:
                    self.log(f"🚨 API ERROR [Google Mega]: Code {resp.status_code} -> {resp.text}")
                    continue

                data = resp.json()
                results = data.get('organic_results', data.get('results', data.get('items', [])))
                
                if not results:
                    self.log(f"⚠️ No Google Mega results found for '{kw}'.")
                else:
                    self.log(f"✅ Found {len(results)} Google Mega results for '{kw}'.")
                
                for item in results:
                    if self.result_count >= self.max_results: break
                    link = item.get('url', item.get('link', ''))
                    if not link: continue
                    
                    self.log(f"  🔗 [Google Mega] Investigating: {link}")

                    if 'instagram.com' in link or 'facebook.com' in link or 'youtube.com' in link: 
                        self.log("     ❌ Skipped: Social media link in PE scope")
                        continue 
                    else: 
                        await self._process_web_link(link, item.get('title', ''), item.get('snippet', ''))
                    await asyncio.sleep(0.3) 
            except Exception as e:
                self.log(f"❌ Google Mega Error: {e}") 

    # =========================================================
    # 3. YOUTUBE (RS ONLY) 
    # =========================================================
    async def fetch_youtube(self):
        if not YT_API_KEY or self.result_count >= self.max_results: return
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            query = urllib.parse.quote(f'"{kw}"')
            # url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&publishedAfter={ISO_48H_AGO.replace('+00:00', 'Z')}&type=video&key={YT_API_KEY}&maxResults=25"

            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&publishedAfter={ISO_12H_AGO.replace('+00:00', 'Z')}&type=video&key={YT_API_KEY}&maxResults=25"

            try:
                self.log(f"⏳ Calling YouTube API for '{kw}'...")
                response = await asyncio.to_thread(requests.get, url)
                
                # --- API HEALTH CHECK ---
                if response.status_code != 200:
                    self.log(f"🚨 API ERROR [YouTube]: Code {response.status_code} -> {response.text}")
                    continue
                    
                data = response.json()
                items = data.get('items', [])
                
                if not items:
                    self.log(f"⚠️ No YouTube videos found for '{kw}'.")
                else:
                    self.log(f"✅ Found {len(items)} YouTube videos for '{kw}'.")

                for item in items:
                    if self.result_count >= self.max_results: break
                    video_id = item['id']['videoId']
                    stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YT_API_KEY}"
                    stats_resp = await asyncio.to_thread(requests.get, stats_url)
                    stats = stats_resp.json()['items'][0]['statistics']
                    self._append_payload("YouTube", item['snippet']['title'], f"https://youtu.be/{video_id}", stats.get('commentCount', '0'), stats.get('viewCount', '0'))
            except Exception as e:
                self.log(f"❌ YouTube Crash: {e}")

    # =========================================================
    # 4. INSTAGRAM (RS ONLY)
    # =========================================================
    async def fetch_instagram(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_IG}/search_hashtag.php"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_IG}
        try:
            hashtag = self.main_kw.replace(" ", "")
            self.log(f"⏳ Calling Instagram for #{hashtag}...")
            response = await asyncio.to_thread(requests.get, search_url, headers=headers, params={"hashtag": hashtag})
            
            # --- API HEALTH CHECK ---
            if response.status_code != 200:
                self.log(f"🚨 API ERROR [Instagram]: Code {response.status_code} -> {response.text}")
                return
                
            edges = response.json().get('posts', {}).get('edges', [])
            
            if not edges:
                self.log(f"⚠️ No Instagram posts found for #{hashtag}.")
            else:
                self.log(f"✅ Found {len(edges)} Instagram posts for #{hashtag}.")

            for edge in edges:
                if self.result_count >= self.max_results: break
                node = edge.get('node', {})
                # if node.get('taken_at_timestamp', 0) < UNIX_48H_AGO: continue 
                if node.get('taken_at_timestamp', 0) < UNIX_12H_AGO: continue
                url = f"https://www.instagram.com/p/{node.get('shortcode')}/"
                cap = node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', 'IG Post')
                self._append_payload("Instagram", cap, url, f"{node.get('edge_liked_by', {}).get('count', 0)} Likes", "N/A")
        except Exception as e:
            self.log(f"❌ Instagram Crash: {e}")

    # =========================================================
    # 5. FACEBOOK (RS ONLY)
    # =========================================================
    async def fetch_facebook(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_FB}/search/global"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_FB}
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            # params = {"query": f'"{kw}"', "recent_posts": "true", "start_date": FORTY_EIGHT_HOURS_AGO.strftime('%Y-%m-%d'), "end_date": NOW.strftime('%Y-%m-%d')}

            params = {"query": f'"{kw}"', "recent_posts": "true", "start_date": TWELVE_HOURS_AGO.strftime('%Y-%m-%d'), "end_date": NOW.strftime('%Y-%m-%d')}

            try:
                self.log(f"⏳ Calling Facebook for '{kw}'...")
                response = await asyncio.to_thread(requests.get, search_url, headers=headers, params=params)
                
                # --- API HEALTH CHECK ---
                if response.status_code != 200:
                    self.log(f"🚨 API ERROR [Facebook]: Code {response.status_code} -> {response.text}")
                    continue
                    
                posts = response.json().get('results', [])
                
                if not posts:
                    self.log(f"⚠️ No Facebook posts found for '{kw}'.")
                else:
                    self.log(f"✅ Found {len(posts)} Facebook posts for '{kw}'.")

                for post in posts:
                    if self.result_count >= self.max_results: break
                    text = post.get('message', post.get('text', ''))
                    if not text: continue
                    self._append_payload("Facebook", text, post.get('url'), f"{post.get('reactions_count', 0)} Réactions", f"{post.get('reshare_count', 0)} Partages")
            except Exception as e:
                self.log(f"❌ Facebook Crash: {e}")

    # =========================================================
    # 6. X (TWITTER) (RS ONLY)
    # =========================================================
    async def fetch_twitter(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_TWITTER}/search.php"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_TWITTER}
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            params = {"query": f'"{kw}"', "search_type": "Latest"}
            try:
                self.log(f"⏳ Calling X (Twitter) for '{kw}'...")
                response = await asyncio.to_thread(requests.get, search_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    self.log(f"🚨 API ERROR [X/Twitter]: Code {response.status_code} -> {response.text}")
                    continue
                    
                tweets = response.json().get('timeline', [])
                
                if not tweets:
                    self.log(f"⚠️ No X (Twitter) posts found for '{kw}'.")
                else:
                    self.log(f"✅ Found {len(tweets)} X (Twitter) posts for '{kw}'.")

                for tweet in tweets:
                    if self.result_count >= self.max_results: break
                    if tweet.get('type') != 'tweet': continue
                    
                    # 1. Build the URL early so we can self.log it
                    tweet_id = tweet.get('tweet_id')
                    screen_name = tweet.get('user_info', {}).get('screen_name', 'i')
                    url = f"https://x.com/{screen_name}/status/{tweet_id}"
                    
                    self.log(f"  🔗 [X] Investigating: {url}")
                    
                    text = tweet.get('text', '')
                    if not text: continue
                    
                    # 2. Check the 12-hour rule with Strict Debugging
                    try:
                        tweet_date_str = tweet.get('created_at', '')
                        created_at = datetime.strptime(tweet_date_str, "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
                        if created_at < TWELVE_HOURS_AGO:
                            self.log("     ❌ Skipped: Plus vieux que 12 heures")
                            continue
                    except Exception as time_err:
                        self.log(f"     ⚠️ Impossible de parser l'heure X/Twitter (Bypass) : {time_err}")
                        continue 
                    
                    likes = tweet.get('favorites', 0)
                    retweets = tweet.get('retweets', 0)
                    views = tweet.get('views', '0')
                    
                    self._append_payload("X (Twitter)", text, url, f"{likes} Likes, {retweets} Reposts", f"{views} Vues")
            except Exception as e:
                self.log(f"❌ X (Twitter) Crash: {e}")

    # =========================================================
    # 7. TIKTOK (RS ONLY)
    # =========================================================
    async def fetch_tiktok(self):
        if not RAPID_API_KEY or self.result_count >= self.max_results: return
        search_url = f"https://{RAPID_HOST_TIKTOK}/api/search/video"
        headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_HOST_TIKTOK}
        
        for kw in self.keywords[:2]:
            if self.result_count >= self.max_results: break
            params = {"keyword": kw, "cursor": "0", "search_id": "0"}
            try:
                self.log(f"⏳ Calling TikTok for '{kw}'...")
                response = await asyncio.to_thread(requests.get, search_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    self.log(f"🚨 API ERROR [TikTok]: Code {response.status_code} -> {response.text}")
                    continue
                    
                videos = response.json().get('item_list', [])
                
                if not videos:
                    self.log(f"⚠️ No TikTok videos found for '{kw}'.")
                else:
                    self.log(f"✅ Found {len(videos)} TikTok videos for '{kw}'.")

                for video in videos:
                    if self.result_count >= self.max_results: break
                    
                    # 1. Build the URL early so we can self.log it
                    video_id = video.get('id')
                    author_id = video.get('author', {}).get('uniqueId', '_')
                    url = f"https://www.tiktok.com/@{author_id}/video/{video_id}"
                    
                    self.log(f"  🔗 [TikTok] Investigating: {url}")
                    
                    # 2. Check the 48-hour rule
                    create_time = video.get('createTime', 0)
                    # if create_time > 0 and create_time < UNIX_48H_AGO: 
                    #     self.log("     ❌ Skipped: Plus vieux que 48 heures")
                    #     continue

                    if create_time > 0 and create_time < UNIX_12H_AGO:
                        self.log("     ❌ Skipped: Plus vieux que 12 heures")
                        continue

                    text = video.get('desc', 'Vidéo TikTok')
                    stats = video.get('stats', {})
                    likes = stats.get('diggCount', 0)
                    comments = stats.get('commentCount', 0)
                    views = stats.get('playCount', 0)
                    
                    self._append_payload("TikTok", text, url, f"{likes} Likes, {comments} Commentaires", f"{views} Vues")
            except Exception as e:
                self.log(f"❌ TikTok Crash: {e}")

    # =========================================================
    # DYNAMIC ORCHESTRATOR
    # =========================================================
    async def run_all(self):
        self.log(f"\n--- DEPLOYING OSINT EXTRACTORS | SCOPE: {self.scope_id} (MAX {self.max_results}) ---")
        tasks = []
        
        if self.scope_id == "PE":
            tasks.append(self.fetch_news_media())
            tasks.append(self._delayed_task(self.fetch_google_mega(), 1.5))
        elif self.scope_id == "RS":
            tasks.append(self.fetch_youtube())
            tasks.append(self._delayed_task(self.fetch_facebook(), 1.5))
            tasks.append(self._delayed_task(self.fetch_instagram(), 3.0))
            tasks.append(self._delayed_task(self.fetch_twitter(), 4.5))
            tasks.append(self._delayed_task(self.fetch_tiktok(), 6.0))
        
        await asyncio.gather(*tasks)
        self.log(f"--- EXTRACTION COMPLETE: FOUND {self.result_count} TOTAL SOURCES ---\n")
        return self.aggregated_data

    # --- THE MISSING HELPER FUNCTION ---
    async def _delayed_task(self, coro, delay):
        await asyncio.sleep(delay)
        await coro

def execute_deep_social_extraction(keywords_list, scope_id, log_callback=None):
    extractor = EliteOSINTExtractor(keywords_list, scope_id, log_callback)
    return asyncio.run(extractor.run_all())
