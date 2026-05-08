# src/agents/formAgent.py
"""
Google Forms Agent — ADK LlmAgent
Reads session-state keys written by the upstream pipeline:
  - original_question_text : str   (question text or image path description)
  - video_path             : str   (absolute path to the rendered .mp4 file)
  - validation_result      : str   (JSON verdict from ValidatorAgent)
and publishes the finished form URL back to state via output_key.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.models import Gemini
from src.agents.rate_limit import build_generate_content_config

from src.tools.gif_converter import convert_mp4_to_gif
from src.tools.form_tools import (
    create_form,
    add_text_question,
    add_multiple_choice_question,
    add_checkbox_question,
    add_dropdown_question,
    add_linear_scale_question,
    get_form,
    get_form_responses,
    delete_item,
    update_form_settings,
    upload_image_to_drive,
    add_image_question,
)

FORM_AGENT_INSTRUCTION = """You are a Google Forms Publisher Agent. Your job is to
package a physics animation video into a Google Form question so students can watch
the animation and submit their answer.

## YOUR INPUTS (from session state)
- `{original_question_text}` — the original physics question (text or image path label)
- `{video_path}` — absolute path to the rendered animation video on disk
- `{validation_result}` — JSON verdict from the Validator (use this to confirm the
  animation passed before publishing; if it did not PASS, note that in the form description)

## REQUIRED WORKFLOW — follow this order exactly

### Step 1 — Verify the video path
Check that `{video_path}` is non-empty. If it is empty, create a form with title
"Physics Question" and a text description noting no animation was produced, then stop.

### Step 2 — Convert MP4 to GIF
Call `convert_mp4_to_gif` with:
- input_mp4: value of `{video_path}`
- fps: 15
- width: 960

If it returns success=False, fall back to uploading the raw mp4 path directly in
Step 3 (Drive will still accept it).
Use `output_gif` from the result as the path for Step 3.

### Step 3 — Upload the GIF to Google Drive
Call `upload_image_to_drive` with:
- image_path: the gif path from Step 2 (or mp4 path as fallback)

### Step 4 — Create the form
Call `create_form` with:
- title: "Physics Quiz #1"
- description: A brief context sentence such as:
  "Watch the animation and answer the question correctly with your explanation."

### Step 5 — Add the animation as an image question
Call `add_image_question` with:
- form_id: from Step 4
- question_title: the specific question the student must answer, extracted from
  `{original_question_text}` and text "Show your working / solution steps". Concise. Never include the numeric answer. 
- drive_file_id: from Step 3
- alt_text: "Physics animation"
- paragraph: True
- required: True
- index: 0

### Step 6 — Output the result
Return ONLY this JSON object (no markdown fences, no extra text):
{
  "form_url": "<responderUri>",
  "form_edit_url": "<editUri>",
  "form_id": "<formId>",
  "drive_file_id": "<driveFileId>",
  "gif_path": "<gif path or empty string>",
  "status": "published"
}

## RULES
- Never reveal the numeric answer in any form field title or description.
- If any tool call fails, include "status": "error" and "error": "<message>" in the JSON.
- Always end with the JSON object — it is captured as form_result in session state.
- Use get_form only if you need to verify item indices before calling delete_item.
- Do NOT call get_form_responses — this agent only creates, never reads responses.
"""

form_agent = LlmAgent(
    name="FormPublisherAgent",
    model=Gemini(model="gemma-4-31b-it"),
    generate_content_config=build_generate_content_config(),
    instruction=FORM_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(convert_mp4_to_gif),
        FunctionTool(create_form),
        FunctionTool(add_text_question),
        FunctionTool(add_multiple_choice_question),
        FunctionTool(add_checkbox_question),
        FunctionTool(add_dropdown_question),
        FunctionTool(add_linear_scale_question),
        FunctionTool(get_form),
        FunctionTool(delete_item),
        FunctionTool(update_form_settings),
        FunctionTool(upload_image_to_drive),
        FunctionTool(add_image_question),
    ],
    output_key="form_result",
    description=(
        "Converts the rendered MP4 animation to GIF, uploads it to Google Drive, "
        "and publishes it as a question inside a new Google Form."
    ),
)
