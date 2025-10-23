from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting Kenyan Music Discovery App...")
    print("This app will only fetch music from established Kenyan artists")
    print("Visit: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")