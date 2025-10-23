import re
import random
from datetime import datetime

class TitleService:
    def __init__(self):
        self.kenyan_themes = [
            "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret",
            "Savannah", "Kilimanjaro", "Masai", "Samburu", "Kalenjin",
            "Luo", "Kikuyu", "Luhya", "Kamba", "Swahili",
            "Uhuru", "Harambee", "Sauti", "Moyo", "Roho"
        ]
        
        self.music_words = [
            "Rhythm", "Melody", "Harmony", "Beat", "Flow",
            "Vibe", "Groove", "Sound", "Tune", "Note",
            "Voice", "Chorus", "Verse", "Hook", "Bridge"
        ]
        
        self.emotional_words = [
            "Love", "Heart", "Soul", "Dream", "Hope",
            "Joy", "Pain", "Fire", "Ice", "Rain",
            "Sun", "Moon", "Stars", "Sky", "Ocean"
        ]
    
    def generate_ai_title(self, original_title, artist):
        """Generate creative AI-style title"""
        # First, clean the original title
        clean_title = self._clean_youtube_title(original_title)
        
        # If clean title is good, use it
        if self._is_good_title(clean_title):
            return clean_title
        
        # Otherwise generate creative title
        return self._generate_creative_title(artist)
    
    def _clean_youtube_title(self, title):
        """Remove YouTube clutter from titles"""
        # Remove common YouTube patterns
        patterns = [
            r'\(official.*?\)', r'\[official.*?\]', r'official music video',
            r'official video', r'\(.*?\)', r'\[.*?\]', r'#\w+',
            r'\b\d{4}\b', r'\bHD\b', r'\b4K\b', r'\blyrics?\b',
            r'\bvideo\b', r'\baudio\b', r'\bvisualizer\b'
        ]
        
        clean = title
        for pattern in patterns:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
        
        # Clean up
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = re.sub(r'^[-\s]*|[-\s]*$', '', clean)
        
        return clean
    
    def _is_good_title(self, title):
        """Check if title is already good"""
        if len(title) < 5 or len(title) > 50:
            return False
        
        bad_indicators = ['mix', 'dj', 'compilation', 'mashup', 'ft.', 'feat.']
        if any(indicator in title.lower() for indicator in bad_indicators):
            return False
        
        return True
    
    def _generate_creative_title(self, artist):
        """Generate creative Kenyan music title"""
        theme = random.choice(self.kenyan_themes)
        music_word = random.choice(self.music_words)
        emotion = random.choice(self.emotional_words)
        
        title_patterns = [
            f"{theme} {music_word}",
            f"{emotion} in {theme}",
            f"{theme} {emotion}",
            f"{music_word} of {theme}",
            f"{emotion} {music_word}",
            f"{theme} Nights",
            f"{emotion} {theme}",
            f"{music_word} {theme}"
        ]
        
        title = random.choice(title_patterns)
        return f"{title} - {artist}"