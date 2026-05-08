# src/tools/frame_extractor.py
import av
import os
import io
from PIL import Image
from pathlib import Path

def extract_key_frames(video_path: str, n_frames: int = 3) -> list[bytes]:
    """
    Extract n_frames evenly-spaced frames from an MP4 video.
    Returns list of PNG bytes.
    
    Strategy:
    1. Open video via PyAV
    2. Calculate total frames/duration
    3. Seek to n positions (start, middle, end)
    4. Decode and convert to PNG bytes
    """
    if not os.path.exists(video_path):
        print(f"  [ERROR] Video file not found for frame extraction: {video_path}")
        return []

    frames_bytes = []
    try:
        container = av.open(video_path)
        stream = container.streams.video[0]
        
        # duration in stream base
        duration = stream.duration
        if duration is None or duration <= 0:
            # Fallback for streams with no duration info
            duration = 1000 
            
        # Time points to sample (in stream.time_base units)
        # We sample at 5%, 50%, 95% to avoid pure black starts or ends if any
        time_points = [
            int(duration * 0.05),
            int(duration * 0.50),
            int(duration * 0.90)
        ]
        
        # If user requested more or less frames, we distribute them
        if n_frames != 3:
            time_points = [int(duration * (i / (n_frames - 1)) * 0.95 + duration * 0.02) for i in range(n_frames)]

        for ts in time_points:
            container.seek(ts, stream=stream)
            # Find the next keyframe
            for frame in container.decode(video=0):
                # Convert to PIL image
                img = frame.to_image()
                
                # Convert to bytes (PNG)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                frames_bytes.append(buf.getvalue())
                break # We only need one frame per seek point
                
        container.close()
    except Exception as e:
        print(f"  [ERROR] Frame extraction failed for {video_path}: {e}")
        
    return frames_bytes

def save_frames_to_disk(frames_bytes: list[bytes], output_dir: str) -> list[str]:
    """Helper to save extracted frames for debugging."""
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i, data in enumerate(frames_bytes):
        path = os.path.join(output_dir, f"frame_{i}.png")
        with open(path, "wb") as f:
            f.write(data)
        paths.append(path)
    return paths
