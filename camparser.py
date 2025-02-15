import re
import requests
import cv2
import numpy as np
import subprocess
import time

# Fetch the webpage HTML
url = "https://mosday.ru/webcam/live.php?mitischi_im_perlovskiy"
response = requests.get(url)
html = response.text

# Search for the M3U8 URL in the HTML
# Example pattern: look for URLs ending with .m3u8
m3u8_url = 'https://www.intek-m.ru/live/st_perl/s.m3u8'

# Configuration
REFERER = "https://mosday.ru/webcam/live.php?mitischi_im_perlovskiy"
FRAME_INTERVAL = 5  # Capture a frame every 5 seconds

# FFmpeg command to stream with headers
ffmpeg_cmd = [
    'ffmpeg',
    '-headers', f'Referer: {REFERER}',
    '-i', m3u8_url,
    '-f', 'image2pipe',  # Output to pipe
    '-vf', f'fps=1/{FRAME_INTERVAL}',  # Capture 1 frame every X seconds
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',  # OpenCV uses BGR format
    '-'
]

# Start FFmpeg subprocess
process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

# Read frames from the pipe
frame_count = 0
while True:
    # Read raw frame bytes from FFmpeg
    raw_frame = process.stdout.read(480 * 240 * 3)  # Adjust resolution if needed
    if not raw_frame:
        break
    
    # Convert bytes to a numpy array (OpenCV format)
    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((480, 240, 3))
    
    # Save the frame
    filename = f"frame_{int(time.time())}.jpg"
    cv2.imwrite(filename, frame)
    print(f"Saved {filename}")
    
    # Optional: Display the frame
    cv2.imshow('Frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    time.sleep(5)

# Cleanup
process.terminate()
cv2.destroyAllWindows()