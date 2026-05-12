import subprocess

def mp4_to_gif_best_quality(input_mp4: str, output_gif: str, fps: int = 15, width: int = 960):
    """Convert an MP4 to a high-quality GIF using a two-pass ffmpeg approach: palette generation then palette-based encoding."""
    palette_file = "palette.png"

    # 1) Generate an optimized color palette from the video
    subprocess.run([
        "ffmpeg", "-i", input_mp4,
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,palettegen=max_colors=256:stats_mode=full",
        "-y", palette_file
    ], check=True)

    # 2) Use that palette to create a high-quality GIF
    subprocess.run([
        "ffmpeg", "-i", input_mp4, "-i", palette_file,
        "-lavfi", f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
        "-loop", "0", "-y", output_gif
    ], check=True)

if __name__ == "__main__":
    mp4_to_gif_best_quality("input.mp4", "output.gif", fps=15, width=960)
