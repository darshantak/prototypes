import whisper
import openai
import librosa
import numpy as np
from openai import OpenAI

# OpenAI API Key (Set this securely, do not hardcode in production)
OPENAI_API_KEY = ""
client = OpenAI(api_key=OPENAI_API_KEY)


# Function to transcribe audio
def transcribe_audio(audio_path):
    """Transcribes audio using Whisper and returns timestamps with lyrics."""
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    return [(seg["start"], seg["end"], seg["text"]) for seg in result["segments"]]

# Function to analyze beats using Librosa
def analyze_beats(audio_path):
    """Extracts beat timings from the audio file."""
    y, sr = librosa.load(audio_path, sr=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    return [(beat_times[i], beat_times[i+1]) for i in range(len(beat_times)-1)]

# Function to determine lyric mood using GPT-4


def get_lyric_mood(lyrics_text):
    prompt = f"Analyze the mood of this lyric: \"{lyrics_text}\". Respond with a single word like: Noir, Aesthetic, Gloomy, or Neutral."
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10
    )
    
    return response.choices[0].message.content.strip()


# Function to filter lyrics by mood
def filter_lyrics_by_mood(lyrics_with_timestamps, target_mood):
    """Filters lyrics that match the specified mood."""
    return [(start, end, text) for start, end, text in lyrics_with_timestamps if get_lyric_mood(text) == target_mood]

# Function to get the best segment from GPT-4
def get_best_segment(filtered_lyrics):
    """Asks GPT-4 to select the best 2-3 segments from filtered lyrics."""
    if not filtered_lyrics:
        return "No matching segments for the selected mood."
    
    formatted_lyrics = "\n".join([f"[{start:.2f}s - {end:.2f}s]: {text}" for start, end, text in filtered_lyrics])
    prompt = (
        "Given these song segments, pick the most engaging 2-3 for a short video reel."
        " Respond with timestamps only.\n\n" + formatted_lyrics
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    
    return response["choices"][0]["message"]["content"]

# Main function
def process_audio(audio_path, target_mood):
    """Runs transcription, filtering, beat analysis, and selects the best audio segment."""
    print("Transcribing audio...")
    lyrics_with_timestamps = transcribe_audio(audio_path)
    
    print(f"Filtering lyrics for mood: {target_mood}...")
    filtered_lyrics = filter_lyrics_by_mood(lyrics_with_timestamps, target_mood)
    
    print("Analyzing beats...")
    beat_times = analyze_beats(audio_path)
    
    print("Getting best segment from GPT-4...")
    best_segments = get_best_segment(filtered_lyrics)
    
    print("Best segments:", best_segments)
    return best_segments
