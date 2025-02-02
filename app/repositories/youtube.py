import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import google.generativeai as genai
import yt_dlp
import whisper
import tempfile
import os
import shutil

# 🔑 Configure Gemini API Key
GEMINI_API_KEY = "AIzaSyBf6XLpCYFTdVG5p7YiouYxEpkGAKYqmJQ"  # Replace with your API key
genai.configure(api_key=GEMINI_API_KEY)

def summarizeyt_with_gemini(text, target_language):
    """Summarize text using Google Gemini API in the user-selected language."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Summarize this text so the user can understand the content of the video. Note down the important details. Be as natural as possible. The summary should be in {target_language}:\n\n{text}"
    response = model.generate_content(prompt)
    return response.text

def extract_video_id(url):
    """Extracts the YouTube video ID from a given URL."""
    parsed_url = urlparse(url)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        query_params = parse_qs(parsed_url.query)
        return query_params.get("v", [None])[0]
    
    match = re.match(r"(?:https?://)?(?:www\.)?youtu\.be/([^?&]+)", url)
    return match.group(1) if match else None

def fetch_transcript(video_url):
    """Auto-detect and fetch the best available YouTube transcript."""
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, "🚫 Invalid YouTube URL."

    try:
        # List all available transcripts
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        print(f"DEBUG: Available transcripts for {video_id}:")
        for t in transcripts:
            print(f" - {t.language_code} (Generated: {t.is_generated})")

        # Prioritize manually created captions, fallback to auto-generated
        best_transcript = next(
            (t for t in transcripts if not t.is_generated),  # Prefer manual captions
            next((t for t in transcripts if t.is_generated), None)  # Fallback to auto-generated
        )

        if not best_transcript:
            raise TranscriptsDisabled

        # Fetch transcript
        transcript = best_transcript.fetch()
        transcript_text = " ".join([t["text"] for t in transcript])
        return transcript_text, None
    
    except TranscriptsDisabled:
        print("🚨 Captions are disabled. Using Whisper STT.")
        
        # Step 1: Download Audio
        audio_path = download_audio(video_url)

        # Step 2: Transcribe Audio
        transcript_text = transcribe_audio(audio_path)

        return transcript_text, None  # Return the STT-generated transcript

    except Exception as e:
        return None, f"Error: {str(e)}"
    

def download_audio(video_url):
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "youtube_audio.mp3")  # ✅ Ensure correct filename

    print(f"Downloading audio to: {output_path}")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "nopostoverwrites": False,  # ✅ Prevents overwriting of files
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
        except Exception as e:
            print(f"yt-dlp download failed: {e}")
            return None

    if not os.path.exists(output_path):
        print(f"Error: Audio file not found at {output_path}")
        return None

    # ✅ Move the file to a safer location before Whisper uses it
    safe_audio_path = "/app/audio/youtube_audio.mp3"
    os.makedirs(os.path.dirname(safe_audio_path), exist_ok=True)
    shutil.move(output_path, safe_audio_path)

    print(f"Audio moved to: {safe_audio_path}")
    return safe_audio_path  # ✅ Return the safe file path for Whisper



def transcribe_audio(audio_path):
    """
    Converts audio to text using OpenAI Whisper.
    """
    model = whisper.load_model("base")  # You can use "small", "medium", or "large" for better accuracy
    result = model.transcribe(audio_path)
    return result["text"]  # Returns the transcribed text