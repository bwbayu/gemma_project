# VisiQ

> From static questions to animated problems — designed to make students reason, not retrieve.

VisiQ is a teacher-facing tool that converts text or image-based physics questions into short Manim animations. Teachers create a workspace (backed by a Google Form), upload questions, review the generated animations, and approve the good ones — approved questions are appended automatically to the workspace's Google Form so students answer them by observing the animation rather than by reading raw text or image input.

---

## The Problem

In the era of LLMs, standard physics homework and unproctored exams have effectively lost their security. A student can paste a question — text or photo — into any chat model and receive a worked solution in seconds. The model does the *observing* and the *modelling* for them, which are precisely the skills physics education is supposed to develop.

This isn't hypothetical. In the 2025 HEPI/Kortext Student Generative AI Survey, **88% of full-time undergraduates** reported using generative AI for assessments, and the share submitting AI-generated content **"without editing"** more than doubled in a single year (3% → 8%). In a 2025 AAC&U / Elon University faculty survey, **90% of faculty** said GenAI will diminish students' critical-thinking skills and **78%** reported that cheating has increased on their campuses since these tools became available.

The cost is hidden but compounding: students stop practising the foundational habit of looking at a situation, picking out the relevant objects and variables, and translating them into a model. Current assessment frameworks are no longer protecting that skill.

## Our Solution

VisiQ reframes each question as a short video animation of the physical scenario. By moving the problem off the page, we eliminate the ability to copy-paste or upload it into an LLM:

- The student watches the animation and has to identify the geometry, the given values, the forces, and what the question is actually asking.
- This mirrors how real physics works — observe the phenomenon first, then build the model.
- A multi-agent validator powered by **Gemma** enforces an **anti-cheat constraint**: the final numerical answer must never appear in the animation. Students see the setup, not the solution.
- The pipeline focuses on physics first, but the same approach generalises to any subject where observation matters more than the wording of a prompt.

---

## Demo

A short walkthrough of VisiQ — uploading a physics question, the multi-agent pipeline generating the animation, and the teacher approving it into a Google Form.

[▶ Watch the demo on YouTube](https://youtu.be/VIDEO_ID)

---

## Architecture

![Architecture](assets/architecture.jpg)

## Generation Pipeline

![Generation Pipeline](assets/flowchart-pipeline.jpg)

## Multi-Agent Architecture

The generation pipeline runs as a `SequentialAgent` composed of two Google ADK `LlmAgent`s — **PhysicsManimAgent** (writes and renders ManimCE code, `thinking: high`) and **ValidatorAgent** (reviews the rendered video against 5 criteria including the anti-cheat constraint, `thinking: default`). On `VERDICT == FAIL` the validator's feedback is written back into session state and PhysicsManimAgent retries; on `VERDICT == PASS` the job transitions to `awaiting_review` where the teacher takes over.

![Multi-Agent Architecture](assets/multiagent%20architecture.jpg)

---

## Screenshots / Demo

**Dashboard**

![Dashboard](assets/dashboard.png)

**Review panel**

![Review panel](assets/review-panel.png)

**Generated animation example**

![Example output](assets/example-output.gif)

---

## Tech Stack

- **Frontend:** React 19, React Router 7, TypeScript 6, Vite 8, Tailwind CSS 3, Radix UI, Lucide icons.
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn.
- **AI / Generation:** Google Gemma-4-31b-it (via `google-genai`), Google ADK (Agent Development Kit), Manim CE 0.19.
- **Cloud / Storage:** Firestore, Google Cloud Storage, Google Forms API, Google Drive API, Cloud Run.
- **Tooling:** Docker, Firebase Hosting, ffmpeg.

---

## How to Run (local)

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- `ffmpeg` on the system PATH (required for MP4 → GIF conversion)
- A Google Cloud project with Firestore, Cloud Storage, and the Gemini API enabled
- OAuth credentials (`credentials.json` + `token.json`) for the Google Forms / Drive APIs, placed under `server/env/`

### Backend

```bash
cd server
python -m venv .venv
.venv\Scripts\activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env              # then fill in the values listed below
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-dir src
```

The interactive API explorer is at `http://localhost:8001/docs`.

### Frontend

```bash
cd client
npm install
copy .env.example .env              # set VITE_API_BASE_URL=http://localhost:8001
npm run dev
```

Open `http://localhost:5173`.

> The shipped `client/.env.example` defaults to port `8000`. If you run the backend on `8001` (as above), make sure your `.env` reflects that.

For deeper setup notes see [client/README.md](client/README.md) and [server/README.md](server/README.md).

---

## Environment Variables

| Variable | Scope | Required | Description |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | client | yes | Base URL of the FastAPI backend (e.g. `http://localhost:8001`). |
| `GOOGLE_API_KEY` | server | yes | Gemini API key used by the agents. |
| `GOOGLE_CLOUD_PROJECT` | server | yes | GCP project ID hosting Firestore and Cloud Storage. |
| `GOOGLE_APPLICATION_CREDENTIALS` | server | yes | Path to the service account JSON used for Firestore + GCS. |
| `GCS_BUCKET_NAME` | server | yes | Cloud Storage bucket for uploaded sources and rendered media. |
| `FIREBASE_STORAGE_BUCKET` | server | yes | Firebase storage bucket (typically the same value as `GCS_BUCKET_NAME`). |
| `FIRESTORE_DATABASE_ID` | server | no | Firestore database ID. Defaults to `physicsanimator-hackathon`. |
| `PIPELINE_MODE` | server | no | `legacy_generation` (default), `legacy_full_fallback`, or `mock`. |
| `PIPELINE_MAX_RETRIES` | server | no | Max retries inside the pipeline. Defaults to `1`. |
| `PIPELINE_TIMEOUT_SECONDS` | server | no | Per-job timeout. Defaults to `1200`. |
| `CORS_ALLOWED_ORIGINS` | server | no | Comma-separated origins. Defaults to `http://localhost:5173,http://localhost:8001`. |
| `API_PREFIX` | server | no | API path prefix. Defaults to `/api/v1`. |
| `GOOGLE_CSE_API_KEY` | server | no | Used by reference-image search tooling. |
| `GOOGLE_CSE_CX` | server | no | Custom Search Engine ID used alongside `GOOGLE_CSE_API_KEY`. |

---

## Deployment

The backend ships as a multi-stage Docker image and runs on Google Cloud Run; the client builds to a static bundle and is hosted on Firebase Hosting. See [DEPLOYMENT.md](DEPLOYMENT.md) for the full step-by-step (Artifact Registry, Secret Manager, Cloud Run, Firebase).

---

## Documentation

- [client/README.md](client/README.md) — frontend overview, directory tree, and page reference.
- [server/README.md](server/README.md) — backend overview, directory tree, multi-agent pipeline, and API reference.
- [DEPLOYMENT.md](DEPLOYMENT.md) — deployment guide.
---

## License

Released under the MIT License. Built for the Gemma Hackathon 2026.
