import sys, os
# Reconfigure stdout/stderr to UTF-8 on Windows where the default console
# encoding (cp1252) cannot represent Unicode box-drawing chars and em dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.agents.pipeline import pipeline
from src.utils import _build_user_message, _print_separator, _IMAGE_EXTENSIONS, _log_event, _log_event_no_content, _parse_verdict

from dotenv import load_dotenv
from google.adk.runners import Runner, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import InMemorySessionService
from authlib.deprecate import AuthlibDeprecationWarning
import asyncio, warnings, argparse, re

# ignore warning
warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature PLUGGABLE_AUTH is enabled\.",
    category=UserWarning,
)
# 

load_dotenv()

async def _run_pipeline_loop(
    question_arg: str,
    max_retries: int,
    app_name: str,
    user_id: str,
    session_id: str,
) -> str:
    """
    Inner pipeline loop
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=pipeline,
        app_name=app_name,
        session_service=session_service,
    )

    initial_message = _build_user_message(question_arg)
    last_video_path = ""
    previous_feedback = ""
    feedback = ""

    if os.path.isfile(question_arg):
        ext = os.path.splitext(question_arg)[1].lower()
        if ext in _IMAGE_EXTENSIONS:
            original_question_text = (
                f"[Image input: {question_arg}] See the image in conversation history for ground truth."
            )
        else:
            with open(question_arg, "r", encoding="utf-8") as f:
                original_question_text = f.read().strip()
    else:
        original_question_text = question_arg

    _MAX_RL_RETRIES = 5   # max 429 pauses per validation attempt
    attempt = 0
    rl_retry = 0          # incremented on each 429; keeps session IDs unique

    while attempt < max_retries:
        attempt += 1
        _print_separator(f"Attempt {attempt}/{max_retries}")

        attempt_session_id = f"{session_id}_attempt_{attempt}_rl{rl_retry}"
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=attempt_session_id,
            state={
                "original_question_text": original_question_text,
                "validator_feedback": previous_feedback,
                "verified_manim_code": "",
            },
        )

        current_message = initial_message

        # Run the sequential pipeline
        agents_seen = set()
        event_count = 0
        _rate_limited = False
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=attempt_session_id,
                new_message=current_message,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                event_count += 1
                if not event.content or not event.content.parts:
                    _log_event_no_content(event, agents_seen)
                    continue
                _log_event(event, agents_seen)
        except Exception as exc:
            exc_str = str(exc)
            print(f"\n  [DEBUG] Pipeline runner raised exception: {type(exc).__name__}: {exc_str[:300]}")
            if ("RESOURCE_EXHAUSTED" in exc_str or "429" in exc_str) and rl_retry < _MAX_RL_RETRIES:
                m = re.search(r'retry in (\d+(?:\.\d+)?)', exc_str)
                wait_secs = max(60, int(float(m.group(1))) + 5) if m else 65
                print(f"\n  [RATE LIMIT] Waiting {wait_secs}s before retrying attempt {attempt}...")
                await asyncio.sleep(wait_secs)
                attempt -= 1  # don't consume this attempt slot
                rl_retry += 1 # new suffix so next session ID is unique
                _rate_limited = True

        if _rate_limited:
            continue  # restart while loop with same attempt number

        print(f"\n  [DEBUG] Event loop finished. Total events: {event_count}, agents seen: {agents_seen}")

        # Read state after pipeline run
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=attempt_session_id,
        )
        state = session.state

        ir_json = state.get("physics_ir_json", "")
        if ir_json:
            os.makedirs("output", exist_ok=True)
            with open("output/physics_ir.json", "w", encoding="utf-8") as f:
                if isinstance(ir_json, str):
                    f.write(ir_json)
                elif isinstance(ir_json, dict):
                    import json
                    f.write(json.dumps(ir_json, indent=2, ensure_ascii=False))
                else:
                    f.write(ir_json.model_dump_json(indent=2))
            print(f"  Saved Physics IR to: output/physics_ir.json")

        video_path = state.get("video_path", "")
        if video_path and os.path.exists(video_path):
            last_video_path = video_path

        validation_raw = state.get("validation_result", "")
        verdict, feedback, suggested_fixes = _parse_verdict(validation_raw)

        _print_separator()
        print(f"  Validator verdict : {verdict}")
        if feedback:
            print(f"  Feedback          : {feedback[:200]}")
        if video_path:
            print(f"  Video path        : {video_path}")

        # Flow decision based on validator output
        if verdict == "PASS":
            return video_path
        
        if attempt < max_retries:
            fix_lines = "\n".join(f"  - {f}" for f in suggested_fixes) if suggested_fixes else "  (none specified)"
            raw_feedback = (
                f"VALIDATION FAILED on attempt {attempt}/{max_retries}.\n\n"
                f"Feedback:\n{feedback}\n\n"
                f"Suggested fixes:\n{fix_lines}\n\n"
                "Please rewrite the animation from scratch and address all issues above."
            )
            _MAX_FEEDBACK = 2000
            previous_feedback = (
                raw_feedback[:_MAX_FEEDBACK] + "..." if len(raw_feedback) > _MAX_FEEDBACK else raw_feedback
            )
            print(f"\n  Retrying with validator feedback...")
        else:
            print(f"\n  Max retries ({max_retries}) reached.")

    if feedback:
        print(f"  Last validator feedback: {feedback[:500]}")
    if last_video_path:
        print(f"  Last rendered (failed validation): {last_video_path}")

    return ""

async def run_pipeline(
    question_arg: str,
    max_retries: int = 3,
    timeout: int = 1200,
) -> str:
    """
    Run the Concept → Coder → Validator pipeline with external retry on FAIL.

    Returns the path to the generated video (may be empty string on total failure).
    """
    app_name = "physics_animator"
    user_id = "user"
    session_id = "session_main"

    try:
        return await asyncio.wait_for(
            _run_pipeline_loop(
                question_arg=question_arg,
                max_retries=max_retries,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print(f"\n  ERROR: Pipeline timed out after {timeout} seconds.")
        return ""

# ENTRYPOINT
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="physics_animator",
        description="Convert a physics question (image or text) into a ManimCE animation video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --question assets/question_example/question_1.png
  python main.py --question "Sebuah balok 10 kg pada bidang miring 37°. Tentukan percepatannya."
  python main.py --question question.txt --max-retries 5
        """,
    )
    parser.add_argument(
        "--question",
        type=str,
        required=True,
        help="Path to a question image (.png/.jpg/.jpeg/.webp), text file (.txt), or inline question text.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        metavar="N",
        help="Maximum pipeline retry attempts on validation failure (default: 3).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1200,
        metavar="SECONDS",
        help="End-to-end pipeline timeout in seconds (default: 1200 = 20 minutes).",
    )
    args = parser.parse_args()
    
    # 
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_API_KEY")
    if not api_key:
        print(
            "ERROR: Gemini API key not found.\n"
            "Set the GOOGLE_API_KEY environment variable and try again.\n"
            "  export GOOGLE_API_KEY='your-api-key-here'"
        )
        sys.exit(1)

    if os.path.exists(args.question) and not os.path.isfile(args.question):
        print(f"ERROR: '{args.question}' is a directory, not a file.")
        sys.exit(1)

    # If it looks like a file path but doesn't exist, warn the user
    if (
        not os.path.isfile(args.question)
        and any(args.question.endswith(ext) for ext in _IMAGE_EXTENSIONS | {".txt", ".md"})
    ):
        print(f"WARNING: File not found: '{args.question}'. Treating as inline text.")

    # RUN PIPELINE
    print("\nPhysicsAnimator — AI Multi-Agent Physics Animation System")
    print(f"Question : {args.question[:80]}{'...' if len(args.question) > 80 else ''}")
    print(f"Max retries: {args.max_retries}")

    try:
        video_path = asyncio.run(run_pipeline(args.question, args.max_retries, args.timeout))
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Report result
    _print_separator("Result")
    if video_path and os.path.exists(video_path):
        print(f"  SUCCESS — Video generated at:\n  {video_path}")
        sys.exit(0)
    else:
        print("  FAILED — No video passed validation after all attempts.")
        sys.exit(1)


if __name__ == "__main__":
    main()