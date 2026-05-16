"""Parses a physics question into the Physics IR JSON schema (used by the experimental IR-based path)."""

from google.adk.agents import LlmAgent
from google.genai import types
from google.adk.models import Gemini

PHYSICS_PARSER_INSTRUCTION = """You are a Physics Problem Parser. Your task is to extract structured physics data from the given problem text.
Output ONLY valid JSON matching the PhysicsIR schema.

Rules:
- Gravity direction MUST be "DOWN".
- Normal force MUST be "PERPENDICULAR_TO_SURFACE".
- Use relative positions (x: -1 to 1, y: -1 to 1).
- Use enum values exactly as defined.
- Do NOT output any explanation, markdown formatting, or text outside the JSON.
"""
from src.ir.schema import PhysicsIR
physics_parser_agent = LlmAgent(
    name="PhysicsParserAgent",
    model=Gemini(model="gemma-4-31b-it"),
    instruction=PHYSICS_PARSER_INSTRUCTION,
    output_schema=PhysicsIR,
    output_key="physics_ir_json",
    description="Parses a physics question into a structured JSON representation (Physics IR).",
)
