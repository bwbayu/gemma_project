# src/tools/gif_converter.py
"""
Tool wrapper around mp42gif so ADK agents can call it.
"""

import os
from src.utils.mp42gif import mp4_to_gif_best_quality


def convert_mp4_to_gif(
    input_mp4: str,
    fps: int = 15,
    width: int = 960,
) -> dict:
    """Convert a .mp4 animation file to a .gif file for embedding in Google Forms.

    Call this BEFORE upload_image_to_drive when video_path ends with .mp4.

    Args:
        input_mp4: Absolute or relative path to the source .mp4 file.
        fps: Frames per second for the output GIF (default 15).
        width: Output width in pixels; height is scaled proportionally (default 960).

    Returns:
        dict with:
          - output_gif (str): Path to the generated .gif file.
          - success (bool): True if conversion succeeded.
          - error (str): Present only if conversion failed.
    """
    if not os.path.exists(input_mp4):
        return {"success": False, "error": f"File not found: {input_mp4}"}

    output_gif = os.path.splitext(input_mp4)[0] + ".gif"

    try:
        mp4_to_gif_best_quality(input_mp4, output_gif, fps=fps, width=width)
        return {"success": True, "output_gif": output_gif}
    except Exception as exc:
        return {"success": False, "error": str(exc)}