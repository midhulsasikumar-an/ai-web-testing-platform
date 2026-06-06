# SignalTrack - AI Web Testing Platform

A collaborative AI-based website testing system built to automate test execution, generate and track bugs, and visualize testing insights through an interactive dashboard.

## Run Locally

Run everything from the project root with one command:

```powershell
npm run dev
```

This starts:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8001`

For first-time setup:

```powershell
npm install
npm run install:all
npm run dev
```

If backend packages are missing:

```powershell
python -m pip install -r backend\requirements.txt
```

## Deploy

Deploy this repo as two services:

- Frontend: Vercel, with `frontend` as the root directory.
- Backend: Render, using `render.yaml` from the repository root.

### Vercel Frontend

Create a Vercel project from this repo and set:

- Root Directory: `frontend`
- Framework Preset: Next.js
- Build Command: `npm run build`
- Environment Variable: `NEXT_PUBLIC_API_URL=https://YOUR-RENDER-SERVICE.onrender.com`

### Render Backend

Create a Render Blueprint from this repo. The `render.yaml` file sets the build and start commands.

Set these Render environment variables:

- `MONGO_URL`
- `FRONTEND_ORIGINS=https://YOUR-VERCEL-APP.vercel.app`
- `GROQ_API_KEY`
- `OPENAI_API_KEY` if you want OpenAI-backed features

Render generates `JWT_SECRET_KEY` automatically from the blueprint.

## Tech Stack

- Frontend: Next.js 16, React 19, Tailwind CSS 4, TypeScript
- Backend: FastAPI, Uvicorn, Playwright
- Database: MongoDB Atlas
- Auth: bcrypt password hashing, JWT tokens
