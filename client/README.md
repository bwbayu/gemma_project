# VisiQ — Client

The VisiQ client is a React + TypeScript + Vite single-page app used by teachers to manage Google Form-backed question workspaces, submit physics questions (text or image), watch generation progress in real time, and approve, regenerate, or discard the generated animations. It talks to the FastAPI backend over REST and polls for job status while a question is being generated.

For the project pitch, problem statement, and global setup, see the [root README](../README.md).

---

## Tech Stack

- **Framework:** React 19 with React Router 7
- **Language:** TypeScript 6
- **Build:** Vite 8
- **Styling:** Tailwind CSS 3 (custom teal palette) + PostCSS
- **UI primitives:** Radix UI Select, Lucide icons
- **Testing:** Vitest 4
- **Lint:** ESLint 10
- **HTTP:** native `fetch` (no Axios)
- **State:** React hooks only — no Redux/Zustand
- **Hosting:** Firebase Hosting (SPA rewrites in `firebase.json`)

---

## Directory Tree

```
client/
├── src/
│   ├── app/
│   │   ├── AppShell.tsx          # Root layout: header, sidebar, <Outlet/>
│   │   └── router.tsx            # React Router route definitions
│   ├── pages/
│   │   ├── DashboardPage.tsx     # Main teacher workflow (workspaces + questions + review)
│   │   ├── SettingsPage.tsx      # Active workspace info + activity stats
│   │   ├── HelpPage.tsx          # Quick-start guide and input tips
│   │   └── NotFoundPage.tsx      # 404 fallback
│   ├── components/ui/            # Reusable primitives (Badge, Button, Card, Input, Select)
│   ├── features/
│   │   ├── api/                  # Typed HTTP clients per resource
│   │   │   ├── http.ts           # fetch wrapper, ApiError class
│   │   │   ├── workspace.ts      # Workspace endpoints
│   │   │   ├── questions.ts      # Question endpoints
│   │   │   ├── jobs.ts           # Job-status polling
│   │   │   └── review.ts         # Review / approve / regenerate / discard
│   │   └── mock/types.ts         # Shared TypeScript interfaces
│   ├── lib/cn.ts                 # Tailwind classname merger
│   ├── assets/                   # Static images and icons
│   ├── index.css                 # Tailwind base + global styles
│   └── main.tsx                  # App entry: mounts <RouterProvider/>
├── public/                       # Static assets served at root
├── vite.config.ts                # Vite + plugin config
├── tailwind.config.ts            # Tailwind theme
├── postcss.config.js
├── eslint.config.js
├── tsconfig.json                 # + tsconfig.app.json / tsconfig.node.json
├── firebase.json                 # Firebase Hosting + SPA rewrites
├── .firebaserc                   # Firebase project binding
└── package.json
```

---

## Available Pages

### `/` — Dashboard
The teacher's primary workspace. From here you can:

- Create a new workspace (which provisions a backing Google Form) or switch between existing ones.
- Submit a new question by either pasting text or uploading an image.
- Watch live generation progress as the job moves through stages (`reading_question` → `generating_animation` → `rendering_video` → `validating_output` → `preparing_assets` → `awaiting_review`).
- Review the generated animation with a video + GIF preview, alongside the original source.
- Take a decision: **Approve** (appends the question + GIF to the workspace's Google Form), **Regenerate** (re-runs the pipeline), or **Discard**.
- Open the Google Form's edit URL, or copy the responder URL for distribution to students.

### `/settings`
Read-only summary of the active workspace plus aggregate counts of questions added and questions that failed. Includes a manual refresh button to re-pull the latest stats.

### `/help`
Onboarding page with:

- A 5-step quick-start guide.
- 3 tips for writing inputs that produce good animations.
- 2 sample physics prompts to try.

### `/*` — Not Found
404 fallback for unknown routes.

> Note: `/workspace` is a legacy alias that redirects to `/`.

---

## API Layer

All HTTP calls are typed and live under [src/features/api/](src/features/api/):

- [`http.ts`](src/features/api/http.ts) — Thin `fetch` wrapper. Prefixes every request with `VITE_API_BASE_URL`, decodes the JSON body, and throws `ApiError` on a non-2xx response with the backend's structured error envelope intact.
- [`workspace.ts`](src/features/api/workspace.ts), [`questions.ts`](src/features/api/questions.ts), [`jobs.ts`](src/features/api/jobs.ts), [`review.ts`](src/features/api/review.ts) — One module per backend resource. Each exports typed functions that map 1:1 onto a backend endpoint.

**Job polling pattern:** the dashboard polls `GET /jobs/{id}` every 2000 ms while a question is being generated. A `useRef` token is used so polling can be cancelled or invalidated when the user navigates away or starts a new request, preventing stale state updates from races.

---

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | yes | `http://localhost:8000` (in `.env.example`) | Base URL of the FastAPI backend. Set to `http://localhost:8001` if you run the backend on the documented dev port. |

Vite only exposes variables prefixed with `VITE_` to the client bundle.

---

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite dev server with HMR on port 5173. |
| `npm run build` | Type-check (`tsc -b`) and build a production bundle into `dist/`. |
| `npm run preview` | Serve the production build locally. |
| `npm run lint` | Run ESLint over the project. |
| `npm run test:smoke` | Run Vitest smoke tests under `src/smoke`. |

---

## Setup

```bash
cd client
npm install
copy .env.example .env       # set VITE_API_BASE_URL to match your backend
npm run dev
```

Open `http://localhost:5173`. The backend must already be running at the URL you set in `VITE_API_BASE_URL`.

---

[Back to root README](../README.md)
