from flask import Flask, render_template, request
import json
import google.generativeai as genai
import azure.cognitiveservices.speech as speechsdk
import os
from translate import Translator
import time
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Create model instance
model = genai.GenerativeModel("models/gemini-2.0-flash")

# Test the model
response = model.generate_content("Write a short story about friendship")
print(response.text)

app = Flask(__name__)

# Configure server to handle larger request lines
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for request content

=======
app = Flask(__name__)

>>>>>>> origin/main
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

<<<<<<< HEAD
@app.route("/translate_story", methods=["POST"])
def translate_story():
    language = request.form.get("language", "en")
    story = request.form.get("story", "")
=======
@app.route("/translate_story")
def translate_story():
    language = request.args.get("language", "en")
    story = request.args.get("story", "")
>>>>>>> origin/main

    estimated_time = (len(story) // 100) + 2
    time.sleep(estimated_time)

    if language == "hi":
        translated_story = translate_text(story, target_language="hi")
    else:
        translated_story = story
    
    return {"story": translated_story}

def call_gemini_api(child_name, theme, story_format):
<<<<<<< HEAD
=======
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
>>>>>>> origin/main
    prompt = (
        f"Write a {story_format.lower()} story for a child named {child_name} "
        f"based on the theme '{theme}'. Make it engaging, age-appropriate, and imaginative."
    )
    try:
<<<<<<< HEAD
=======
        model = genai.GenerativeModel("models/gemini-2.0-flash")
>>>>>>> origin/main
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
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
    max_length = 500
    chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
<<<<<<< HEAD
    
    # Generate a unique ID for this translation
    translation_id = f"trans_{int(time.time())}"
    print(f"Translation ID: {translation_id}")
    
    # Step 1: Store original English text with ID
    translation_record = {
        "id": translation_id,
        "original_text": text,
        "english_chunks": chunks,
        "timestamp": time.time()
    }
    
    # Step 2: Perform the actual translation
    translator = Translator(to_lang=target_language)
    translated_chunks = []
    
    print(f"Processing translation {translation_id} from English to {target_language}...")
    for i, chunk in enumerate(chunks):
        translated_chunk = translator.translate(chunk)
        translated_chunks.append(translated_chunk)
        print(f"Chunk {i+1}/{len(chunks)} translated")
    
    # Step 3: Store the translated chunks
    translation_record["translated_chunks"] = translated_chunks
    translation_record["final_translation"] = " ".join(translated_chunks)
    
    # For debugging/tracking purposes
    print(f"Translation {translation_id} complete")
    
    return translation_record["final_translation"]
=======
    translator = Translator(to_lang=target_language)
    translated_chunks = [translator.translate(chunk) for chunk in chunks]
    return " ".join(translated_chunks)
>>>>>>> origin/main

# if __name__ == "__main__":
#     if not os.path.exists("static/audio"):
#         os.makedirs("static/audio")
<<<<<<< HEAD
#     app.run(debug=True, threaded=True, use_reloader=True, 
#             host='0.0.0.0', 
#             port=5000,
#             request_handler=lambda wsgi_app: app.wsgi_app)
=======
#     app.run(debug=True)
>>>>>>> origin/main
