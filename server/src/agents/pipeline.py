"""ADK pipeline definitions.

`generation_pipeline` runs PhysicsManimAgent → ValidatorAgent

Agents communicate through shared session state. Key state keys:
- `original_question_text`, `validator_feedback`  (input to Coder)
- `manim_code`, `video_path`                       (Coder outputs)
- `vlm_validation_result`, `validation_result`     (Validator outputs)

Each pipeline gets its own Coder + Validator instance so concurrent runs do not
share state inside the LlmAgent objects.
"""

from google.adk.agents import SequentialAgent

from src.agents.physicsManimAgent import make_physics_manim_agent
from src.agents.validatorAgent import make_validator_agent

_generation_physics_manim_agent = make_physics_manim_agent()
_generation_validator_agent = make_validator_agent()

generation_pipeline = SequentialAgent(
    name="PhysicsGenerationPipeline",
    description=(
        "Sequential pipeline that converts a physics question into a ManimCE animation "
        "video and validates output quality. "
        "Runs: Manim Coder -> Validator"
    ),
    sub_agents=[_generation_physics_manim_agent, _generation_validator_agent],
)
