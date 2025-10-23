import requests
from flask import current_app, url_for
from datetime import datetime, timedelta, timezone
import time
import re
import concurrent.futures
from app import db
from app.models import Artist, Song

class YouTubeService:
    def __init__(self):
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.api_keys = current_app.config.get('YOUTUBE_API_KEYS', [])
        if not isinstance(self.api_keys, list) or not self.api_keys:
            raise RuntimeError("YOUTUBE_API_KEYS must be a non-empty list in config")

        self.current_key_index = 0
        self.default_thumbnail = url_for('static', filename='images/default_album.jpg', _external=False)
        self.api_delay = 1.0  # Reduced delay
        self.timeout = 10  # Reduced timeout
        
        # Cache for channel info to avoid repeated API calls
        self.channel_cache = {}
        self.cache_ttl = timedelta(hours=24)
        
        # Batch size for parallel processing
        self.batch_size = 5

        # 🔥 More natural, human-like Kenyan music search queries (2025-focused)
        self.search_queries = [
            # General Kenyan music searches
            "New Kenyan official music video 2025",
            "Latest Kenyan songs 2025",
            "Kenyan AfroPop official music video",
            "Kenya Bongo and Afrobeat songs 2025",
            "Nairobi music release this week",
            "Kenya trending music videos 2025",
            "Top Kenyan hits 2025",
            "Kenyan RnB official video 2025",
            "Kenya Hip Hop official release 2025",
            "New gengetone song 2025",
            "#Njerae  ",
            "watendawili music",
            "cedo",
            "tipsy gee",
            "costa ojwang",
            "Bensoul",
            "BURUKLYNBOYZ",
            "Nikita Kering",
            "Toxic lyrikali",
            "Nyashinski",
             "Xenia Manasseh",
    "Karun",
    "Muthaka",
    "Lisa Oduor-Noah",
    "Kui Ciu",
    "Okello Max",
     "Prince Indah",
     "Watendawili",
            

            # Artist-based queries
            "Nyashinski new song 2025",
            "Bensoul latest song 2025",
            "Buruklyn Boyz new track 2025",
            "Teslah new release 2025",
            "Nikita Kering new video 2025",
            "Khaligraph Jones official video 2025",
            "Otile Brown latest song 2025",
            "Iyanii new hit 2025",
            "Savara or Bien new song 2025",
            

            # Broader category searches
            "Kenyan official gospel song 2025",
            "Kenyan love song 2025",
            
            "Kenya Top Charts 2025 music",
            "Kenyan YouTube trending official video",
            "Kenya latest audio release 2025",
            "Best new Kenyan artists 2025",

            # Additional open searches
            "New Kenyan hit song",
            "Kenyan music video premiere 2025",
            "Kenya official music 2025 latest",
           
        ]

    def get_current_api_key(self):
        return self.api_keys[self.current_key_index]

    def rotate_api_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return self.get_current_api_key()

    def search_kenyan_music(self):
        """Searches YouTube for verified Kenyan music uploaded in the last 30 days."""
        all_videos = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        cutoff_iso = cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"🎯 Searching for Kenyan music (last 30 days)")
        print(f"📅 Cutoff: {cutoff_iso}")

        # Process queries in batches for better performance
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_query = {
                executor.submit(self._search_artist_2025, query, cutoff_date): query 
                for query in self.search_queries
            }
            
            for future in concurrent.futures.as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    videos = future.result()
                    all_videos.extend(videos)
                    print(f"🔎 Query '{query}': {len(videos)} results")
                except Exception as e:
                    print(f"⚠️ Query '{query}' failed: {e}")

        unique = self._remove_duplicates(all_videos)
        filtered = self._filter_2025_content(unique)

        # ✅ Keep only the top 50 newest verified Kenyan songs
        filtered = filtered[:50]

        print(f"🎵 Final selection: {len(filtered)} new Kenyan songs")
        return filtered

    def _search_artist_2025(self, search_term, cutoff_date):
        videos = []
        api_key = self.get_current_api_key()
        
        params = {
            'part': 'snippet',
            'q': search_term,
            'type': 'video',
            'videoCategoryId': '10',  # Music category
            'regionCode': 'KE',
            'maxResults': 50,
            'order': 'date',
            'publishedAfter': cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'key': api_key
        }

        try:
            resp = requests.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
            if resp.status_code != 200:
                print(f"  YouTube API error ({resp.status_code}): {resp.text[:200]}")
                self.rotate_api_key()
                return videos

            items = resp.json().get('items', [])
            
            # Process videos in parallel batches
            video_batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
            
            for batch in video_batches:
                batch_results = self._process_video_batch(batch, search_term, cutoff_date)
                videos.extend([v for v in batch_results if v])
                
            self.rotate_api_key()
            time.sleep(self.api_delay)
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout for query: {search_term}")
        except Exception as e:
            print(f"❌ Error in _search_artist_2025: {e}")

        return videos

    def _process_video_batch(self, batch, search_term, cutoff_date):
        """Process a batch of videos in parallel."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_video = {
                executor.submit(self._process_2025_video, item, search_term, cutoff_date): item 
                for item in batch
            }
            
            for future in concurrent.futures.as_completed(future_to_video):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"⚠️ Video processing error: {e}")
        return results

    def _process_2025_video(self, item, search_term, cutoff_date):
        try:
            video_id = item.get('id', {}).get('videoId')
            if not video_id:
                return None

            snippet = item.get('snippet', {})
            published_at = snippet.get('publishedAt')
            if not published_at:
                return None

            # Fast date parsing without full ISO parsing
            try:
                published_str = published_at.replace('Z', '').replace('T', ' ').split('.')[0]
                published_dt = datetime.strptime(published_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            except:
                return None

            if published_dt < cutoff_date:
                return None

            title = snippet.get('title', '')
            channel_title = snippet.get('channelTitle', '')
            channel_id = snippet.get('channelId')

            # ✅ Quick pre-filter before API call
            if not self._quick_pre_filter(title, channel_title):
                return None

            # ✅ Check channel info with caching
            channel_info = self._get_cached_channel_info(channel_id)
            if not channel_info:
                return None

            is_kenyan = channel_info.get("country") == "KE"
            subs = channel_info.get("subs", 0)
            if not is_kenyan or subs < 10000:
                return None

            # ✅ Filter official releases only
            if not self._is_2025_official_release(title, channel_title, search_term):
                return None

            thumbnail_url = snippet.get('thumbnails', {}).get('high', {}).get('url', self.default_thumbnail)

            return {
                'video_id': video_id,
                'title': self._generate_ai_title(title, channel_title),
                'channel_title': channel_title,
                'published_at': published_dt,
                'thumbnail_url': thumbnail_url,
                'youtube_url': f"https://www.youtube.com/watch?v={video_id}",
                'verified_artist': channel_title,
                'original_title': title
            }

        except Exception as e:
            print(f"  Error processing video item: {e}")
            return None

    def _quick_pre_filter(self, title, channel_title):
        """Quick filter to avoid API calls for obviously non-music content."""
        title_lower = title.lower()
        quick_exclude = ['reaction', 'mix', 'dj', 'interview', 'podcast', 'compilation', 'lyrics', 'shorts']
        return not any(x in title_lower for x in quick_exclude)

    def _get_cached_channel_info(self, channel_id):
        """Get channel info with caching to avoid repeated API calls."""
        if not channel_id:
            return None
            
        # Check cache first
        cache_entry = self.channel_cache.get(channel_id)
        if cache_entry and datetime.now(timezone.utc) - cache_entry['timestamp'] < self.cache_ttl:
            return cache_entry['data']
            
        # Fetch from API
        channel_info = self._get_channel_info(channel_id)
        if channel_info:
            self.channel_cache[channel_id] = {
                'data': channel_info,
                'timestamp': datetime.now(timezone.utc)
            }
        return channel_info

    def _get_channel_info(self, channel_id):
        api_key = self.get_current_api_key()
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': api_key
        }
        
        try:
            resp = requests.get(f"{self.base_url}/channels", params=params, timeout=8)  # Reduced timeout
            if resp.status_code != 200:
                return None

            data = resp.json().get("items", [])
            if not data:
                return None

            info = data[0]
            snippet = info.get("snippet", {})
            statistics = info.get("statistics", {})

            country = snippet.get("country", "")
            subs = int(statistics.get("subscriberCount", 0)) if "subscriberCount" in statistics else 0
            return {"country": country, "subs": subs}
            
        except requests.exceptions.Timeout:
            print(f"⏰ Channel info timeout for {channel_id}")
            return None
        except Exception as e:
            print(f"❌ Channel info error for {channel_id}: {e}")
            return None

    def _generate_placeholder_thumbnail(self, artist_name, song_title):
        """Generate a lightweight AI placeholder image URL."""
        return url_for('static', filename='images/default_album.jpg', _external=False)

    def _is_2025_official_release(self, title, channel_title, search_term):
        title_lower = title.lower()
        
        # Fast exclusion check
        exclude = ['reaction', 'mix', 'dj', 'interview', 'podcast', 'compilation', 'lyrics', 'cover', 'behind the scenes', 'challenge', 'dance', 'shorts']
        if any(x in title_lower for x in exclude):
            return False

        # Fast inclusion check
        include_indicators = ['official', 'music video', 'official video', 'audio', 'single', 'release']
        if any(x in title_lower for x in include_indicators):
            return True
            
        if 'official' in channel_title.lower():
            return True

        return False

    def _generate_ai_title(self, original_title, artist):
        # Faster title cleaning using simpler string operations
        title = original_title
        for pattern in ['official', 'video', 'lyrics', 'HD', '4K']:
            title = title.replace(pattern, '').replace(pattern.upper(), '')
        
        # Remove content in brackets more efficiently
        title = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        if artist.lower() not in title.lower():
            title = f"{title} - {artist}"
        return title.title()

    def _remove_duplicates(self, videos):
        seen = set()
        unique = []
        for v in videos:
            vid = v.get('video_id')
            if vid and vid not in seen:
                seen.add(vid)
                unique.append(v)
        return unique

    def _filter_2025_content(self, videos):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        filtered = [
            v for v in videos
            if v['published_at'] >= cutoff and not any(x in v['title'].lower() for x in ['mix', 'cover', 'reaction'])
        ]
        filtered.sort(key=lambda x: x['published_at'], reverse=True)
        return filtered

    def save_videos_to_db(self, videos):
        """Save videos to database with proper artist ID handling."""
        if not videos:
            print("📭 No new videos to save")
            return 0

        saved_count = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        for v in videos:
            try:
                if v['published_at'] < cutoff:
                    continue

                # Check if song already exists
                if Song.query.filter_by(youtube_id=v['video_id']).first():
                    continue

                # Find or create artist
                artist = Artist.query.filter_by(name=v['channel_title']).first()
                if not artist:
                    artist = Artist(name=v['channel_title'])
                    db.session.add(artist)
                    db.session.flush()  # This gets the artist ID

                # Create song
                song = Song(
                    title=v['title'],
                    artist_id=artist.id,
                    release_date=v['published_at'],
                    youtube_url=v['youtube_url'],
                    youtube_id=v['video_id'],
                    thumbnail_url=v.get('thumbnail_url', self.default_thumbnail)
                )
                db.session.add(song)
                saved_count += 1

                days_ago = (datetime.now(timezone.utc) - v['published_at']).days
                print(f"💾 Saved: {v['title']} ({days_ago} days ago)")

            except Exception as e:
                print(f"❌ Error saving video {v.get('video_id')}: {e}")
                db.session.rollback()
                continue

        try:
            db.session.commit()
            print(f"🎉 Saved {saved_count} new Kenyan songs!")
        except Exception as e:
            print(f"❌ Commit error: {e}")
            db.session.rollback()
            return 0

        return saved_count

    def update_music_library(self):
        """Main method to update the music library - combines search and save."""
        print("🚀 Starting Kenyan music library update...")
        
        start_time = time.time()
        
        try:
            # Search for new Kenyan music
            videos = self.search_kenyan_music()
            
            # Save to database
            saved_count = self.save_videos_to_db(videos)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Update completed in {duration:.2f} seconds")
            print(f"📊 Results: {len(videos)} found, {saved_count} saved")
            
            return {
                'status': 'success',
                'videos_found': len(videos),
                'videos_saved': saved_count,
                'duration_seconds': round(duration, 2)
            }
            
        except Exception as e:
            print(f"❌ Update failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
