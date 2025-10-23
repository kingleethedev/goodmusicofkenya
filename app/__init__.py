from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import os

# Initialize extensions
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Set secret key for sessions (CRITICAL FIX)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2025'
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Import models to ensure they are registered with SQLAlchemy
    from app import models
    
    # Add custom Jinja2 filters
    @app.template_filter('number_format')
    def number_format(value):
        """Format numbers with commas"""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value
    
    @app.template_filter('truncate')
    def truncate(text, length=50):
        """Truncate text to specified length"""
        if len(text) <= length:
            return text
        return text[:length] + '...'
    
    # Initialize scheduler
    scheduler = BackgroundScheduler(daemon=True)
    
    def scheduled_update():
        with app.app_context():
            try:
                from app.services.youtube_service import YouTubeService
                from app.services.gemini_service import GeminiService
                
                youtube_service = YouTubeService()
                
                # Fetch new videos
                print("🎵 Starting scheduled music update...")
                videos = youtube_service.search_kenyan_music()
                saved_count = youtube_service.save_videos_to_db(videos)
                
                print(f"✅ Scheduled update: Added {saved_count} new songs")
                
                # Generate images for new songs without images (if Gemini is available)
                if saved_count > 0:
                    try:
                        gemini_service = GeminiService()
                        from app.models import Song
                        
                        # Get the newly added songs
                        new_songs = Song.query.order_by(Song.created_at.desc()).limit(saved_count).all()
                        images_generated = 0
                        
                        for song in new_songs:
                            if not song.image_url:
                                image_url = gemini_service.generate_image(
                                    song.title, 
                                    song.artist.name, 
                                    song.release_date.strftime('%Y-%m-%d')
                                )
                                if image_url:
                                    song.image_url = image_url
                                    images_generated += 1
                        
                        db.session.commit()
                        print(f"🎨 Generated {images_generated} new images")
                        
                    except Exception as gemini_error:
                        print(f"⚠️ Gemini image generation skipped: {gemini_error}")
                
                print("✅ Scheduled update completed successfully!")
                
            except Exception as e:
                print(f"❌ Error in scheduled update: {str(e)}")
    
    # Schedule the job
    try:
        scheduler.add_job(
            func=scheduled_update,
            trigger="interval",
            hours=app.config.get('SCHEDULER_INTERVAL_HOURS', 6),  # Default to 6 hours
            id='update_music_data'
        )
        scheduler.start()
        print(f"⏰ Scheduler started successfully (runs every {app.config.get('SCHEDULER_INTERVAL_HOURS', 6)} hours)")
    except Exception as e:
        print(f"❌ Error starting scheduler: {e}")
    
    # Create tables and handle database migration
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Check if we need to migrate the database schema
            from app.routes import check_database_schema, migrate_database
            if not check_database_schema():
                print("🔄 Migrating database schema...")
                if migrate_database():
                    print("✅ Database migration completed!")
                else:
                    print("❌ Database migration failed!")
            else:
                print("✅ Database schema is up to date!")
                
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")

    @app.template_filter('days_ago')
    def days_ago_filter(dt):
        """Calculate days ago from a datetime"""
        from datetime import datetime, timezone
        if not dt:
            return "Unknown"
        try:
            # Ensure both datetimes are timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - dt
            return delta.days
        except Exception:
            return "Unknown"
    
    @app.template_filter('is_recent')
    def is_recent_filter(dt, days=30):
        """Check if datetime is within last N days"""
        from datetime import datetime, timezone, timedelta
        if not dt:
            return False
        try:
            # Ensure both datetimes are timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            return dt >= cutoff
        except Exception:
            return False
    
    @app.context_processor
    def utility_processor():
        """Add utility functions to templates"""
        from datetime import datetime, timezone
        return {
            'now': lambda: datetime.now(timezone.utc),
            'timezone': timezone
        }
    
    
    return app