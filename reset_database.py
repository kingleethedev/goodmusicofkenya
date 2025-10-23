# reset_database.py
from app import db, create_app
from app.models import Artist, Song

def reset_database():
    app = create_app()
    
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables with new schema
        db.create_all()
        
        print("✅ Database reset and created with new schema!")

if __name__ == '__main__':
    reset_database()