# SignalTrack — AI Web Testing Platform

A collaborative AI-based website testing system built to automate test execution, generate and track bugs, and visualize testing insights through an interactive dashboard.

## Quick Start

Run everything from the **project root** with a single command:

```bash
npm install
npm run dev
```

This starts both the **Next.js frontend** (port 3000) and the **FastAPI backend** (port 8000) concurrently.

### First-Time Setup

```bash
# Install all dependencies (frontend npm + backend pip)
npm run install:all

# Start the development servers
npm run dev
```

### Individual Services

```bash
# Frontend only
npm run dev:frontend

# Backend only
npm run dev:backend
```

## Default Credentials

Create a new account via the signup form, or use the signup API:

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo User", "email": "demo@bugtracker.io", "password": "demo123"}'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | MongoDB connection status |
| `POST` | `/api/auth/signup` | Create new account |
| `POST` | `/api/auth/login` | Authenticate & get JWT |
| `GET` | `/api/auth/me` | Get current user (JWT required) |
| `POST` | `/api/tests/start` | Start a new test run |
| `GET` | `/api/tests` | List all test runs |
| `GET` | `/api/tests/:id` | Get specific test run |
| `GET` | `/api/bugs` | List all bugs |
| `GET` | `/api/bugs/:id` | Get specific bug |

## Tech Stack

- **Frontend**: Next.js 16, React 19, TailwindCSS 4, TypeScript
- **Backend**: FastAPI, Uvicorn, Playwright
- **Database**: MongoDB Atlas
- **Auth**: bcrypt password hashing, JWT tokens

## Environment Variables

Backend `.env` file (`backend/.env`):

```
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
MONGO_URL=your-mongodb-connection-string
```

## Notes

- The backend requires Python 3.10+ and the packages listed in `backend/requirements.txt`.
- The frontend runs on Next.js 16 with React 19.
- Auth tokens are stored in `localStorage` and auto-validated on page load.
