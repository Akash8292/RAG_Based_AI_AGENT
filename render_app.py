"""
Lightweight version for Render - RAG System Only
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from gtts import gTTS
import speech_recognition as sr
import os
import json
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    BASE_DIR = os.getcwd()
    KB_PATH = os.path.join(BASE_DIR, "kfc_knowledge.json")
    TEMP_DIR = os.path.join(BASE_DIR, "temp_audio")

os.makedirs(Config.TEMP_DIR, exist_ok=True)

# Knowledge Base
class KnowledgeBase:
    def __init__(self, kb_path):
        with open(kb_path, 'r') as f:
            self.kb = json.load(f)
        print(f"✓ Loaded {len(self.kb)} knowledge entries")
    
    def search(self, query):
        query_lower = query.lower()
        scores = {}
        
        for key, entry in self.kb.items():
            keywords = entry['question'].lower().split(', ')
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[key] = score
        
        if not scores:
            return "I'm a KFC assistant. Ask me about menu, prices, or deals!"
        
        best_key = max(scores, key=scores.get)
        return self.kb[best_key]['answer']

# Speech Processor
class SpeechProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def convert_to_wav(self, input_file, output_file):
        try:
            audio = AudioSegment.from_file(input_file)
            audio.export(output_file, format="wav")
            return True
        except Exception as e:
            print(f"Audio conversion error: {e}")
            return False
    
    def speech_to_text(self, audio_file_path):
        try:
            wav_path = audio_file_path.replace(
                os.path.splitext(audio_file_path)[1], 
                "_converted.wav"
            )
            
            if not self.convert_to_wav(audio_file_path, wav_path):
                return None
            
            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            print(f"STT Error: {e}")
            return None
    
    def text_to_speech(self, text, output_path):
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            return True
        except Exception as e:
            print(f"TTS Error: {e}")
            return False

# Initialize
kb = KnowledgeBase(Config.KB_PATH)
speech = SpeechProcessor()

# Routes
@app.route('/')
def index():
    return render_template('index_simple.html')

@app.route('/api/status')
def status():
    return jsonify({
        "mode": "rag",
        "active": True,
        "system": "RAG Knowledge Base"
    })

@app.route('/api/process', methods=['POST'])
def process():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        input_path = os.path.join(Config.TEMP_DIR, "input.webm")
        output_path = os.path.join(Config.TEMP_DIR, "output.mp3")
        
        audio_file.save(input_path)
        
        # Speech to text
        user_text = speech.speech_to_text(input_path)
        
        if not user_text:
            return jsonify({"error": "Could not understand audio"}), 400
        
        print(f"User: {user_text}")
        
        # Get response from knowledge base
        response_text = kb.search(user_text)
        print(f"Bot: {response_text}")
        
        # Text to speech
        speech.text_to_speech(response_text, output_path)
        
        return jsonify({
            "user_text": user_text,
            "response_text": response_text,
            "audio_url": "/audio/output.mp3"
        })
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_file(os.path.join(Config.TEMP_DIR, filename))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)