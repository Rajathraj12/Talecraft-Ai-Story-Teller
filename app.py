from flask import Flask, render_template, request
import json
import google.generativeai as genai
import azure.cognitiveservices.speech as speechsdk
import os
from translate import Translator
import time
from dotenv import load_dotenv
import requests
import urllib3
import ssl

# Load environment variables from .env file
load_dotenv()

# Configure for SSL certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Flask app
app = Flask(__name__)

# Configure server to handle larger request lines
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for request content

STORIES_FILE = "data/stories.json"
def load_stories():
    try:
        with open(STORIES_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_story(story_id, story_data):
    stories = load_stories()
    stories[story_id] = story_data
    with open(STORIES_FILE, "w") as file:
        json.dump(stories, file, indent=4)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_story():
    child_name = request.form.get("child_name")
    theme = request.form.get("theme")
    story_format = request.form.get("story_format")
    language_code = request.form.get("language_code", "en-US")
    voice_style = request.form.get("voice_style", "cheerful")

    story = call_gemini_api(child_name, theme, story_format)

    if language_code == "hi-IN" and len(story) > 1000:
        story = story[:1000]

    if language_code == "hi-IN":
        story = translate_text(story, target_language="hi")

    if story_format.lower() == "moral-based":
        moral = generate_moral(theme)
        if language_code == "hi-IN":
            moral = translate_text(moral, target_language="hi")
        story += f"\n\n<b>Moral of the Story:</b> {moral}"

    story_id = f"{child_name}_{theme}"
    audio_filename = f"{story_id}_{language_code}.mp3"
    audio_path = f"static/audio/{audio_filename}"
    audio_result = text_to_speech(story, audio_path, language_code, voice_style)

    if not audio_result:
        print("Audio generation failed. Proceeding without audio.")
        audio_path = None

    if audio_path:
        print(f"AUDIO PATH: {audio_path} - Exists: {os.path.exists(audio_path)}")
    else:
        print("AUDIO PATH: None (Audio generation failed)")

    return render_template(
        "story.html",
        story=story,
        child_name=child_name,
        audio_file=audio_path
    )

@app.route("/translate_story", methods=["POST"])
def translate_story():
    language = request.form.get("language", "en")
    story = request.form.get("story", "")

    if language == "hi":
        translated_story = translate_text(story, target_language="hi")
    else:
        translated_story = story
    
    return {"story": translated_story}

def call_gemini_api(child_name, theme, story_format):
    try:
        # Create model instance - moved from global scope to function
        model = genai.GenerativeModel("models/gemini-2.0-flash")
        
        prompt = (
            f"Write a {story_format.lower()} story for a child named {child_name} "
            f"based on the theme '{theme}'. Make it engaging, age-appropriate, and imaginative."
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return f"Error generating story: {str(e)}"

def text_to_speech(text, filename, language_code="en-US", style="cheerful"):
    service_region = os.getenv("AZURE_SPEECH_REGION", "centralindia")
    speech_key = os.getenv("AZURE_SPEECH_KEY")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=filename)

    voice_map = {
        "en-US": "en-IN-NeerjaNeural",
        "hi-IN": "hi-IN-SwaraNeural",
        "fr-FR": "fr-FR-DeniseNeural"
    }
    voice_name = voice_map.get(language_code, "en-US-JennyNeural")
    speech_config.speech_synthesis_voice_name = voice_name

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    max_chunk_size = 5000
    chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

    for chunk in chunks:
        ssml = f"""
        <speak version='1.0' xml:lang='{language_code}'>
            <voice name='{voice_name}'>
                <express-as style='{style}'>
                    {chunk}
                </express-as>
            </voice>
        </speak>
        """

        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Speech synthesis failed: {result.reason}")
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"Cancellation reason: {cancellation_details.reason}")
                if cancellation_details.error_details:
                    print(f"Error details: {cancellation_details.error_details}")
            return None

    print(f"Audio saved: {filename}")
    return filename

def generate_moral(theme):
    morals = {
        "kindness": "Always be kind to others, as kindness makes the world a better place.",
        "honesty": "Honesty is the best policy, and it builds trust and respect.",
        "courage": "Face your fears with courage, and you will grow stronger."
    }
    return morals.get(theme.lower(), "Always strive to do your best and learn from every experience.")

def translate_text(text, target_language="hi"):
    # For very short text, use a simple dictionary to avoid API calls
    common_translations = {
        "hi": {
            "once upon a time": "एक समय की बात है",
            "the end": "अंत",
            "moral of the story": "कहानी की शिक्षा",
        }
    }
    
    # Simple cache to avoid translating the same text multiple times
    # This helps during development and when users translate the same stories
    cache_file = "data/translation_cache.json"
    translation_cache = {}
    
    # Load cache if it exists
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                translation_cache = json.load(f)
    except Exception as e:
        print(f"Error loading translation cache: {e}")
    
    # Create a cache key
    cache_key = f"{text[:50]}_{target_language}"
    
    # Check if translation is in cache
    if cache_key in translation_cache:
        print(f"Using cached translation for {cache_key[:20]}...")
        return translation_cache[cache_key]
    
    # Use Gemini API for translations instead of external services
    # This is more reliable and controlled within our rate limits
    try:
        # Only create the model when needed (not on import)
        model = genai.GenerativeModel("models/gemini-2.0-flash")
        
        # For longer texts, split into reasonable chunks
        # Gemini handles context better than the external translation APIs
        max_length = 750  # Increased from 500
        
        if len(text) <= max_length:
            # Translate short text directly
            prompt = f"Translate the following English text to Hindi. Only respond with the translation, nothing else:\n\n{text}"
            response = model.generate_content(prompt)
            translated_text = response.text
        else:
            # Split longer text into paragraphs instead of arbitrary chunks
            paragraphs = text.split('\n\n')
            translated_paragraphs = []
            
            # Translate each paragraph
            for i, para in enumerate(paragraphs):
                if para.strip():  # Skip empty paragraphs
                    prompt = f"Translate the following English text to Hindi. Only respond with the translation, nothing else:\n\n{para}"
                    try:
                        response = model.generate_content(prompt)
                        translated_para = response.text
                        translated_paragraphs.append(translated_para)
                        print(f"Paragraph {i+1}/{len(paragraphs)} translated")
                    except Exception as para_error:
                        print(f"Error translating paragraph {i+1}: {para_error}")
                        # On error, keep the original paragraph
                        translated_paragraphs.append(para)
            
            # Join the translated paragraphs back with the same structure
            translated_text = '\n\n'.join(translated_paragraphs)
        
        # Save to cache
        translation_cache[cache_key] = translated_text
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(translation_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving translation cache: {e}")
        
        return translated_text
        
    except Exception as e:
        print(f"Translation error with Gemini API: {e}")
        
        # Fallback to simplified translation using the Translator library
        # This is less likely to timeout but may be less accurate
        try:
            translator = Translator(to_lang=target_language)
            
            # For very short texts
            if len(text) < 100:
                return translator.translate(text)
                
            # Split into smaller chunks for the translator
            chunks = [text[i:i + 200] for i in range(0, len(text), 200)]
            translated_chunks = []
            
            for chunk in chunks:
                try:
                    # Set a short timeout for each chunk
                    translated_chunk = translator.translate(chunk)
                    translated_chunks.append(translated_chunk)
                except:
                    # If a chunk fails, keep it untranslated
                    translated_chunks.append(chunk)
            
            return " ".join(translated_chunks)
            
        except Exception as fallback_error:
            print(f"Fallback translation failed: {fallback_error}")
            # If all else fails, return original text
            return text

# if __name__ == "__main__":
#     if not os.path.exists("static/audio"):
#         os.makedirs("static/audio")
#     # Add a print statement for debugging
#     print("Starting TaleCraft AI Story Teller application...")
#     app.run(debug=True, threaded=True, use_reloader=True, 
#             host='0.0.0.0', 
#             port=5000)
