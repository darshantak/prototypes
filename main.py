import os
import numpy as np
import librosa
import moviepy.editor as mp
from moviepy.video.fx import all as vfx
from moviepy.editor import VideoFileClip, AudioFileClip, afx

def trim_video(video_path, duration=4):
    """Load video, correct rotation, and trim it to `duration` seconds from the start."""
    try:
        clip = VideoFileClip(video_path)
    except Exception as e:
        print(f"Error loading video {video_path}: {e}")
        return None

    # Auto-correct orientation if necessary
    if hasattr(clip, 'rotation'):
        if clip.rotation == 90:
            clip = clip.rotate(-90)
        elif clip.rotation == 270:
            clip = clip.rotate(90)

    return clip.subclip(0, min(duration, clip.duration))  # Trim safely

def detect_best_music_end(audio_path, target_time):
    """Find the closest beat to the target time to trim the music naturally."""
    try:
        y, sr = librosa.load(audio_path)
    except Exception as e:
        print(f"Error loading audio {audio_path}: {e}")
        return target_time
    
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)

    if len(beat_times) == 0:
        print("No beats detected! Falling back to manual trimming.")
        return target_time  # Fallback to original duration

    best_end = min(beat_times, key=lambda x: abs(x - target_time))
    print(f"Original target time: {target_time:.2f}s, Adjusted music end time: {best_end:.2f}s")
    return best_end

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

def resize_clip(clip, target_width=720, target_height=1280):
    """Resize the video while maintaining aspect ratio based on height."""
    return clip.resize((target_width, target_height))

def create_reel(video_paths, audio_path, output_path, filter_type="normal", target_duration=15):
    """Create a reel from the given videos and sync it with detected beats."""

    # Trim videos to **first 3 seconds** and filter out invalid ones
    clips = [trim_video(vp, duration=3) for vp in video_paths if os.path.exists(vp)]
    clips = [clip for clip in clips if clip and clip.duration > 0]  # Remove invalid clips

    if not clips:
        print("No valid video clips found.")
        return

    # Get the **total video duration** (sum of all clips)
    total_video_duration = sum(clip.duration for clip in clips)

    # Detect best music end time **based on available video duration**
    best_end_time = detect_best_music_end(audio_path, min(target_duration, total_video_duration))

    # Ensure best_end_time leaves space for fade-out
    fade_duration = min(2, best_end_time / 3)  # Prevent too long fade-out
    best_end_time = max(0, best_end_time - fade_duration)

    # Resize clips while maintaining aspect ratio
    target_width, target_height = 720, 1280  # Force resolution
    filtered_clips = [apply_filter(resize_clip(clip, target_width, target_height), filter_type) for clip in clips]

    # Merge the clips sequentially
    final_video = mp.concatenate_videoclips(filtered_clips, method="compose")

    # Trim **final video** to match music length to avoid black screen
    final_video = final_video.subclip(0, min(final_video.duration, best_end_time + fade_duration))

    try:
        audio = AudioFileClip(audio_path).subclip(0, final_video.duration)
    except Exception as e:
        print(f"Error processing audio: {e}")
        return

    # Apply proper fade-in & fade-out
    fade_in_duration = min(1.5, final_video.duration / 4)  # Adjust based on total length
    audio = audio.fx(afx.audio_fadein, fade_in_duration).fx(afx.audio_fadeout, fade_duration)

    print(f"Final trimmed music duration: {final_video.duration:.2f}s (Includes Fade-In & Fade-Out)")
    
    final_video = final_video.set_audio(audio)

    # Save output video
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=30, bitrate="5000k", preset="slow")

    # Close all clips to free memory
    for clip in clips + filtered_clips + [final_video]:
        clip.close()

def main():
    video_folder = "clips/"
    video_paths = [os.path.join(video_folder, f) for f in os.listdir(video_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
    audio_path = "tokoyo.mp3"
    output_path = "output_reel.mp4"
    create_reel(video_paths, audio_path, output_path, filter_type="normal", target_duration=20)

if __name__ == "__main__":
    main()
