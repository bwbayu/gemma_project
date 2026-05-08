from google.adk.agents import SequentialAgent

from src.agents.physicsParserAgent import physics_parser_agent
from src.agents.irCompilerAgent import ir_compiler_agent
from src.agents.validatorAgent import validator_agent

pipeline = SequentialAgent(
    name="PhysicsAnimationPipeline",
    description=(
            "Physics animation generation pipeline using intermediate representation (IR). "
            "Stages: PhysicsParserAgent (problem -> IR), "
            "IRCompilerAgent (IR -> ManimCE code/video), "
            "and ValidatorAgent (verification and consistency checking)."
    ),
    sub_agents=[physics_parser_agent, ir_compiler_agent, validator_agent],
)
