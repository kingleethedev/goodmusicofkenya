from app import db
from datetime import datetime
import google.generativeai as genai
from flask import current_app
import os
from datetime import timezone

class Artist(db.Model):
    __tablename__ = 'artists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    songs = db.relationship('Song', backref='artist', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Artist {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'genre': self.genre,
            'location': self.location,
            'is_verified': self.is_verified,
            'song_count': len(self.songs),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def generate_ai_description(self):
        """Generate artist description using Gemini AI"""
        try:
            from app.services.gemini_service import GeminiService
            
            gemini_service = GeminiService()
            if not gemini_service.is_available():
                print("⚠️ Gemini service not available")
                return None
                
            # Get artist context from their songs
            song_titles = [song.title for song in self.songs[:5]]  # Get first 5 songs for context
            
            description = gemini_service.generate_artist_description(self.name, song_titles)
            if description:
                self.description = description
                self.updated_at = datetime.utcnow()
                db.session.commit()
                
                print(f"✅ Generated AI description for {self.name}")
                return self.description
                
        except Exception as e:
            print(f"❌ Error generating description for {self.name}: {e}")
            return None
        
        return None
    
    def get_top_songs(self, limit=5):
        """Get top songs by view count or recent releases"""
        return sorted(self.songs, key=lambda x: x.view_count, reverse=True)[:limit]
    
    def get_recent_songs(self, limit=5):
        """Get most recent songs"""
        return sorted(self.songs, key=lambda x: x.release_date, reverse=True)[:limit]
    
    def get_songs_count_by_year(self):
        """Get song count by year for analytics"""
        from collections import defaultdict
        year_counts = defaultdict(int)
        for song in self.songs:
            year = song.release_date.year
            year_counts[year] += 1
        return dict(year_counts)

class Song(db.Model):
    __tablename__ = 'songs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    release_date = db.Column(db.DateTime, nullable=False)
    youtube_url = db.Column(db.String(500), nullable=False)
    youtube_id = db.Column(db.String(50), unique=True, nullable=False)
    thumbnail_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    duration = db.Column(db.String(20), nullable=True)  # e.g., "3:45"
    genre = db.Column(db.String(100), nullable=True)
    is_explicit = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        # Ensure release_date is timezone-aware if provided
        if 'release_date' in kwargs and kwargs['release_date']:
            if kwargs['release_date'].tzinfo is None:
                kwargs['release_date'] = kwargs['release_date'].replace(tzinfo=timezone.utc)
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<Song {self.title} by {self.artist.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist.name,
            'artist_id': self.artist_id,
            'release_date': self.release_date.isoformat(),
            'youtube_url': self.youtube_url,
            'youtube_id': self.youtube_id,
            'thumbnail_url': self.thumbnail_url,
            'image_url': self.image_url,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'duration': self.duration,
            'genre': self.genre,
            'is_explicit': self.is_explicit,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def generate_ai_description(self):
        """Generate song description using Gemini AI"""
        try:
            from app.services.gemini_service import GeminiService
            
            gemini_service = GeminiService()
            if not gemini_service.is_available():
                return None
                
            description = gemini_service.generate_song_description(self.title, self.artist.name)
            return description
                
        except Exception as e:
            print(f"❌ Error generating song description for {self.title}: {e}")
            return None
        
        return None
    
    def get_youtube_embed_url(self):
        """Get YouTube embed URL"""
        return f"https://www.youtube.com/embed/{self.youtube_id}"
    
    def get_days_since_release(self):
        """Get days since release"""
        # Ensure both datetimes are timezone-aware for comparison
        if self.release_date.tzinfo is None:
            release_date = self.release_date.replace(tzinfo=timezone.utc)
        else:
            release_date = self.release_date
            
        now = datetime.now(timezone.utc)
        delta = now - release_date
        return delta.days
    
    def is_recent(self, days=30):
        """Check if song was released in the last N days"""
        return self.get_days_since_release() <= days

# Analytics and Helper Models
class MusicStats(db.Model):
    __tablename__ = 'music_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    total_songs = db.Column(db.Integer, default=0)
    total_artists = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    most_popular_artist = db.Column(db.String(100))
    most_viewed_song = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def update_stats(self):
        """Update all music statistics"""
        from sqlalchemy import func
        
        self.total_songs = Song.query.count()
        self.total_artists = Artist.query.count()
        self.total_views = db.session.query(func.sum(Song.view_count)).scalar() or 0
        
        # Most popular artist (by total views)
        popular_artist = db.session.query(
            Artist.name, func.sum(Song.view_count).label('total_views')
        ).join(Song).group_by(Artist.id).order_by(func.sum(Song.view_count).desc()).first()
        
        if popular_artist:
            self.most_popular_artist = popular_artist[0]
        
        # Most viewed song
        most_viewed = Song.query.order_by(Song.view_count.desc()).first()
        if most_viewed:
            self.most_viewed_song = most_viewed.title
        
        self.last_updated = datetime.utcnow()
        db.session.commit()

class Genre(db.Model):
    __tablename__ = 'genres'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Genre {self.name}>'

# Common Kenyan genres (you can pre-populate these)
KENYAN_GENRES = [
    "Gengetone", "Afro-pop", "Gospel", "Benga", "Ohangla", "Hip Hop",
    "RnB", "Reggae", "Dancehall", "Zilizopendwa", "Kapuka", "Genge",
    "Afro-fusion", "Afrobeats", "Bongo Flava", "Mugithi", "Taarab"
]