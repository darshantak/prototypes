import cv2
import numpy as np
import os
from moviepy.editor import VideoFileClip

# Define filter functions
def apply_cinematic(frame):
    """Adds a cinematic warm tone to the frame."""
    sepia_filter = np.array([[0.393, 0.769, 0.189],
                             [0.349, 0.686, 0.168],
                             [0.272, 0.534, 0.131]])
    return cv2.transform(frame, sepia_filter).clip(0, 255).astype(np.uint8)

def apply_gloomy(frame):
    """Applies a dark and bluish filter for a gloomy effect."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv[..., 2] = hsv[..., 2] * 0.6  # Reduce brightness
    hsv[..., 0] = hsv[..., 0] + 10   # Slightly shift hue
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

def apply_grayscale(frame):
    """Converts the frame to grayscale."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

def apply_brighten(frame):
    """Brightens the frame by increasing contrast and brightness."""
    return cv2.convertScaleAbs(frame, alpha=1.2, beta=30)

def apply_darken(frame):
    """Darkens the frame by reducing brightness."""
    return cv2.convertScaleAbs(frame, alpha=0.8, beta=-30)

# Function to apply filter to video
def process_video(input_path, output_path, filter_function):
    """Applies a filter to a video and saves the output."""
    clip = VideoFileClip(input_path)
    
    def process_frame(frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert MoviePy frame to OpenCV format
        processed_frame = filter_function(frame)
        return cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)  # Convert back to RGB
    
    new_clip = clip.fl_image(process_frame)
    new_clip.write_videofile(output_path, codec="libx264", fps=clip.fps)
    print(f"Processed video saved as: {output_path}")

# Get user input
filter_options = {
    "1": apply_cinematic,
    "2": apply_gloomy,
    "3": apply_grayscale,
    "4": apply_brighten,
    "5": apply_darken
}

print("Choose a filter:")
print("1 - Cinematic")
print("2 - Gloomy")
print("3 - Grayscale")
print("4 - Brighten")
print("5 - Darken")

choice = input("Enter filter number: ")

if choice not in filter_options:
    print("Invalid choice. Exiting.")
    exit()

filter_function = filter_options[choice]

# Process multiple videos
input_folder = "clips/"
output_folder = "filtered_clips/"

os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith((".mp4", ".avi", ".mov")):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"filtered_{filename}")
        print(f"Processing {filename}...")
        process_video(input_path, output_path, filter_function)

print("All videos processed successfully!")
