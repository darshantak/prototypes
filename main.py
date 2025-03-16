import os
import numpy as np
import librosa
import moviepy.editor as mp
from moviepy.video.fx import all as vfx
from moviepy.editor import VideoFileClip, AudioFileClip

def trim_video(video_path, max_duration=5):
    """Load video and trim it to `max_duration` seconds."""
    clip = VideoFileClip(video_path)
    return clip.subclip(0, min(max_duration, clip.duration))  # Trim safely

def detect_beats(audio_path, hop_length=512):
    """Detect beats in the audio file."""
    y, sr = librosa.load(audio_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
    
    print(f"Detected tempo: {tempo.item():.2f} BPM")  # Ensure tempo is a scalar
    print(f"Found {len(beat_times)} beats")
    
    return beat_times

def apply_filter(clip, filter_type="normal"):
    """Apply a visual filter to the clip."""
    filters = {
        "normal": lambda c: c,
        "grayscale": lambda c: c.fx(vfx.blackwhite),
        "noir": lambda c: c.fx(vfx.blackwhite).fx(vfx.colorx, 1.5),
        "warm": lambda c: c.fx(vfx.colorx, 1.2).fx(vfx.gamma_corr, 0.8),
        "cool": lambda c: c.fx(vfx.colorx, 0.8).fx(vfx.gamma_corr, 1.2),
    }
    return filters.get(filter_type, lambda c: c)(clip)

def create_reel(video_paths, audio_path, output_path, filter_type="normal", total_duration=15):
    """Create a reel from the given videos and audio."""

    # Trim videos and filter out invalid ones
    clips = [trim_video(vp, max_duration=5) for vp in video_paths if os.path.exists(vp)]
    clips = [clip for clip in clips if clip.duration > 0]  # Remove invalid clips

    if not clips:
        print("No valid video clips found.")
        return

    # Determine how long each clip should be
    num_clips = len(clips)
    segment_duration = min(total_duration / num_clips, 5)  # Each clip gets equal time, max 5s

    print(f"Total clips: {num_clips}, Each clip duration: {segment_duration:.2f}s")

    # Apply filters and trim each clip to its allocated segment
    filtered_clips = [apply_filter(clip.subclip(0, segment_duration), filter_type) for clip in clips]

    # Merge the clips sequentially
    final_video = mp.concatenate_videoclips(filtered_clips, method="compose")
    
    # Sync with music
    audio = AudioFileClip(audio_path).subclip(0, min(total_duration, final_video.duration))
    final_video = final_video.set_audio(audio)

    # Ensure the final video doesn't exceed total duration
    final_video = final_video.subclip(0, min(total_duration, final_video.duration))
    
    # Save output video
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

    # Close all clips to free memory
    for clip in clips + filtered_clips + [final_video]:
        clip.close()

def main():
    video_folder = "clips/"
    video_paths = [os.path.join(video_folder, f) for f in os.listdir(video_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
    audio_path = "music.mp3"
    output_path = "output_reel.mp4"
    create_reel(video_paths, audio_path, output_path, filter_type="normal", total_duration=15)

if __name__ == "__main__":
    main()
