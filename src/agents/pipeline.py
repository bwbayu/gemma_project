from google.adk.agents import SequentialAgent

from src.agents.physicsManimAgent import physics_manim_agent
from src.agents.validatorAgent import validator_agent

pipeline = SequentialAgent(
    name="PhysicsAnimationPipeline",
    description=(
        "Sequential pipeline that converts a physics question into a ManimCE animation video. "
        "Runs: Manim Coder → Validator"
    ),
    sub_agents=[physics_manim_agent, validator_agent],
)
