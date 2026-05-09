from google.adk.agents import SequentialAgent

from src.agents.physicsManimAgent import physics_manim_agent
from src.agents.validatorAgent import validator_agent
from src.agents.formAgent import form_agent

pipeline = SequentialAgent(
    name="PhysicsAnimationPipeline",
    description=(
        "Sequential pipeline that converts a physics question into a ManimCE animation "
        "video and publishes it as a Google Form question. "
        "Runs: Manim Coder → Validator → Form Publisher"
    ),
    sub_agents=[physics_manim_agent, validator_agent, form_agent],
)
