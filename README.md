<div align="center">

# 🎵 Canta Social Copilot

**Your AI-powered social media strategy engine for X and LinkedIn.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

</div>

---

## Overview

**Canta Social Copilot** is an AI-driven content operations platform that helps creators and professionals research, draft, review, schedule, and analyze social media content for **X (Twitter)** and **LinkedIn** — all from a single, unified workspace.

Every public action is gated behind an approval and policy layer. Canta never publishes, comments, or engages on your behalf without explicit human authorization.

## ✨ Features

### Strategy & Voice Engine
- Brand identity, voice tone, audience segments, and content pillar configuration
- AI learns your writing style and adapts drafts to match

### Content Studio
- AI-powered idea generation from RSS feeds, URLs, notes, and documents
- Platform-specific draft generation (X posts, X threads, LinkedIn articles)
- Quality scoring with warnings for unsupported claims, repetition, and policy violations
- Image attachment support with cloud storage

### Publishing & Scheduling
- Full content lifecycle: **Idea → Draft → Review → Approved → Scheduled → Published**
- LinkedIn OAuth integration for direct API publishing
- X assisted-manual publishing workflow
- Content calendar with scheduled job management

### Analytics & Experiments
- CSV import and manual metric entry for both platforms
- Performance dashboard with top-performing content insights
- A/B experiment tracking with variant-level metric comparison
- Automated weekly performance reports powered by AI

### Engagement Assistant
- Context-aware reply drafting for conversations
- Voice-consistent response suggestions
- Manual approval required for every engagement action

### Security & Compliance
- Supabase Auth with JWT-verified API endpoints
- Full audit trail for every generated, edited, approved, and published item
- Release-level controls (Observe → Draft → Approve → Integrate → Schedule)
- Global publishing kill switch

## 🏗️ Architecture

```
┌──────────────────────────────────┐
│       React + TypeScript UI      │  ← Vercel
│         (Vite + Supabase Auth)   │
└──────────────┬───────────────────┘
               │ HTTPS + JWT
┌──────────────▼───────────────────┐
│       FastAPI Backend            │  ← Render
│  ├── Strategy & Voice Service    │
│  ├── Content Generation (Groq)   │
│  ├── Quality & Policy Engine     │
│  ├── Scheduling (APScheduler)    │
│  ├── Platform Adapters           │
│  │   ├── LinkedIn (OAuth API)    │
│  │   └── X (Manual + API)        │
│  └── Analytics & Reporting       │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│     Supabase (PostgreSQL)        │
│  ├── Database                    │
│  ├── Auth                        │
│  └── Storage (Images)            │
└──────────────────────────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier works)
- A [Groq](https://groq.com) API key (free tier available)

### Backend Setup

```bash
cd backend
python -m venv ../.venv
..\.venv\Scripts\Activate.ps1
pip install -e "../backend[dev]"

# Run database migrations
..\.venv\Scripts\alembic.exe upgrade head

# Start the development server
..\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in your browser for local development.

### Environment Configuration

This project supports both local development and deployed hosting. Use the split below:

- Backend values go into `.env.example`
- Frontend values go in .env.local.example`

**Backend** (`.env.example`):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string for Supabase or your deployed database |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SUPABASE_JWKS_URL` | Optional URL for the Supabase project's public signing keys; defaults to `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. Backend access tokens must use ES256 (ECC P-256). |
| `BACKEND_BASE_URL` | Public base URL of the FastAPI backend, e.g. `http://127.0.0.1:8000` or your Render URL |
| `FRONTEND_ORIGIN` | Frontend origin used for CORS and redirect handling, e.g. `http://127.0.0.1:5173` or your Vercel URL |
| `INFERENCE_PROVIDER` | AI provider (`openai_compatible`) |
| `INFERENCE_BASE_URL` | Groq API base URL |
| `INFERENCE_API_KEY` | Your Groq API key |
| `INFERENCE_MODEL` | Model name (e.g. `gpt-oss-120b`) |
| `LINKEDIN_CLIENT_ID` | LinkedIn OAuth app client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth app client secret |
| `X_CLIENT_ID` | X OAuth app client ID |
| `X_CLIENT_SECRET` | X OAuth app client secret |
| `X_REFRESH_TOKEN_ENCRYPTION_KEY` | Fernet key used to encrypt X refresh tokens at rest. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and store only in the backend environment. |

**Frontend** (`.env.local.example`):

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key |
| `VITE_API_URL` | Backend API base URL, e.g. `http://127.0.0.1:8000` or your Render backend URL |

> OAuth callbacks use the backend public URL and the frontend origin configured in the backend env values.

Before deploying OAuth refresh-token support, set `X_REFRESH_TOKEN_ENCRYPTION_KEY` in the backend environment and run `alembic upgrade head` from the `backend` directory against the configured database. Keep the encryption key stable and backed up: changing or losing it makes saved X refresh tokens unreadable. Then reconnect X once to grant `offline.access` and save a refresh token. Existing X connections do not acquire a refresh token automatically; until reconnected, the app will prompt to reconnect when the access token expires.

The backend verifies Supabase access tokens with the project's published ES256 signing keys. Set `SUPABASE_URL` to the same Supabase project used by the frontend. `SUPABASE_JWKS_URL` is normally left blank so the backend derives the project's JWKS endpoint. When deploying this change, remove the obsolete `SUPABASE_JWT_SECRET` variable from Render, set or confirm `SUPABASE_URL`, and redeploy the backend. No frontend auth environment variable changes are required.

## 🛡️ Safety Model

Canta Social Copilot is designed with safety as a core principle:

- **No browser automation** against X or LinkedIn
- **No password collection** or session replay
- **No CAPTCHA solving** or bot-detection avoidance
- **No scraping** of restricted pages, profiles, or connections
- **No autonomous engagement** — every public action requires human approval
- **Official APIs only** where access has been explicitly granted
- **Full audit trail** of every action taken

## 📦 Deployment

This project is designed to run on a cloud deployment stack while still supporting local development:

| Component | Recommended Host |
|---|---|
| Frontend | [Vercel](https://vercel.com) |
| Backend | [Render](https://render.com) |
| Database | [Supabase](https://supabase.com) |
| AI Engine | [Groq](https://groq.com) |

For deployed use, set the backend `BACKEND_BASE_URL` and `FRONTEND_ORIGIN` to the live Render and Vercel URLs respectively, and point `VITE_API_URL` in the frontend to the deployed backend URL.

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 G. A. (Ner0)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ✍️ Author

**G. A. (Ner0)**

---

<div align="center">
  <sub>Built with ❤️ for creators who value authenticity over automation.</sub>
</div>
