from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app import db
from app.models import Artist, Song
from app.services.youtube_service import YouTubeService
from app.services.gemini_service import GeminiService
from datetime import datetime, timedelta, timezone
import sqlite3
import os

main_bp = Blueprint('main', __name__)

def check_database_schema():
    """Check and update database schema if needed"""
    try:
        # Test if new columns exist
        test_artist = Artist.query.first()
        if test_artist:
            # This will fail if columns don't exist
            _ = getattr(test_artist, 'description', None)
            _ = getattr(test_artist, 'genre', None)
            _ = getattr(test_artist, 'location', None)
            _ = getattr(test_artist, 'is_verified', None)
            _ = getattr(test_artist, 'updated_at', None)
        return True
    except Exception:
        return False

def migrate_database():
    """Migrate database to add new columns"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'kenyan_music.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check and add columns to artists table
        cursor.execute("PRAGMA table_info(artists)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'description' not in columns:
            cursor.execute('ALTER TABLE artists ADD COLUMN description TEXT')
        
        if 'genre' not in columns:
            cursor.execute('ALTER TABLE artists ADD COLUMN genre VARCHAR(100)')
        
        if 'location' not in columns:
            cursor.execute('ALTER TABLE artists ADD COLUMN location VARCHAR(100)')
        
        if 'is_verified' not in columns:
            cursor.execute('ALTER TABLE artists ADD COLUMN is_verified BOOLEAN DEFAULT FALSE')
        
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE artists ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        
        # Check and add columns to songs table
        cursor.execute("PRAGMA table_info(songs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'like_count' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN like_count INTEGER DEFAULT 0')
        
        if 'duration' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN duration VARCHAR(20)')
        
        if 'genre' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN genre VARCHAR(100)')
        
        if 'is_explicit' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN is_explicit BOOLEAN DEFAULT FALSE')
        
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False

@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    
    # Check and migrate database if needed
    if not check_database_schema():
        migrate_database()
    
    try:
        # Get basic stats with safe defaults
        total_songs = Song.query.count() or 0
        total_artists = Artist.query.count() or 0
        
        # Songs from the last 7 days
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_this_week = Song.query.filter(Song.release_date >= week_ago).count() or 0
        
        # Latest songs for display (limited to 8 for homepage)
        latest_songs = Song.query.order_by(Song.release_date.desc()).limit(8).all() or []
        
        # Featured artists (artists with most songs) - FIXED QUERY
        featured_artists = db.session.query(Artist).outerjoin(Song).group_by(Artist.id).order_by(
            db.func.count(Song.id).desc()
        ).limit(12).all() or []
        
        # Get paginated songs for the main grid
        songs_paginated = Song.query.order_by(Song.release_date.desc()).paginate(
            page=page, per_page=12, error_out=False
        )
        
        return render_template('index.html', 
                             songs=songs_paginated,
                             latest_songs=latest_songs,
                             featured_artists=featured_artists,
                             total_songs=total_songs,
                             total_artists=total_artists,
                             new_this_week=new_this_week)
                             
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', 
                             songs=[],
                             latest_songs=[],
                             featured_artists=[],
                             total_songs=0,
                             total_artists=0,
                             new_this_week=0)

@main_bp.route('/artist/<name>')
def artist_songs(name):
    """Show songs by specific artist"""
    if not name or name.strip() == "":
        flash('Artist name is required', 'error')
        return redirect(url_for('main.artists_list'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    try:
        artist = Artist.query.filter_by(name=name).first()
        if not artist:
            flash(f'Artist "{name}" not found', 'warning')
            return redirect(url_for('main.artists_list'))
            
        songs = Song.query.filter_by(artist_id=artist.id).order_by(
            Song.release_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Calculate thirty days ago for the template - ensure timezone awareness
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        return render_template('artist.html', 
                             artist=artist, 
                             songs=songs,
                             thirty_days_ago=thirty_days_ago)
        
    except Exception as e:
        print(f"Error loading artist {name}: {e}")
        flash('Error loading artist page', 'error')
        return redirect(url_for('main.artists_list'))
@main_bp.route('/artist/<name>/generate-description', methods=['POST'])
def generate_artist_description(name):
    """Generate AI description for artist"""
    try:
        artist = Artist.query.filter_by(name=name).first()
        if not artist:
            return jsonify({
                'success': False,
                'message': 'Artist not found'
            }), 404
        
        description = artist.generate_ai_description()
        if description:
            return jsonify({
                'success': True,
                'description': description,
                'message': 'Artist description generated successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not generate description. Please check your Gemini API key.'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@main_bp.route('/latest')
def latest_songs():
    """Show latest songs (last 30 days)"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    songs = Song.query.filter(
        Song.release_date >= thirty_days_ago
    ).order_by(Song.release_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('latest.html', songs=songs)

@main_bp.route('/trending')
def trending_songs():
    """Show trending songs by view count"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    songs = Song.query.order_by(Song.view_count.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('trending.html', songs=songs)

@main_bp.route('/update', methods=['POST'])
def update_songs():
    """Manual trigger to update songs"""
    try:
        youtube_service = YouTubeService()
        
        # Fetch new videos
        videos = youtube_service.search_kenyan_music()
        saved_count = youtube_service.save_videos_to_db(videos)
        
        # Try to generate images if Gemini service is available
        images_generated = 0
        try:
            gemini_service = GeminiService()
            new_songs = Song.query.order_by(Song.created_at.desc()).limit(saved_count).all()
            
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
        except Exception as gemini_error:
            print(f"Gemini image generation failed: {gemini_error}")
            # Continue even if image generation fails
        
        return jsonify({
            'success': True,
            'message': f'Updated {saved_count} new songs and generated {images_generated} images',
            'saved_count': saved_count,
            'images_generated': images_generated
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating songs: {str(e)}'
        }), 500

@main_bp.route('/search')
def search_songs():
    """Search songs by title or artist"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if not query:
        flash('Please enter a search term', 'warning')
        return redirect(url_for('main.index'))
    
    songs = Song.query.join(Artist).filter(
        db.or_(
            Song.title.ilike(f'%{query}%'),
            Artist.name.ilike(f'%{query}%')
        )
    ).order_by(Song.release_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('search.html', songs=songs, query=query)

@main_bp.route('/artists')
def artists_list():
    """List all artists with song counts - SIMPLE VERSION"""
    try:
        # Get all artists with song counts in one query (no pagination)
        artists_with_counts = db.session.query(
            Artist, 
            db.func.count(Song.id).label('song_count')
        ).outerjoin(Song).group_by(Artist.id).order_by(
            Artist.name
        ).all()
        
        return render_template('artists.html', artists=artists_with_counts)
        
    except Exception as e:
        print(f"Error in artists_list: {e}")
        # Ultimate fallback - simple list
        artists = Artist.query.order_by(Artist.name).all()
        return render_template('artists.html', artists=artists)

@main_bp.route('/api/songs')
def api_songs():
    """JSON API endpoint for songs"""
    try:
        songs = Song.query.order_by(Song.release_date.desc()).limit(50).all()
        return jsonify([song.to_dict() for song in songs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/artists')
def api_artists():
    """JSON API endpoint for artists"""
    try:
        artists = Artist.query.order_by(Artist.name).all()
        return jsonify([artist.to_dict() for artist in artists])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/cleanup-old', methods=['POST'])
def cleanup_old_songs():
    """Remove songs older than 1 month"""
    try:
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Find old songs
        old_songs = Song.query.filter(Song.release_date < one_month_ago).all()
        deleted_count = len(old_songs)
        
        # Delete old songs
        for song in old_songs:
            db.session.delete(song)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Removed {deleted_count} songs older than 1 month',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error cleaning up old songs: {str(e)}'
        }), 500

@main_bp.route('/search-manual', methods=['POST'])
def search_manual():
    """Manual search with specific artists to avoid quota limits"""
    try:
        youtube_service = YouTubeService()
        
        # Only search for top artists to avoid quota limits
        limited_artists = ["Sauti Sol", "Nyashinski", "Khaligraph Jones", "Otile Brown", "Bien"]
        
        # Modify the search queries temporarily
        original_queries = youtube_service.search_queries.copy()
        youtube_service.search_queries = [f"{artist} new song 2025" for artist in limited_artists]
        
        videos = youtube_service.search_kenyan_music()
        saved_count = youtube_service.save_videos_to_db(videos)
        
        # Restore original queries
        youtube_service.search_queries = original_queries
        
        return jsonify({
            'success': True,
            'message': f'Manual search completed. Saved {saved_count} new songs from top artists.',
            'saved_count': saved_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error in manual search: {str(e)}'
        }), 500

@main_bp.route('/add-song', methods=['GET', 'POST'])
def add_song():
    """Manual song addition form"""
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            artist_name = request.form.get('artist')
            youtube_url = request.form.get('youtube_url')
            release_date = request.form.get('release_date')
            
            if not all([title, artist_name, youtube_url, release_date]):
                return jsonify({
                    'success': False, 
                    'message': 'All fields are required'
                })
            
            # Extract YouTube ID from URL
            youtube_id = extract_youtube_id(youtube_url)
            if not youtube_id:
                return jsonify({
                    'success': False, 
                    'message': 'Invalid YouTube URL'
                })
            
            # Check if song already exists
            existing_song = Song.query.filter_by(youtube_id=youtube_id).first()
            if existing_song:
                return jsonify({
                    'success': False, 
                    'message': 'Song already exists in database'
                })
            
            # Find or create artist
            artist = Artist.query.filter_by(name=artist_name).first()
            if not artist:
                artist = Artist(name=artist_name)
                db.session.add(artist)
                db.session.flush()
            
            # Create song
            song = Song(
                title=title,
                artist_id=artist.id,
                release_date=datetime.strptime(release_date, '%Y-%m-%d').replace(tzinfo=timezone.utc),
                youtube_url=youtube_url,
                youtube_id=youtube_id,
                thumbnail_url=f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
            )
            
            db.session.add(song)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Song "{title}" added successfully!'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False, 
                'message': f'Error adding song: {str(e)}'
            })
    
    return render_template('add_song.html')

@main_bp.route('/bulk-add-songs', methods=['POST'])
def bulk_add_songs():
    """Add multiple songs at once"""
    try:
        songs_data = request.json.get('songs', [])
        added_count = 0
        errors = []
        
        for i, song_data in enumerate(songs_data):
            try:
                title = song_data.get('title')
                artist_name = song_data.get('artist')
                youtube_url = song_data.get('youtube_url')
                release_date = song_data.get('release_date')
                
                if not all([title, artist_name, youtube_url, release_date]):
                    errors.append(f"Song {i+1}: Missing required fields")
                    continue
                
                # Extract YouTube ID
                youtube_id = extract_youtube_id(youtube_url)
                if not youtube_id:
                    errors.append(f"Song {i+1}: Invalid YouTube URL")
                    continue
                
                # Check if song exists
                existing_song = Song.query.filter_by(youtube_id=youtube_id).first()
                if existing_song:
                    errors.append(f"Song {i+1}: Already exists in database")
                    continue
                
                # Find or create artist
                artist = Artist.query.filter_by(name=artist_name).first()
                if not artist:
                    artist = Artist(name=artist_name)
                    db.session.add(artist)
                    db.session.flush()
                
                # Create song
                song = Song(
                    title=title,
                    artist_id=artist.id,
                    release_date=datetime.strptime(release_date, '%Y-%m-%d').replace(tzinfo=timezone.utc),
                    youtube_url=youtube_url,
                    youtube_id=youtube_id,
                    thumbnail_url=f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
                )
                
                db.session.add(song)
                added_count += 1
                
            except Exception as e:
                errors.append(f"Song {i+1}: {str(e)}")
                continue
        
        db.session.commit()
        
        response = {
            'success': True,
            'message': f'Added {added_count} new songs successfully!',
            'added_count': added_count
        }
        
        if errors:
            response['errors'] = errors
            response['message'] = f'Added {added_count} songs with {len(errors)} errors'
        
        return jsonify(response)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error in bulk add: {str(e)}'
        }), 500

def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    import re
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)',
        r'youtube\.com\/embed\/([^?]+)',
        r'youtube\.com\/v\/([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@main_bp.route('/stats')
def stats():
    """Show platform statistics"""
    try:
        total_songs = Song.query.count() or 0
        total_artists = Artist.query.count() or 0
        total_views = db.session.query(db.func.sum(Song.view_count)).scalar() or 0
        
        # Recent activity
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_this_week = Song.query.filter(Song.release_date >= week_ago).count() or 0
        
        # Top artists by song count
        top_artists = db.session.query(
            Artist, 
            db.func.count(Song.id).label('song_count')
        ).join(Song).group_by(Artist.id).order_by(
            db.func.count(Song.id).desc()
        ).limit(10).all()
        
        # Most viewed songs
        most_viewed = Song.query.order_by(Song.view_count.desc()).limit(10).all()
        
        return render_template('stats.html',
                            total_songs=total_songs,
                            total_artists=total_artists,
                            total_views=total_views,
                            new_this_week=new_this_week,
                            top_artists=top_artists,
                            most_viewed=most_viewed)
                            
    except Exception as e:
        print(f"Error in stats route: {e}")
        return render_template('stats.html',
                            total_songs=0,
                            total_artists=0,
                            total_views=0,
                            new_this_week=0,
                            top_artists=[],
                            most_viewed=[])
    
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
@main_bp.route('/artist/<name>/share-data')
def artist_share_data(name):
    """Get artist data for social media sharing"""
    artist = Artist.query.filter_by(name=name).first_or_404()
    
    share_data = {
        'title': f"{artist.name} - Kenyan Artist",
        'description': artist.description or f"Discover {artist.name}, a talented Kenyan artist",
        'url': url_for('main.artist_songs', name=artist.name, _external=True),
        'image': url_for('static', filename='images/logo.png', _external=True),
        'song_count': len(artist.songs),
        'has_description': bool(artist.description)
    }
    
    return jsonify(share_data)
import random
@main_bp.route('/artist/<name>/generate-card')
def generate_artist_card(name):
    """Generate a shareable artist card image"""
    from flask import send_file
    import io
    from PIL import Image, ImageDraw, ImageFont
    
    artist = Artist.query.filter_by(name=name).first_or_404()
    
    try:
        # Create a simple card image
        width, height = 800, 400
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Add background pattern
        for i in range(50):
            x, y = random.randint(0, width), random.randint(0, height)
            size = random.randint(5, 20)
            color = random.choice([(220, 20, 60), (46, 139, 87), (70, 130, 180)])
            draw.ellipse([x, y, x + size, y + size], fill=color)
        
        # Add text
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Artist name
        draw.text((50, 50), artist.name, fill=(0, 0, 0), font=font_large)
        
        # Song count
        draw.text((50, 120), f"{len(artist.songs)} songs", fill=(100, 100, 100), font=font_small)
        
        # Website
        draw.text((50, 150), "Good Music KE", fill=(70, 130, 180), font=font_small)
        
        # Save to bytes
        img_io = io.BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png', 
                        as_attachment=True, 
                        download_name=f"{artist.name}_artist_card.png")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# In your routes.py or views.py
from flask import current_app, render_template, request, flash, redirect, url_for, jsonify
@main_bp.route('/artist/<name>')
def artist_detail(name):
    try:
        artist = Artist.query.filter_by(name=name).first_or_404()
        
        # Ensure songs is never None - initialize as empty list if None
        if artist.songs is None:
            artist.songs = []
            
        # Paginate songs if there are any
        page = request.args.get('page', 1, type=int)
        if artist.songs:
            songs = Song.query.filter_by(artist_id=artist.id).order_by(
                Song.release_date.desc()
            ).paginate(page=page, per_page=12, error_out=False)
        else:
            songs = None
            
        return render_template('artist.html', artist=artist, songs=songs)
        
    except Exception as e:
        current_app.logger.error(f"Error loading artist {name}: {str(e)}")
        flash('Error loading artist profile', 'error')
        return redirect(url_for('main.artists_list'))