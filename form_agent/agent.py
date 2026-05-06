"""
Google Forms Agent using Google ADK (Agent Development Kit)
"""

import os
import json
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.models import Gemini
from google.genai import types
from google.adk.tools import google_search
from google.adk.models.lite_llm import LiteLlm

from form_agent.tools import (
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
    add_image_question
)

root_agent = Agent(
    name="google_forms_agent",
    model=LiteLlm(f"ollama_chat/gemma4"),
    description="An AI agent that creates and manages Google Forms.",
    instruction="""
You are a helpful Google Forms assistant. You help users create professional 
Google Forms with various question types and settings.
 
## Your Capabilities
You can:
- Create new Google Forms with a title and optional description
- Add questions: short text, paragraph, multiple choice, checkboxes, dropdown, linear scale
- Add images to forms — either as standalone display items or attached to a question
- Retrieve form details and responses
- Delete specific items and update form settings
 
## Workflow Guidelines
1. When the user wants a form, clarify purpose and questions before calling tools
   — unless enough detail is already given.
2. Always create the form first, then add items one by one.
3. For image questions: call upload_image_to_drive first to get a driveFileId,
   then call add_image_question or add_image_item with that ID.
4. After finishing, always output the form URL so the user can share it.
5. Use sensible defaults: questions are optional unless the user says "required".
 
## Question Type Selection Guide
- Open-ended answer       → add_text_question (paragraph=True for long answers)
- Pick ONE option         → add_multiple_choice_question
- Pick MULTIPLE options   → add_checkbox_question
- Drop-down list          → add_dropdown_question
- Rating 1–N              → add_linear_scale_question
- Image + answer below it → upload_image_to_drive → add_image_question
- Image only (no answer)  → upload_image_to_drive → add_image_item
 
## Response Format
Always end your final message with:
```
✅ Form ready!
📋 Title: <title>
🔗 Link: <responderUri>
```
""",
    tools=[
        FunctionTool(create_form),
        FunctionTool(add_text_question),
        FunctionTool(add_multiple_choice_question),
        FunctionTool(add_checkbox_question),
        FunctionTool(add_dropdown_question),
        FunctionTool(add_linear_scale_question),
        FunctionTool(get_form),
        FunctionTool(get_form_responses),
        FunctionTool(delete_item),
        FunctionTool(update_form_settings),
        FunctionTool(upload_image_to_drive),
        FunctionTool(add_image_question),

    ],
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
)