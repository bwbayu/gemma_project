# src/tools/python_repl.py
# how to test out : .\env\Scripts\python -c "from src.tools.python_repl import python_repl; print(python_repl('x=10\nprint(x)'))"

import traceback, subprocess, sys, json

_MAX_CODE_LENGTH = 10000
_EXEC_TIMEOUT_SECONDS = 10

# integrate input string code and actual python code that contain import, try/except, extract output
_WORKER_SCRIPT = r"""
import contextlib, io, json, math, traceback, ast, re
import numpy as np

SAFE_GLOBALS = {
    "__builtins__": {
        "print": print,
        "range": range,
        "len": len,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "getattr": getattr,
        "type": type,
        "repr": repr,
        "True": True,
        "False": False,
        "None": None,
    },
    "math": math,
    "np": np,
    "numpy": np,
    "pi": math.pi,
    "DEGREES": math.pi / 180,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sqrt": math.sqrt,
    "radians": math.radians,
    "degrees": math.degrees,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ast": ast,
    "re": re,
    "json": json,
}

# code input
code = __CODE_PAYLOAD__
stdout_buf = io.StringIO()
local_vars = {}

try:
    # get the bytecode/code object from compile
    compiled = compile(code, "<python_repl_subprocess>", "exec")

    # copy namespace
    globals_copy = dict(SAFE_GLOBALS)
    globals_copy["__builtins__"] = dict(SAFE_GLOBALS["__builtins__"])

    # Capture stdout (print output) while executing compiled code.
    # Example: if code is 'x=10; print(x)', stdout_buf will contain "10\n".
    with contextlib.redirect_stdout(stdout_buf):
        exec(compiled, globals_copy, local_vars)

    # Capture public local variables created/updated by exec.
    # Example: if code is 'x=10', local_vars may contain {"x": 10}.
    captured = {k: repr(v) for k, v in local_vars.items() if not k.startswith("_")}

    result = {"status": "success", "output": stdout_buf.getvalue(), "locals": captured}
except Exception:
    result = {
        "status": "error",
        "output": stdout_buf.getvalue(),
        "error": traceback.format_exc(),
    }

# return result as json
print(json.dumps(result))
"""

def python_repl(code: str):
    """
    Agent Tools to execute python code on a subprocess and return the result back to the agent.
    
    Use this tool to:
    - Verify physics calculations (force magnitudes, ratios, trigonometric decompositions)
    - Compute exact Manim coordinates and positions (polygon vertices, arrow endpoints)
    - Test mathematical expressions before using them in code
    - Parse and inspect Python code using the ast module (for code validation)

    Available in sandbox: math, numpy (as np), trig functions (sin, cos, tan, sqrt, etc.),
    DEGREES constant (pi/180), ast module, re module, json module.

    NOT available: file I/O, network, subprocess, os, sys, exec, eval, __import__.

    Args:
        code: Python code string to execute. Max 10000 characters.

    Returns:
        dict with:
          - 'status': 'success' or 'error'
          - 'output': captured stdout from print() calls
          - 'locals': dict of variable names to their repr() values (on success)
          - 'error': traceback string (on error)
    """
    if len(code) > _MAX_CODE_LENGTH:
        return {
            "status": "error",
            "output": "",
            "error": f"Code exceeds maximum length of {_MAX_CODE_LENGTH} characters ({len(code)} given).",
        }
    
    # syntax check by compile it first
    try:
        # <python_repl_tool> is just filename
        # exec is compiler mode, it's the same thing as run "python python_repl_tool.py"
        compile(code, "<python_repl_tool>", "exec")
    except SyntaxError:
        # catch syntax error, return it as error, so next model can fix it on next iteration of retry
        return {
            "status": "error",
            "output": "",
            "error": traceback.format_exc(),
        }
    
    # if there is no syntax error, run the actual code on subprocess

    # replace __CODE_PAYLOAD__ on _WORKER_SCRIPT with actual code
    script = _WORKER_SCRIPT.replace("__CODE_PAYLOAD__", repr(code))

    # run the script on subprocess, return error after 10 seconds timeout
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=_EXEC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "output": "",
            "error": f"Code execution timed out after {_EXEC_TIMEOUT_SECONDS} seconds.",
        }
    except Exception:
        return {
            "status": "error",
            "output": "",
            "error": traceback.format_exc(),
        }
    
    # parse the output code exec from subprocess
    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {
            "status": "error",
            "output": "",
            "error": f"Subprocess returned no JSON output. Stderr: {proc.stderr}",
        }
    
    try:
        # Parse stdout as JSON directly.
        return json.loads(stdout)
    except Exception:
        # If direct parse fails, try parsing only the last non-empty line
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        if lines:
            try:
                return json.loads(lines[-1])
            except Exception:
                pass
        return {
            "status": "error",
            "output": "",
            "error": f"Could not parse subprocess result JSON. Raw stdout: {stdout}\nStderr: {proc.stderr}",
        }
