from .schema import PhysicsIR
import json

def format_ir_validation_error(errors: list[str], original_ir: dict) -> str:
    """
    Format IR validation errors into a string that can be fed back to the Parser.
    """
    error_msg = "The generated Physics IR JSON failed validation with the following errors:\n"
    for err in errors:
        error_msg += f"- {err}\n"
    error_msg += "\nPlease fix the JSON to satisfy these constraints."
    return error_msg

def format_syntax_error(error_output: str, original_code: str) -> str:
    """
    Format Manim syntax errors into a string that can be fed back to the Compiler.
    """
    error_msg = f"Manim execution failed with the following error:\n```\n{error_output}\n```\n"
    error_msg += "Please fix the code. Do not change the underlying physics logic."
    return error_msg
