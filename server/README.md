# VisiQ — Server

The VisiQ server is a FastAPI backend that orchestrates a multi-agent pipeline (PhysicsParser → PhysicsManim → Validator → Form) to convert physics questions into Manim-rendered animations. It persists workspaces, questions, and generation jobs in Firestore, stores rendered media in Google Cloud Storage, and appends approved questions to teacher-owned Google Forms.

For the project pitch, problem statement, and global setup, see the [root README](../README.md).

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI + Uvicorn
- **Validation:** Pydantic v2
- **LLM:** Google Gemini 2.0 Flash via `google-genai`
- **Agents:** Google ADK (Agent Development Kit)
- **Animation:** Manim CE 0.19, rendered to MP4
- **Media:** ffmpeg (MP4 → GIF), PyAV, Pillow
- **Database:** Firestore
- **Storage:** Google Cloud Storage
- **External APIs:** Google Forms, Google Drive
- **Container:** Multi-stage Dockerfile, deployed to Cloud Run

---

## Directory Tree

```
server/
├── app/                                  # FastAPI HTTP layer
│   ├── main.py                           # App factory, CORS, exception handlers
│   ├── config.py                         # Pydantic Settings loaded from .env
│   ├── dependencies.py                   # DI providers (repos, services)
│   ├── api/
│   │   ├── routers/                      # health, workspaces, questions, jobs
│   │   └── schemas/                      # Pydantic request/response models
│   ├── services/                         # Business logic
│   │   ├── workspace_service.py
│   │   ├── question_service.py
│   │   ├── job_service.py
│   │   ├── pipeline_service.py           # Dispatches to legacy / legacy_full / mock pipeline
│   │   └── review_service.py             # Approve / regenerate / discard
│   ├── repositories/
│   │   ├── firestore/                    # Firestore data access (workspaces, questions, jobs, app_state)
│   │   └── storage/gcs_repo.py           # GCS upload + signed URLs
│   ├── integrations/
│   │   └── legacy_pipeline_adapter.py    # Bridge between FastAPI services and src/ pipeline
│   └── utils/errors.py                   # AppError + structured error envelope
├── src/                                  # Multi-agent generation pipeline
│   ├── app.py                            # run_generation_pipeline entrypoint
│   ├── agents/
│   │   ├── pipeline.py                   # Sequential agent composition
│   │   ├── physicsParserAgent.py         # OCR/extraction from image
│   │   ├── physicsManimAgent.py          # Gemini + Manim code generation
│   │   ├── validatorAgent.py             # VLM video validation
│   │   ├── formAgent.py                  # Google Forms append
│   │   ├── irCompilerAgent.py            # Intermediate representation
│   │   └── rate_limit.py                 # 429 retry logic
│   ├── ir/                               # IR schema, validator, patcher
│   ├── tools/
│   │   ├── manim_runner.py               # Execute Manim code
│   │   ├── python_repl.py                # Inline math evaluation
│   │   ├── manim_docs.py                 # Manim API lookup tool
│   │   ├── vlm_validator.py              # Gemini frame review
│   │   ├── gif_converter.py              # MP4 → GIF via ffmpeg
│   │   ├── frame_extractor.py            # Extract frames from video
│   │   └── form_tools.py                 # Google Forms API
│   └── utils.py
├── output/                               # Local Manim renders (mp4, gif, frames)
├── assets/                               # Reference images / palettes
├── env/                                  # OAuth tokens, credentials (gitignored)
├── Dockerfile                            # Multi-stage build for Cloud Run
├── requirements.txt
└── pyproject.toml
```

---

## Architecture

Requests follow a layered path:

1. **Routers** ([app/api/routers/](app/api/routers/)) receive HTTP requests and validate input with Pydantic schemas.
2. **Services** ([app/services/](app/services/)) apply business rules and orchestration.
3. **Repositories** ([app/repositories/](app/repositories/)) persist state in Firestore and serve files via Google Cloud Storage.
4. For generation, services call the **`legacy_pipeline_adapter`** ([app/integrations/legacy_pipeline_adapter.py](app/integrations/legacy_pipeline_adapter.py)) which invokes the multi-agent pipeline in [src/](src/).

Three pipeline modes can be selected via the `PIPELINE_MODE` env var:

| Mode | Behaviour |
| --- | --- |
| `legacy_generation` (default) | Manim Coder → Validator. |
| `legacy_full_fallback` | Manim Coder → Validator → Form append. |
| `mock` | Deterministic simulator for frontend-only iteration. |

---

## Multi-Agent Pipeline

| Agent | Role |
| --- | --- |
| **PhysicsParserAgent** | If the input is an image, uses Gemini VLM to OCR and extract the question text. Skipped for text input. |
| **PhysicsManimAgent** | Generates Manim Community Edition code that animates the scenario. Has tool access to a Python REPL (for coordinate / trig math) and a Manim docs lookup. Enforces strict physics rules and Unicode-only labels (no LaTeX — the renderer crashes on `MathTex`). Retries up to 3 times on render errors. |
| **ValidatorAgent** | Uses Gemini VLM on extracted frames to score the rendered video against five criteria: physics accuracy, question-code alignment, **pedagogical anti-cheat (the final answer must NOT appear in the animation)**, code quality, and presentation. Returns `PASS` or `FAIL`. |
| **FormAgent** | On approval, converts the MP4 to a GIF (ffmpeg), uploads to Google Drive, and appends the question + media to the workspace's Google Form. |

Job stages reported back to the client: `reading_question` → `generating_animation` → `rendering_video` → `validating_output` → `preparing_assets` → `awaiting_review` (terminal: `completed` or `failed`).

---

## API Reference

Base path: `/api/v1` (configurable via `API_PREFIX`).

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check. |
| GET | `/workspaces` | List all workspaces (newest first). |
| GET | `/workspaces/active` | Get the currently active workspace, or `null`. |
| POST | `/workspaces` | Create a workspace (provisions a backing Google Form) and mark it active. |
| POST | `/workspaces/{workspace_id}/activate` | Mark an existing workspace as active. |
| GET | `/workspaces/{workspace_id}/links` | Return the Google Form edit URL + responder URL. |
| GET | `/workspaces/{workspace_id}/questions` | List questions in a workspace (newest first). |
| POST | `/workspaces/{workspace_id}/questions` | Submit a new question (text via form field, or image upload) and enqueue a generation job. |
| GET | `/questions/{question_id}/review` | Get the review payload (validation verdict, video/GIF URLs, source) once generation completes. |
| POST | `/questions/{question_id}/approve` | Approve and append to the Google Form. |
| POST | `/questions/{question_id}/regenerate` | Reset the question and enqueue a fresh generation job. |
| POST | `/questions/{question_id}/discard` | Mark the question as discarded. |
| GET | `/jobs/{job_id}` | Get current job status and stage. |

Interactive docs are available at `/docs` (Swagger UI) and `/redoc` when the server is running.

### Examples

**Create a workspace**

```http
POST /api/v1/workspaces
Content-Type: application/json

{
  "title": "Newton's Laws Practice — Week 3",
  "description": "Quick set on free-body diagrams."
}
```

Response `201 Created`:
```json
{
  "workspaceId": "wks_01HF...",
  "formRef": {
    "formId": "1AbC...",
    "formTitle": "Newton's Laws Practice — Week 3",
    "formDescription": "Quick set on free-body diagrams.",
    "formEditUrl": "https://docs.google.com/forms/d/.../edit",
    "formResponderUrl": "https://docs.google.com/forms/d/e/.../viewform"
  },
  "createdAt": "2026-05-15T03:14:00Z",
  "updatedAt": "2026-05-15T03:14:00Z"
}
```

**Create a question (text)**

```http
POST /api/v1/workspaces/wks_01HF.../questions
Content-Type: multipart/form-data

text=A 2 kg block on a 30° frictionless incline. Find the acceleration.
```

**Create a question (image)**

```http
POST /api/v1/workspaces/wks_01HF.../questions
Content-Type: multipart/form-data

image=@question.png
```

Response `201 Created`:
```json
{
  "questionItemId": "q_01HG...",
  "jobId": "job_01HG..."
}
```

**Poll job status**

```http
GET /api/v1/jobs/job_01HG...
```

Response `200 OK`:
```json
{
  "jobId": "job_01HG...",
  "workspaceId": "wks_01HF...",
  "questionItemId": "q_01HG...",
  "stage": "validating_output",
  "status": "in_progress",
  "attempt": 1,
  "maxAttempts": 1,
  "message": "Validating rendered animation against the question.",
  "error": null,
  "createdAt": "2026-05-15T03:15:00Z",
  "updatedAt": "2026-05-15T03:17:42Z",
  "finishedAt": null
}
```

**Get review result**

```http
GET /api/v1/questions/q_01HG.../review
```

Response `200 OK`:
```json
{
  "questionItemId": "q_01HG...",
  "validation": {
    "verdict": "PASS",
    "summary": "Block, incline, and gravity vector are accurate. Answer not shown.",
    "localVideoPath": "/app/output/videos/InclineScene.mp4"
  },
  "result": {
    "videoUrl": "https://storage.googleapis.com/.../result.mp4",
    "gifUrl": null
  },
  "source": {
    "inputType": "text",
    "text": "A 2 kg block on a 30° frictionless incline. Find the acceleration.",
    "imageUrl": null
  },
  "append": {
    "status": "pending",
    "errorMessage": null
  }
}
```

**Approve and append to Google Form**

```http
POST /api/v1/questions/q_01HG.../approve
```

Response `200 OK`:
```json
{
  "questionItemId": "q_01HG...",
  "status": "added"
}
```

### Error Envelope

All `AppError`-derived failures return a structured envelope:

```json
{
  "error": {
    "code": "WORKSPACE_NOT_FOUND",
    "message": "Workspace not found.",
    "details": {}
  }
}
```

Pydantic validation errors return HTTP `422` with field-level details. Unhandled exceptions return HTTP `500`.

---

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GOOGLE_API_KEY` | yes | — | Gemini API key used by the agents. |
| `GOOGLE_CLOUD_PROJECT` | yes | — | GCP project ID hosting Firestore + GCS. |
| `GOOGLE_APPLICATION_CREDENTIALS` | yes | — | Path to the service account JSON for Firestore + GCS. |
| `GCS_BUCKET_NAME` | yes | — | Cloud Storage bucket for uploaded sources and rendered media. |
| `FIREBASE_STORAGE_BUCKET` | yes | — | Firebase storage bucket (commonly the same as `GCS_BUCKET_NAME`). |
| `FIRESTORE_DATABASE_ID` | no | `physicsanimator-hackathon` | Firestore database ID. |
| `PIPELINE_MODE` | no | `legacy_generation` | `legacy_generation`, `legacy_full_fallback`, or `mock`. |
| `PIPELINE_MAX_RETRIES` | no | `1` | Retries inside the pipeline. |
| `PIPELINE_TIMEOUT_SECONDS` | no | `1200` | Per-job timeout in seconds. |
| `CORS_ALLOWED_ORIGINS` | no | `http://localhost:5173,http://localhost:8001` | Comma-separated list of allowed origins. |
| `API_PREFIX` | no | `/api/v1` | Prefix applied to all routers. |
| `GOOGLE_CSE_API_KEY` | no | — | Custom Search API key used by reference-image tooling. |
| `GOOGLE_CSE_CX` | no | — | Custom Search Engine ID paired with `GOOGLE_CSE_API_KEY`. |

OAuth credentials for the Google Forms / Drive APIs are not env vars: place `credentials.json` and `token.json` under `server/env/` (gitignored). The Dockerfile entrypoint also accepts these via Secret Manager when deployed to Cloud Run.

---

## Setup

### Prerequisites

- Python 3.11+
- `ffmpeg` on the system PATH (required for MP4 → GIF conversion at approval time)
- A Google Cloud project with Firestore, Cloud Storage, and the Gemini API enabled
- A service account JSON with Firestore + GCS permissions
- OAuth credentials for the Google Forms / Drive APIs (interactive consent on first run produces `token.json`)

### Steps

```bash
cd server
python -m venv .venv
.venv\Scripts\activate                 # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env                 # fill in the variables documented above
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-dir src
```

Visit `http://localhost:8001/docs` for the interactive API explorer.

---

[Back to root README](../README.md)
