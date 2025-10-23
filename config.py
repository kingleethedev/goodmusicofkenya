# config.py
import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2025'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///kenyan_music.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # YouTube API Configuration - Multiple keys
    YOUTUBE_API_KEYS = [
        os.environ.get('YOUTUBE_API_KEY_1', 'your-first-api-key-here'),
        os.environ.get('YOUTUBE_API_KEY_2', 'your-second-api-key-here')
    ]
    
    # Remove empty keys if any
    YOUTUBE_API_KEYS = [key for key in YOUTUBE_API_KEYS if key and key != 'your-first-api-key-here' and key != 'your-second-api-key-here']
    
    # Gemini API Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key-here'
    
    # Scheduler Configuration
    SCHEDULER_INTERVAL_HOURS = int(os.environ.get('SCHEDULER_INTERVAL_HOURS', 6))
    
    # Application Settings
    SONGS_PER_PAGE = 12
    ARTISTS_PER_PAGE = 24
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'images')
    
    # Ensure upload folder exists
    @classmethod
    def init_app(cls, app):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)