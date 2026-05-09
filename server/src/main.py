import sys, os
# Reconfigure stdout/stderr to UTF-8 on Windows where the default console
# encoding (cp1252) cannot represent Unicode box-drawing chars and em dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.agents.pipeline import pipeline
from src.agents.validatorAgent import validator_agent
from src.agents.irCompilerAgent import ir_compiler_agent
from src.utils import _build_user_message, _print_separator, _IMAGE_EXTENSIONS, _log_event, _log_event_no_content, _parse_verdict, _PROJECT_ROOT

from dotenv import load_dotenv
from google.adk.runners import Runner, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types
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


async def _run_agent_only(
    agent,
    runner_app_name: str,
    session_service,
    user_id: str,
    session_id: str,
    message: types.Content,
) -> set:
    """
    Run a single agent (or SequentialAgent) against an existing session.
    Returns the set of agent names that were seen in events.
    """
    single_runner = Runner(
        agent=agent,
        app_name=runner_app_name,
        session_service=session_service,
    )
    agents_seen = set()
    async for event in single_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        if not event.content or not event.content.parts:
            _log_event_no_content(event, agents_seen)
        else:
            _log_event(event, agents_seen)
    return agents_seen


_MAX_CODE_IN_INSTRUCTION = 3000  # chars — prevents token overflow in Validator instruction

async def _prepare_for_validator(session_service, app_name: str, user_id: str, session_id: str) -> None:
    """
    Truncate verified_manim_code in session state before the Validator runs.
    The VALIDATOR_INSTRUCTION embeds {verified_manim_code} directly, so very long
    code causes input token quota exhaustion (gemma-4-31b limit: 16k tokens/min).
    The Validator uses python_repl for actual analysis — truncation only affects
    the inline display in the instruction, not the programmatic checks.
    """
    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    code = session.state.get("verified_manim_code", "")
    if isinstance(code, str) and len(code) > _MAX_CODE_IN_INSTRUCTION:
        session.state["verified_manim_code"] = (
            code[:_MAX_CODE_IN_INSTRUCTION]
            + f"\n# ... [truncated — {len(code) - _MAX_CODE_IN_INSTRUCTION} chars omitted for token budget]"
        )
        print(f"  [TOKEN] verified_manim_code truncated: {len(code)} → {_MAX_CODE_IN_INSTRUCTION} chars")


_MAX_STAGE_RL_RETRIES = 5  # max 429 retries per individual stage call

async def _run_with_retry(
    agent,
    runner_app_name: str,
    session_service,
    user_id: str,
    session_id: str,
    message,
    stage_label: str = "",
) -> set:
    """
    Run a single agent stage with automatic 429 backoff retry.
    Raises the last exception if all retries are exhausted.
    """
    for rl_attempt in range(_MAX_STAGE_RL_RETRIES):
        try:
            return await _run_agent_only(
                agent=agent,
                runner_app_name=runner_app_name,
                session_service=session_service,
                user_id=user_id,
                session_id=session_id,
                message=message,
            )
        except Exception as exc:
            exc_str = str(exc)
            if ("RESOURCE_EXHAUSTED" in exc_str or "429" in exc_str) and rl_attempt < _MAX_STAGE_RL_RETRIES - 1:
                m = re.search(r'retry in (\d+(?:\.\d+)?)', exc_str)
                retry_secs = int(float(m.group(1))) + 5 if m else 35
                wait_secs = max(retry_secs, 30)
                label = f"[{stage_label}] " if stage_label else ""
                print(f"  [RATE LIMIT] {label}429 hit. Waiting {wait_secs}s (suggested: {m.group(1) if m else '?'}s)...")
                await asyncio.sleep(wait_secs)
            else:
                raise  # non-429 error or retries exhausted
    return set()  # unreachable, but satisfies type checker


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

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={
            "original_question_text": original_question_text,
            "validator_feedback": "",
            "verified_manim_code": "",
            # Required by VALIDATOR_INSTRUCTION template — populated later by vlm_validate_video tool
            "vlm_validation_result": "(not yet assessed — call vlm_validate_video first)",
        },
    )

    current_message = initial_message

    while attempt < max_retries:
        attempt += 1
        _print_separator(f"Attempt {attempt}/{max_retries}")

        attempt_session_id = session_id
        agents_seen = set()
        event_count = 0
        _rate_limited = False

        # ── Smart Retry: if IR already exists, skip PhysicsParser ──────────────
        pre_session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=attempt_session_id
        )
        pre_state = pre_session.state
        has_ir = bool(pre_state.get("physics_ir_json"))

        if has_ir and attempt > 1:
            # IR is still valid from a previous attempt. Only re-run Compiler + Validator.
            # Reset code/validation keys so IRCompiler regenerates fresh code with feedback.
            print("  [SMART] IR already parsed — skipping PhysicsParser.")
            pre_state["verified_manim_code"] = ""
            pre_state["vlm_validation_result"] = "(not yet assessed — call vlm_validate_video first)"

            # Remove stale scene_script.py so IRCompiler always writes a fresh file
            _script_path = os.path.join(_PROJECT_ROOT, "output", "scene_script.py")
            if os.path.exists(_script_path):
                os.remove(_script_path)
                print("  [SMART] Removed stale scene_script.py")

            for stage_agent, stage_label in [(ir_compiler_agent, "IRCompiler"), (validator_agent, "Validator")]:
                print(f"  [SMART] Running stage: {stage_label}")
                if stage_label == "Validator":
                    await _prepare_for_validator(session_service, app_name, user_id, attempt_session_id)
                try:
                    extra = await _run_with_retry(
                        agent=stage_agent,
                        runner_app_name=app_name,
                        session_service=session_service,
                        user_id=user_id,
                        session_id=attempt_session_id,
                        message=current_message,
                        stage_label=stage_label,
                    )
                    agents_seen.update(extra)
                except Exception as stage_exc:
                    print(f"  [SMART] Stage '{stage_label}' failed after retries: {stage_exc}")
                    break

        else:
            # ── Full pipeline run (first attempt or no IR yet) ──────────────────
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
                    # Use the actual suggested retry delay + small buffer; minimum 30s
                    retry_secs = int(float(m.group(1))) + 5 if m else 35
                    wait_secs = max(retry_secs, 30)
                    print(f"\n  [RATE LIMIT] Waiting {wait_secs}s (suggested: {m.group(1) if m else '?'}s)...")
                    await asyncio.sleep(wait_secs)
                    rl_retry += 1

                    # --- Smart Resume: pick up from where the 429 hit ---
                    mid_session = await session_service.get_session(
                        app_name=app_name, user_id=user_id, session_id=attempt_session_id
                    )
                    mid_state = mid_session.state

                    # NOTE: Cannot wrap in a new SequentialAgent (ADK single-parent constraint).
                    # Run each remaining stage via its own temporary Runner.
                    resume_stages: list = []
                    if mid_state.get("verified_manim_code"):
                        print("  [RESUME] Code already generated. Running Validator only...")
                        resume_stages = [(validator_agent, "Validator")]
                    elif mid_state.get("physics_ir_json"):
                        print("  [RESUME] IR exists. Running IRCompiler then Validator...")
                        resume_stages = [
                            (ir_compiler_agent, "IRCompiler"),
                            (validator_agent, "Validator"),
                        ]
                    else:
                        print("  [RESUME] No usable state. Retrying full pipeline...")
                        attempt -= 1
                        _rate_limited = True

                    if not _rate_limited:
                        for stage_agent, stage_label in resume_stages:
                            print(f"  [RESUME] Running stage: {stage_label}")
                            if stage_label == "Validator":
                                await _prepare_for_validator(session_service, app_name, user_id, attempt_session_id)
                            try:
                                extra_seen = await _run_with_retry(
                                    agent=stage_agent,
                                    runner_app_name=app_name,
                                    session_service=session_service,
                                    user_id=user_id,
                                    session_id=attempt_session_id,
                                    message=current_message,
                                    stage_label=stage_label,
                                )
                                agents_seen.update(extra_seen)
                            except Exception as resume_exc:
                                print(f"  [RESUME] Stage '{stage_label}' failed after retries: {resume_exc}")
                                break

        if _rate_limited:
            continue  # restart while loop for full retry

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

            # Update session state so agents see the new feedback
            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
            session.state["validator_feedback"] = previous_feedback

            # Feedback message for the next IRCompiler run
            current_message = types.Content(
                role="user",
                parts=[types.Part(text=f"The previous attempt failed validation. Please fix the issues and provide a corrected version.\n\n{previous_feedback}")]
            )
            print(f"\n  Retrying with validator feedback (smart retry — PhysicsParser skipped)...")
        else:
            print(f"\n  Max retries ({max_retries}) reached.")


    if feedback:
        print(f"  Last validator feedback: {feedback[:500]}")
    if last_video_path:
        print(f"  Last rendered (failed validation): {last_video_path}")

    return ""

async def run_pipeline(
    question_arg: str,
    max_retries: int = 10,
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
        default=10,
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
