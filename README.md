# GroupFind

**Turn your Instagram group chat into a trip plan — activities extracted, deduped, and ready to book.**

🔗 Live: [groupfind.vercel.app](https://groupfind.vercel.app)

---

## Why I built this

Planning a trip to Indonesia with friends, we were firing Reels and posts into our group chat all week. By the time it came to book anything, half the recommendations were buried under 300 messages and nobody remembered what we'd agreed on.

GroupFind is a one-step fix: export your Instagram chat, upload the JSON, get back the actual places mentioned with booking info, organized, ready to share with the group.

## How it works

1. User exports their Instagram chat from the app (Instagram's built-in data export)
2. User uploads the chat JSON to GroupFind
3. Backend parses messages and pulls out shared Reels and posts
4. A two-phase LLM pipeline turns those into structured activities
5. Frontend shows a reviewable list with booking links

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌───────────────┐
│  Next.js UI  │ ──> │   FastAPI    │ ──> │ Celery worker │
│  (Vercel)    │     │   gateway    │     │  (LLM calls)  │
└──────────────┘     └──────┬───────┘     └───────┬───────┘
                            │                      │
                            ▼                      ▼
                     ┌──────────────┐      ┌───────────────┐
                     │  PostgreSQL  │      │  Groq / Llama │
                     └──────────────┘      │     3.1       │
                                           └───────────────┘
```

**Stack:** Next.js · FastAPI · Celery · PostgreSQL · Llama 3.1 (via Groq) · Docker Compose

## Design decisions

**Two-phase LLM pipeline, not one giant prompt.**
Phase 1 extracts activity candidates from the Instagram messages (name, location hints, context). Phase 2 enriches each activity with booking details. Splitting this meant:
- Phase 1 failures don't burn Phase 2 tokens
- Each phase has a tighter, testable prompt
- Intermediate results persist in Postgres, so re-runs are cheap

**Llama 3.1 on Groq, not GPT-4 or Claude.** 
The extraction task is simple enough that a small model with a clean prompt handles it well, and Groq's inference speed means a 200-message chat processes in seconds, not minutes. For a personal project paid out of pocket, this was the difference between "usable" and "too expensive to share with friends."

**Celery for async LLM work.**
A large chat can take 30+ seconds end-to-end. Running that inside an HTTP request would time out and feel broken. Celery pushes the work to a background worker and the frontend polls for status.

**Docker Compose for local dev.**
Four services (Next.js, FastAPI, Celery worker, Postgres) is past the point where I want to remember four terminal commands.

## Running locally

```bash
git clone https://github.com/alvaropran/groupfind
cd groupfind
cp .env.example .env   # fill in GROQ_API_KEY, DATABASE_URL, etc.
docker-compose up
```

Frontend: `localhost:3000` · API: `localhost:8000`

## What I'd do differently

- **Structured output is fragile.** The LLM is prompted to return JSON, which works most of the time but occasionally breaks. A production version would use constrained decoding or Groq's native structured output.
- **Booking links come from the LLM.**  That means occasional hallucinated URLs. The right fix is routing activity names through the Google Places API for verified links.
- **No cross-run dedupe.** If a user uploads two overlapping chats, they get duplicate activities. A content hash on the activity would merge them.

## Tech

**Backend:** Python, FastAPI, Celery, PostgreSQL, Groq SDK
**Frontend:** TypeScript, Next.js
**Infra:** Docker Compose, Vercel
