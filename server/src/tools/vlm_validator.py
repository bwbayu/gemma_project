"""VLM visual check: sample frames from the rendered video and ask Gemini for a structured visual verdict."""

import os
import json
from google.adk.tools import ToolContext
from google.genai import types, Client
from src.tools.frame_extractor import extract_key_frames, save_frames_to_disk
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.resolve())

def vlm_validate_video(tool_context: ToolContext) -> dict:
    """
    ADK Tool that performs visual validation of the rendered Manim video.
    Extracts frames and compare them with the original question.
    """
    state = tool_context.state
    video_path = state.get("video_path", "")
    original_question = state.get("original_question_text", "")
    
    if not video_path or not os.path.exists(video_path):
        return {
            "visual_verdict": "SKIP",
            "reason": f"Video file not found at {video_path}. Rendering might have failed."
        }

    # 1. Extract frames. Sampling 3 frames at ~5/50/90% of the video avoids the
    # all-black opening and trailing frames Manim produces and keeps the VLM
    # request to a single Gemini call.
    frames_bytes = extract_key_frames(video_path, n_frames=3)
    if not frames_bytes:
        return {
            "visual_verdict": "SKIP",
            "reason": "Failed to extract frames from video."
        }
    
    # 2. Save frames for debugging/audit
    debug_dir = os.path.join(_PROJECT_ROOT, "output", "vlm_frames")
    save_frames_to_disk(frames_bytes, debug_dir)

    # 3. Call Gemini 2.0 Flash
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_API_KEY")
    if not api_key:
        return {
            "visual_verdict": "SKIP",
            "reason": "API Key missing for VLM validation."
        }

    client = Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
    
    prompt = f"""You are a Physics Education Visual Reviewer. 
Compare the provided frames from an animation with the original physics question.

ORIGINAL QUESTION:
{original_question}

TASK:
Verify if the animation VISUALLY represents the physics problem correctly.
1. Force directions: Weight points DOWN, Normal is perpendicular to surface, etc.
2. Object setup: Matches the scenario (inclines, pulleys, blocks).
3. Given values: Numbers visible in labels match the question.
4. Visual quality: No overlapping labels, text is readable, arrows don't go off-screen.
5. Anti-cheat: Ensure the FINAL ANSWER or solution steps are NOT visible in the frames.

Return ONLY a JSON object:
{{
  "visual_verdict": "PASS" or "FAIL",
  "visual_issues": ["list of specific visual problems found"],
  "visual_strengths": ["list of what looks correct"],
  "pedagogical_check": "does it hide the answer?"
}}
"""

    parts = [types.Part.from_text(text=prompt)]
    for i, fb in enumerate(frames_bytes):
        parts.append(types.Part.from_bytes(data=fb, mime_type="image/png"))

    try:
        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        result = json.loads(response.text)
        # Store as JSON string so VALIDATOR_INSTRUCTION template interpolates cleanly
        state["vlm_validation_result"] = json.dumps(result, ensure_ascii=False)
        return result
        
    except Exception as e:
        print(f"  [VLM] Error during Gemini 2.0 Flash call: {e}")
        error_result = {
            "visual_verdict": "SKIP",
            "reason": f"VLM API call failed: {str(e)}"
        }
        state["vlm_validation_result"] = json.dumps(error_result, ensure_ascii=False)
        return error_result
