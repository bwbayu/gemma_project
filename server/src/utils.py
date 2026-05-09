from google.genai import types
from google.adk.events import Event
import os, json, re
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.resolve())

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

def _print_separator(title: str = "") -> None:
    """Print a visual separator line, optionally with a centered title."""
    width = 60
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print(f"\n{'─' * width}")

def _build_user_message(question_arg: str) -> types.Content:
    """
    Build a Gemini Content message from the --question argument.

    Handles three cases:
    - Image file (.png, .jpg, etc.) → multimodal Part with image bytes
    - Text file (.txt)              → plain text Part
    - Inline string                 → plain text Part
    """
    parts: list[types.Part] = []

    # Gemini's inline blob limit is 20MB.
    _MAX_FILE_SIZE = 20 * 1024 * 1024

    if os.path.isfile(question_arg):
        file_size = os.path.getsize(question_arg)
        if file_size > _MAX_FILE_SIZE:
            raise ValueError(
                f"File too large ({file_size / 1024 / 1024:.1f} MB). "
                f"Maximum supported size is {_MAX_FILE_SIZE // 1024 // 1024} MB."
            )

        ext = os.path.splitext(question_arg)[1].lower()

        if ext in _IMAGE_EXTENSIONS:
            # [2a] Image input: send raw bytes + instruction text as a multipart message
            with open(question_arg, "rb") as f:
                image_bytes = f.read()
            mime_type = _MIME_MAP.get(ext, "image/png")
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            parts.append(types.Part(text=(
                "This is a physics exam question. Read the image carefully:\n\n"
                "1. Extract all visible text, numbers, units, and variable names.\n"
                "2. Identify any diagrams, arrows, coordinate systems, or geometric elements.\n"
                "3. Identify the physical scenario, given quantities, and what the student must find.\n\n"
                "Then write complete ManimCE Python code that animates this physics scenario.\n"
                "If any part of the image is unclear or ambiguous, state that explicitly rather than guessing."
            )))

        elif ext in {".txt", ".md"}:
            # [2b] Text file: read and send as plain text
            with open(question_arg, "r", encoding="utf-8") as f:
                question_text = f.read().strip()
            parts.append(types.Part(text=question_text))
        else:
            raise ValueError(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(sorted(_IMAGE_EXTENSIONS | {'.txt', '.md'}))}"
            )
    else:
        # [2c] Inline text argument: send directly
        parts.append(types.Part(text=question_arg))

    return types.Content(role="user", parts=parts)

def _log_event(event: Event, agents_seen: set):
    author = event.author or "pipeline"
    agents_seen.add(author)
    
    part_types = []
    for p in event.content.parts:
        if getattr(p, "thought", False):
            # Thinking part — print a preview to the terminal
            thought_text = getattr(p, "text", "") or ""
            if thought_text:
                preview = thought_text[:500].replace("\n", " ")
                if len(thought_text) > 500:
                    preview += "..."
                print(f"  [{author}] 💭 {preview}")
        elif getattr(p, "text", None):
            part_types.append("text")
        elif getattr(p, "function_call", None):
            fc = p.function_call
            part_types.append(f"tool_call:{fc.name}" if fc else "tool_call")
        elif getattr(p, "function_response", None):
            fr = p.function_response
            part_types.append(f"tool_result:{fr.name}" if fr else "tool_result")
        else:
            part_types.append("other")

    # Find the first non-thought text part for the main log line
    text = ""
    for p in event.content.parts:
        if not getattr(p, "thought", False):
            text = getattr(p, "text", None) or ""
            if text:
                break

    if text:
        preview = text[:300].replace("\n", " ")
        if len(text) > 300:
            preview += "..."
        print(f"  [{author}] {preview}")
    elif part_types:
        print(f"  [{author}] (no text) parts={part_types}")

def _log_event_no_content(event: Event, agents_seen: set):
    author = event.author or "?"
    agents_seen.add(author)
    # Dump full event attributes for Validator empty events
    if author == "Validator":
        attrs = {k: repr(v)[:200] for k, v in vars(event).items() if not k.startswith("_")}
        print(f"  [Validator] EMPTY EVENT details: {attrs}")
    else:
        print(f"  [{author}] (empty event, id={getattr(event, 'id', '?')})")

def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from LLM output text.

    Handles common LLM output patterns:
    - Pure JSON string
    - JSON wrapped in ```json ... ``` fences
    - JSON preceded/followed by explanation text

    Returns the parsed dict, or raises ValueError if no valid JSON found.
    """
    text = text.strip()

    # [1] Try direct parse — the cleanest, most common case when the LLM
    #     follows instructions correctly.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # [2] Try stripping markdown JSON fences.
    #     Matches: ```json\n{...}\n``` or ```\n{...}\n```
    match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # [3] Find the first balanced { ... } block using brace-depth tracking.
    #     Scans from each '{' and tracks nesting depth to find where it closes.
    #     This handles cases where LLM prose contains stray braces before JSON.
    i = 0
    while i < len(text):
        if text[i] == "{":
            depth = 0
            in_string = False
            escape_next = False
            for j in range(i, len(text)):
                ch = text[j]
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    if in_string:
                        escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[i : j + 1])
                        except json.JSONDecodeError:
                            break  # this '{' didn't start valid JSON, try next
            i += 1
        else:
            i += 1

    raise ValueError(f"Could not extract valid JSON from text (length={len(text)})")

def _parse_verdict(validation_raw) -> tuple[str, str, list[str]]:
    """
    Parse the validation_result state value.
    Returns (verdict, feedback, suggested_fixes).

    WHY handle both dict and str?
    ADK stores LlmAgent output in session state. The format depends on how
    the agent responded:
      - If the LLM output was valid JSON, ADK may parse it to a dict
      - If it was plain text JSON, it's stored as a string
    extract_json() handles both cases plus markdown fence wrapping.
    """
    try:
        if isinstance(validation_raw, dict):
            data = validation_raw
        elif isinstance(validation_raw, str):
            if not validation_raw.strip():
                return "FAIL", "Validator returned empty output — the agent may have failed silently or timed out.", []
            data = _extract_json(validation_raw)
        else:
            return "FAIL", f"Could not parse validator output (unexpected type: {type(validation_raw).__name__}).", []

        raw_verdict = data.get("verdict", "FAIL")
        if not isinstance(raw_verdict, str):
            return "FAIL", f"Verdict field has invalid type '{type(raw_verdict).__name__}', expected string.", []
        verdict = raw_verdict.strip().upper()
        if verdict not in ("PASS", "FAIL"):
            return "FAIL", f"Unknown verdict value '{verdict}', expected PASS or FAIL.", []
        # Coerce types defensively — LLM may return feedback as int/dict
        # or suggested_fixes as a scalar string instead of a list.
        raw_feedback = data.get("feedback", "No feedback provided.")
        feedback = str(raw_feedback) if not isinstance(raw_feedback, str) else raw_feedback

        raw_fixes = data.get("suggested_fixes", [])
        if isinstance(raw_fixes, list):
            fixes = [str(f) for f in raw_fixes]
        elif isinstance(raw_fixes, str):
            fixes = [raw_fixes]
        else:
            fixes = []

        return verdict, feedback, fixes
    except (json.JSONDecodeError, ValueError) as exc:
        # Log raw output for debugging — helps identify what the validator actually returned
        preview = ""
        if isinstance(validation_raw, str):
            preview = validation_raw[:300].replace("\n", " ")
        return "FAIL", f"Could not parse validator output (JSON error: {exc}). Raw preview: {preview}", []