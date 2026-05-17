"""CLI + programmatic entrypoint for the ADK pipeline.

Runs `generation_pipeline` (Coder→Validator) with retry-on-FAIL: each retry
injects the validator's feedback into the next attempt so the Coder can
address the specific issue.
"""

import sys, os
# Reconfigure stdout/stderr to UTF-8 on Windows where the default console
# encoding (cp1252) cannot represent Unicode box-drawing chars and em dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.agents.pipeline import generation_pipeline
from src.agents.rate_limit import enable_rate_limit_retry_logging
from src.utils import _build_user_message, _print_separator, _IMAGE_EXTENSIONS, _log_event, _log_event_no_content, _parse_verdict

from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from authlib.deprecate import AuthlibDeprecationWarning
import asyncio, warnings, argparse

from google.adk.runners import Runner, RunConfig
from google.adk.agents.run_config import StreamingMode
# ignore warning
warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature PLUGGABLE_AUTH is enabled\.",
    category=UserWarning,
)
# 

load_dotenv()
enable_rate_limit_retry_logging()

def _resolve_original_question_text(question_arg: str) -> str:
    if os.path.isfile(question_arg):
        ext = os.path.splitext(question_arg)[1].lower()
        if ext in _IMAGE_EXTENSIONS:
            return f"[Image input: {question_arg}] See the image in conversation history for ground truth."
        with open(question_arg, "r", encoding="utf-8") as f:
            return f.read().strip()
    return question_arg


async def _run_generation_pipeline_loop(
    question_arg: str,
    max_retries: int,
    app_name: str,
    user_id: str,
    session_id: str,
) -> tuple[str, str, str]:
    """
    Backend generation loop (Coder -> Validator only).

    Returns (video_path, verdict, feedback_summary).
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=generation_pipeline,
        app_name=app_name,
        session_service=session_service,
    )

    initial_message = _build_user_message(question_arg)
    original_question_text = _resolve_original_question_text(question_arg)
    last_video_path = ""
    feedback = ""
    previous_feedback = ""

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        attempt_session_id = f"{session_id}_gen_attempt_{attempt}"
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

        async for event in runner.run_async(
            user_id=user_id,
            session_id=attempt_session_id,
            new_message=initial_message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            if not event.content or not event.content.parts:
                continue

        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=attempt_session_id,
        )
        state = session.state
        video_path = state.get("video_path", "")
        if video_path and os.path.exists(video_path):
            last_video_path = video_path

        validation_raw = state.get("validation_result", "")
        verdict, feedback, suggested_fixes = _parse_verdict(validation_raw)
        if verdict == "PASS":
            return video_path, verdict, feedback

        if attempt < max_retries:
            fix_lines = "\n".join(f"  - {f}" for f in suggested_fixes) if suggested_fixes else "  (none specified)"
            raw_feedback = (
                f"VALIDATION FAILED on attempt {attempt}/{max_retries}.\n\n"
                f"Feedback:\n{feedback}\n\n"
                f"Suggested fixes:\n{fix_lines}\n\n"
                "Please rewrite the animation from scratch and address all issues above."
            )
            # Cap the feedback we inject into the next attempt so prompt tokens
            # do not grow unboundedly across retries.
            _MAX_FEEDBACK = 2000
            previous_feedback = (
                raw_feedback[:_MAX_FEEDBACK] + "..." if len(raw_feedback) > _MAX_FEEDBACK else raw_feedback
            )

    if last_video_path:
        return last_video_path, "FAIL", feedback
    return "", "FAIL", feedback or "Generation did not produce a valid output."


async def run_generation_pipeline(
    question_arg: str,
    max_retries: int = 1,
    timeout: int = 1200,
) -> tuple[str, str, str]:
    """
    Run generation-only pipeline (Coder -> Validator) without form publishing.

    Returns (video_path, verdict, feedback_summary).
    """
    app_name = "physics_animator"
    user_id = "user"
    session_id = "session_generation"

    try:
        return await asyncio.wait_for(
            _run_generation_pipeline_loop(
                question_arg=question_arg,
                max_retries=max_retries,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return "", "FAIL", f"Generation pipeline timed out after {timeout} seconds."

# ENTRYPOINT
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="physics_animator",
        description="Convert a physics question (image or text) into a ManimCE animation video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.app --question assets/question_example/question_1.png
  python -m src.app --question "Sebuah balok 10 kg pada bidang miring 37°. Tentukan percepatannya."
  python -m src.app --question question.txt --max-retries 5
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
        video_path = asyncio.run(run_generation_pipeline(args.question, args.max_retries, args.timeout))
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
