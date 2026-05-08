from google.adk.agents import LlmAgent
from google.genai import types
from google.adk.models import Gemini

from src.tools.python_repl import python_repl
from src.tools.manim_docs import (
    get_class_info,
    get_class_info_batch,
    search_manim_classes,
    list_animation_classes,
    list_mobject_classes,
    get_class_methods,
    get_method_info,
    get_direction_constants,
)
from src.tools.manim_runner import execute_manim_code

IR_COMPILER_INSTRUCTION = """You are a Manim Compiler.
Given a Physics IR JSON, produce a working animated scene that visualizes the objects and forces exactly as described.
Do NOT reason about physics — just compile the JSON into Manim code.

## WORKFLOW
1. Read the JSON.
2. Call `get_class_info_batch` for every Manim class you plan to use before writing code.
3. Use `python_repl` for coordinate calculations if needed.
4. Write the complete scene code following the structure below.
5. Call `execute_manim_code(manim_code=<code>, scene_name=<PascalCaseName>)` to render.
6. If error → read the full error, fix the specific bug, retry.
7. Output ONLY the final working Python code — no markdown fences, no explanation.

## SCENE STRUCTURE
```python
from manim import *
import numpy as np

class PascalCaseSceneName(Scene):
    def construct(self):
        self.camera.background_color = BLACK
        # Follow the IR precisely.
        self.wait(2)
```

## NO LATEX — MANDATORY
LaTeX is NOT installed. Any LaTeX call crashes the renderer.
- NEVER: `MathTex`, `Tex`, `Brace.get_text()`, `Brace.get_tex()`
- ALWAYS: `Text("F = ma")` using Unicode for math symbols

## RETRY FEEDBACK
{validator_feedback}
"""

ir_compiler_agent = LlmAgent(
    name="IRCompilerAgent",
    model=Gemini(model="gemma-4-26b-a4b-it"),
    # generate_content_config=types.GenerateContentConfig(
    #     thinking_config=types.ThinkingConfig(thinking_level="high")
    # ),
    instruction=IR_COMPILER_INSTRUCTION,
    tools=[
        python_repl,
        execute_manim_code,
        get_class_info,
        get_class_info_batch,
        search_manim_classes,
        list_animation_classes,
        list_mobject_classes,
        get_class_methods,
        get_method_info,
        get_direction_constants,
    ],
    output_key="manim_code",
    description="Compiles Physics IR JSON into Manim Python code.",
)
