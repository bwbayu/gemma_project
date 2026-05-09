from google.adk.agents import SequentialAgent

from src.agents.physicsManimAgent import make_physics_manim_agent
from src.agents.validatorAgent import make_validator_agent
from src.agents.formAgent import form_agent

_full_physics_manim_agent = make_physics_manim_agent()
_full_validator_agent = make_validator_agent()
_generation_physics_manim_agent = make_physics_manim_agent()
_generation_validator_agent = make_validator_agent()

pipeline = SequentialAgent(
    name="PhysicsAnimationPipeline",
    description=(
        "Sequential pipeline that converts a physics question into a ManimCE animation "
        "video and publishes it as a Google Form question. "
        "Runs: Manim Coder → Validator → Form Publisher"
    ),
    sub_agents=[_full_physics_manim_agent, _full_validator_agent, form_agent],
)

generation_pipeline = SequentialAgent(
    name="PhysicsGenerationPipeline",
    description=(
        "Sequential pipeline that converts a physics question into a ManimCE animation "
        "video and validates output quality. "
        "Runs: Manim Coder -> Validator"
    ),
    sub_agents=[_generation_physics_manim_agent, _generation_validator_agent],
)
