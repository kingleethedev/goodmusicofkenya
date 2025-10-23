import google.generativeai as genai
import os
from flask import current_app
from PIL import Image, ImageDraw, ImageFont
import random
import re
import time

class GeminiService:
    def __init__(self):
        self.api_key = current_app.config.get('GEMINI_API_KEY')
        self.model = None
        self.model_name = None
        
        try:
            if self.api_key and self.api_key not in ['your-gemini-api-key-here', 'your_gemini_api_key_here']:
                genai.configure(api_key=self.api_key)
                self._initialize_model()
                print("✅ Gemini API configured successfully")
            else:
                print("⚠️ No valid Gemini API key provided")
                
        except Exception as e:
            print(f"❌ Gemini configuration failed: {str(e)}")
            self.model = None

    def _initialize_model(self):
        """Initialize the best available Gemini model for text generation"""
        try:
            # Convert generator to list
            available_models = list(genai.list_models())
            model_names = [model.name for model in available_models]
            print(f"📋 Available Gemini models: {model_names}")
            
            # Debug: Print each model's capabilities
            print("🔍 Model capabilities:")
            text_generation_models = []
            
            for model in available_models:
                methods = []
                try:
                    # Try to get supported generation methods
                    if hasattr(model, 'supported_generation_methods'):
                        methods = list(model.supported_generation_methods) if model.supported_generation_methods else []
                    print(f"   {model.name}: {methods}")
                    
                    # Check if it supports generateContent
                    if 'generateContent' in methods:
                        text_generation_models.append(model)
                        print(f"     ✅ Supports generateContent")
                    else:
                        # If no methods listed but it's a Gemini model, try it anyway
                        if ('gemini' in model.name.lower() and 
                            'embedding' not in model.name.lower() and
                            'image' not in model.name.lower() and
                            'audio' not in model.name.lower() and
                            'veo' not in model.name.lower() and
                            'imagen' not in model.name.lower()):
                            text_generation_models.append(model)
                            print(f"     🤔 No methods listed, but trying as Gemini model")
                except Exception as e:
                    print(f"     ❌ Error checking model {model.name}: {e}")
            
            text_model_names = [model.name for model in text_generation_models]
            print(f"🎯 Text generation models to try: {text_model_names}")
            
            if not text_generation_models:
                print("⚠️ No text generation models identified, will try all Gemini models")
                # Fallback: try any model with 'gemini' in the name
                for model in available_models:
                    if 'gemini' in model.name.lower():
                        text_generation_models.append(model)
            
            # Try different model names in order of preference
            model_preferences = [
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro',
                'models/gemini-pro',
                'models/gemini-2.0-flash',
                'models/gemini-2.0-flash-001',
                'models/gemini-2.0-flash-exp',
                'models/gemini-2.5-flash',
                'models/gemini-2.5-flash-preview-09-2025',
                'models/gemini-2.0-pro-exp',
                'models/gemini-2.5-pro',
                'models/gemini-2.5-pro-preview-09-2025',
                'models/gemini-pro-latest',
                'models/gemini-flash-latest',
                'models/gemini-1.0-pro'
            ]
            
            # First try preferred models that exist
            for model_pref in model_preferences:
                for model in text_generation_models:
                    if model.name == model_pref:
                        try:
                            self.model_name = model_pref
                            self.model = genai.GenerativeModel(model_pref)
                            print(f"🎯 Using preferred text generation model: {model_pref}")
                            return
                        except Exception as e:
                            print(f"⚠️ Could not initialize preferred model {model_pref}: {e}")
                            continue
            
            # If no preferred models work, try any available text generation model
            for model in text_generation_models:
                try:
                    self.model_name = model.name
                    self.model = genai.GenerativeModel(model.name)
                    print(f"🎯 Using available text generation model: {model.name}")
                    return
                except Exception as e:
                    print(f"⚠️ Could not initialize model {model.name}: {e}")
                    continue
            
            # Last resort: try any model
            for model in available_models:
                try:
                    self.model_name = model.name
                    self.model = genai.GenerativeModel(model.name)
                    print(f"⚠️ Using fallback model: {model.name}")
                    return
                except Exception as e:
                    print(f"❌ Could not initialize fallback model {model.name}: {e}")
                    continue
            
            print("❌ Could not initialize any model")
            self.model = None
                
        except Exception as e:
            print(f"❌ Error initializing Gemini model: {e}")
            self.model = None

    def is_available(self):
        """Check if Gemini service is available"""
        return self.model is not None

    def generate_artist_description(self, artist_name, song_titles=None):
        """Generate artist description using Gemini AI"""
        if not self.is_available():
            print("⚠️ Gemini service not available")
            return None
            
        try:
            # Prepare context from songs
            songs_context = ""
            if song_titles:
                songs_text = ", ".join(song_titles[:5])
                songs_context = f"Known songs include: {songs_text}."
            else:
                songs_context = "This is an emerging artist with recent releases."
            
            # Generate prompt
            prompt = f"""Write a concise, engaging biography for the Kenyan music artist '{artist_name}'. 
            
            Context: {songs_context}
            
            Requirements:
            - Focus on their musical style, genre, and significance in the Kenyan music scene
            - Keep it under 150 words
            - Use an engaging, informative, and professional tone
            - Mention their potential impact and unique qualities
            - Format as a single flowing paragraph
            - Make it sound authentic and appealing to music fans
            
            Biography:"""
            
            # Add safety settings
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 300,
            }
            
            print(f"🔍 Sending prompt to {self.model_name}...")
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response and response.text:
                description = response.text.strip()
                # Clean up any markdown or special formatting
                description = description.replace('**', '').replace('*', '').replace('#', '')
                description = re.sub(r'\n+', ' ', description)  # Remove extra newlines
                description = re.sub(r'\s+', ' ', description).strip()  # Normalize spaces
                
                print(f"✅ Generated description for {artist_name}")
                return description
            else:
                print(f"❌ No response generated for {artist_name}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating artist description for {artist_name}: {e}")
            return None

    def generate_song_description(self, song_title, artist_name):
        """Generate song description using Gemini AI"""
        if not self.is_available():
            return None
            
        try:
            prompt = f"""Write a brief, engaging description for the Kenyan song '{song_title}' by {artist_name}.
            
            Requirements:
            - Describe the song's musical style, vibe, and energy
            - Mention what makes it unique or noteworthy
            - Keep it under 80 words
            - Use an exciting, engaging tone that makes people want to listen
            - Focus on the listening experience
            
            Description:"""
            
            generation_config = {
                "temperature": 0.8,
                "top_p": 0.9,
                "max_output_tokens": 150,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response and response.text:
                return response.text.strip()
                
        except Exception as e:
            print(f"❌ Error generating song description: {e}")
            return None
        
        return None

    def generate_image(self, song_title, artist_name, release_date=None):
        """Generate custom album art image"""
        try:
            # Use correct static path
            image_dir = os.path.join("app", "static", "images")
            os.makedirs(image_dir, exist_ok=True)

            # Create safe filename
            filename = self._sanitize_filename(f"{song_title}_{artist_name}") + ".jpg"
            filepath = os.path.join(image_dir, filename)

            # If already exists, return its static path
            if os.path.exists(filepath):
                return f"/static/images/{filename}"

            # Create custom image
            image = self._create_custom_album_art(song_title, artist_name, release_date)
            image.save(filepath, "JPEG", quality=85)

            print(f"🖼️ Generated album art: {filename}")
            return f"/static/images/{filename}"

        except Exception as e:
            print(f"❌ Error generating image: {str(e)}")
            return "/static/images/default_album.jpg"

    def _create_custom_album_art(self, song_title, artist_name, release_date):
        """Create a custom album art image with Kenyan theme"""
        width, height = 400, 400

        # Kenyan-inspired color palette
        kenyan_colors = [
            (0, 102, 0),    # Dark Green
            (204, 0, 0),    # Red
            (255, 204, 0),  # Yellow
            (0, 51, 102),   # Dark Blue
            (153, 0, 76),   # Purple
            (255, 102, 0),  # Orange
            (0, 102, 102),  # Teal
            (102, 0, 51),   # Maroon
        ]

        # Base image with gradient or solid color
        bg_color = random.choice(kenyan_colors)
        image = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)

        # Add Kenyan-inspired patterns
        self._add_kenyan_patterns(draw, width, height)
        
        # Add song text
        self._add_song_text(draw, song_title, artist_name, width, height)

        return image

    def _add_kenyan_patterns(self, draw, width, height):
        """Add Kenyan-inspired geometric patterns"""
        # Add some geometric shapes inspired by Kenyan art
        for i in range(15):
            x, y = random.randint(0, width), random.randint(0, height)
            size = random.randint(10, 40)
            
            # Kenyan pattern colors (white, black, red, green)
            pattern_colors = [
                (255, 255, 255, 180),  # White
                (0, 0, 0, 150),        # Black  
                (204, 0, 0, 160),      # Red
                (0, 102, 0, 160),      # Green
            ]
            
            color = random.choice(pattern_colors)
            shape_type = random.choice(["circle", "square", "triangle"])
            
            if shape_type == "circle":
                draw.ellipse([x, y, x + size, y + size], fill=color)
            elif shape_type == "square":
                draw.rectangle([x, y, x + size, y + size], fill=color)
            elif shape_type == "triangle":
                draw.polygon([x, y, x + size, y, x + size//2, y + size], fill=color)

    def _add_song_text(self, draw, song_title, artist_name, width, height):
        """Add song title and artist name to image"""
        try:
            # Try to find available fonts
            font_paths = [
                "arial.ttf",
                "arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]

            font_large = None
            font_small = None
            
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font_large = ImageFont.truetype(path, 24)
                        font_small = ImageFont.truetype(path, 16)
                        break
                    except:
                        continue

            # Fallback to default font
            if font_large is None:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Prepare and split text
            title_lines = self._split_text(song_title, 20)
            artist_text = f"by {artist_name}"[:25]

            # Calculate positions
            total_text_height = len(title_lines) * 30 + 40
            y_start = (height - total_text_height) // 2

            # Draw title lines with shadow effect
            for i, line in enumerate(title_lines):
                bbox = draw.textbbox((0, 0), line, font=font_large)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = y_start + (i * 30)
                
                # Shadow
                draw.text((x + 2, y + 2), line, font=font_large, fill=(0, 0, 0, 180))
                # Main text
                draw.text((x, y), line, font=font_large, fill=(255, 255, 255))

            # Draw artist name
            bbox = draw.textbbox((0, 0), artist_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = y_start + len(title_lines) * 30 + 20
            
            # Shadow
            draw.text((x + 1, y + 1), artist_text, font=font_small, fill=(0, 0, 0, 180))
            # Main text
            draw.text((x, y), artist_text, font=font_small, fill=(255, 255, 255))
            
        except Exception as e:
            print(f"⚠️ Could not add text to image: {str(e)}")

    def _split_text(self, text, max_length):
        """Split text into lines of maximum length"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_length:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines if lines else [text[:max_length]]

    def _sanitize_filename(self, filename):
        """Remove invalid filename characters"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[^\w\s-]', '', filename)
        filename = re.sub(r'[-\s]+', '_', filename)
        return filename[:50].strip('_')

    def test_connection(self):
        """Test if Gemini API is working"""
        if not self.is_available():
            return False, "Gemini service not configured"
            
        try:
            response = self.model.generate_content("Say 'Hello' in a creative way.")
            if response and response.text:
                return True, f"✅ Gemini connected: {response.text[:50]}..."
            else:
                return False, "No response from Gemini"
        except Exception as e:
            return False, f"❌ Gemini test failed: {str(e)}"