import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from google.adk.tools import ToolContext
from src.utils import _PROJECT_ROOT


def strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences (```python ... ```) if present.

    LLMs frequently wrap code output in markdown fences even when instructed
    not to. This strips them so we write clean Python to disk.

    Pattern breakdown:
      ^```          — literal backtick fence at string start
      (?:python|py)? — optional language hint (python or py)
      \\s*\\n        — any whitespace/newline after the opening fence
      (.*?)         — capture group: the actual code (non-greedy)
      ```\\s*$       — closing fence at string end
    """
    code = code.strip()
    # Pattern: optional ```python or ``` at start, optional ``` at end
    match = re.match(r"^```(?:python|py)?\s*\n(.*?)```\s*$", code, re.DOTALL)
    if match:
        return match.group(1).strip()
    return code


def _check_code_safety(
    code: str,
    blocked_modules: set[str],
    blocked_calls: set[str],
) -> str | None:
    """Check code for dangerous imports/calls via AST. Returns error message or None.

    Checks:
    - Direct imports: import os, from os import ...
    - Direct calls: eval(), exec(), __import__(), open(), compile(), getattr(), delattr()
    - Attribute calls: builtins.eval(), obj.__import__(), etc.
    - Double-underscore attribute access: __subclasses__, __globals__, __builtins__, etc.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Can't parse AST — fall back to regex scan on raw text.
        for mod in blocked_modules:
            if re.search(rf"\bimport\s+{mod}\b", code) or re.search(rf"\bfrom\s+{mod}\b", code):
                return f"blocked import '{mod}' detected (regex fallback)"
        for call in blocked_calls:
            if re.search(rf"\b{call}\s*\(", code):
                return f"blocked call '{call}()' detected (regex fallback)"
        return None

    # Dangerous dunder attributes that enable sandbox escapes
    _BLOCKED_ATTRS = {
        "__subclasses__", "__globals__", "__builtins__", "__import__",
        "__loader__", "__spec__", "__code__", "__reduce__",
    }

    for node in ast.walk(tree):
        # Check `import X` and `import X.Y`
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module in blocked_modules:
                    return f"blocked import '{alias.name}'"
        # Check `from X import ...` and `from X.Y import ...`
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_module = node.module.split(".")[0]
                if top_module in blocked_modules:
                    return f"blocked import 'from {node.module}'"
        # Check function calls: both direct (eval()) and attribute (obj.eval())
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in blocked_calls:
                return f"blocked call '{func.id}()'"
            # Catch attribute-based calls: builtins.eval(), os.system(), etc.
            if isinstance(func, ast.Attribute) and func.attr in blocked_calls:
                return f"blocked call via attribute '.{func.attr}()'"
        # Check dangerous dunder attribute access (e.g. __subclasses__, __globals__)
        elif isinstance(node, ast.Attribute):
            if node.attr in _BLOCKED_ATTRS:
                return f"blocked attribute access '.{node.attr}'"

    return None


def execute_manim_code(
    manim_code: str,
    scene_name: str,
    tool_context: ToolContext,
) -> dict:
    """
    Executes ManimCE Python code by writing it to a file and running the manim
    CLI renderer via subprocess. Returns success with the output video path, or
    failure with a truncated error message.

    Args:
        manim_code: Complete Python source code containing a ManimCE Scene class.
                    Must start with 'from manim import *' and define a Scene subclass.
        scene_name: The exact name of the Scene class to render, e.g. 'PulleySystemScene'.

    Returns:
        dict with keys:
          - 'status': 'success' or 'error'
          - 'video_path': absolute path to the rendered .mp4 (only on success)
          - 'error_message': truncated error output (only on error)
    """
    manim_code = strip_markdown_fences(manim_code)

    # Safety check: reject code that imports dangerous modules or calls risky
    # builtins. Uses AST inspection so comments and string literals don't
    # trigger false positives. Falls back to regex if AST parsing fails.
    _BLOCKED_MODULES = {
        "os", "sys", "subprocess", "shutil", "socket", "http",
        "urllib", "requests", "pathlib", "importlib", "ctypes",
        "multiprocessing", "threading", "signal", "webbrowser",
        "ftplib", "smtplib", "telnetlib", "xmlrpc", "pickle",
        "shelve", "tempfile", "glob", "io",
    }
    _BLOCKED_CALLS = {
        "__import__", "eval", "exec", "compile",
        "open", "getattr", "delattr", "setattr",
        "globals", "locals", "vars", "dir",
        "breakpoint", "input",
    }

    safety_error = _check_code_safety(manim_code, _BLOCKED_MODULES, _BLOCKED_CALLS)
    if safety_error:
        return {
            "status": "error",
            "error_message": (
                f"Code rejected: {safety_error}. "
                "Manim code should only import from 'manim' and standard math libraries. "
                "Remove any os, sys, subprocess, socket, or network imports."
            ),
        }

    tool_context.state["verified_manim_code"] = manim_code

    output_dir = os.path.join(_PROJECT_ROOT, "output")
    os.makedirs(output_dir, exist_ok=True)

    script_path = os.path.join(output_dir, "scene_script.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(manim_code)

    cmd = [
        sys.executable, "-m", "manim",
        "-ql",
        "--media_dir", output_dir,
        script_path,
        scene_name,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=_PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_message": (
                "Manim rendering timed out after 120 seconds. "
                "Simplify the scene: reduce animation steps, avoid heavy LaTeX, "
                "use fewer objects."
            ),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error_message": f"Unexpected error launching manim subprocess: {exc}",
        }

    if result.returncode == 0:
        target_name = f"{scene_name}.mp4"
        video_path = ""
        for root, _, files in os.walk(os.path.join(output_dir, "videos")):
            if target_name in files:
                video_path = os.path.join(root, target_name)
                break

        if video_path:
            tool_context.state["video_path"] = video_path
            return {
                "status": "success",
                "video_path": video_path,
            }
        else:
            return {
                "status": "error",
                "error_message": (
                    f"Manim exited successfully but '{target_name}' not found in {output_dir}/videos/.\n"
                    f"Ensure the scene class name '{scene_name}' exactly matches the class in your code.\n"
                    f"Stdout (last 500 chars):\n{result.stdout[-500:]}"
                ),
            }
    else:
        stderr = result.stderr or ""
        stdout = result.stdout or ""

        # Keep the most informative tail of stderr
        if len(stderr) > 1500:
            stderr = "...(truncated — showing last 1500 chars)...\n" + stderr[-1500:]

        return {
            "status": "error",
            "error_message": (
                f"Manim rendering failed (exit code {result.returncode}).\n\n"
                f"STDERR:\n{stderr}\n\n"
                f"STDOUT (last 300 chars):\n{stdout[-300:]}"
            ),
        }
