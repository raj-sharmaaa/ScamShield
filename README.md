# ScamShield

ScamShield is an explainable scam and phishing detector for URLs, emails, SMS, WhatsApp messages, and suspicious text. Paste something that feels wrong and get a risk score, a verdict, the signals that influenced it, and a practical next step.

This repository contains a working full-stack foundation:

- Next.js 16 + TypeScript frontend dashboard
- FastAPI + Pydantic 2 backend API
- A deterministic, explainable rules engine with rule IDs, evidence, severity, confidence, and recommendations
- SQLite persistence for local scan history and reports
- A repository boundary ready to be replaced with PostgreSQL
- Public test cases, API docs, rate limiting, CORS configuration, Docker support, and backend tests

The ML/NLP layer is deliberately not faked. The current rules engine is a transparent baseline that makes product behavior testable. A future model can implement the same analysis contract without changing the dashboard.

## Optional AI explanations

ScamShield includes a server-side OpenAI explanation adapter. It does not choose the risk score or findings; it only rewrites the plain-language summary using the deterministic result. It is disabled by default.

After revoking any accidentally exposed key and creating a replacement, configure it in the backend environment, never in frontend code:

```bash
export OPENAI_API_KEY='your-rotated-key'
export AI_ANALYSIS_ENABLED=true
export AI_MODEL=gpt-4o-mini
```

Then start the API. The key is read only by FastAPI, requests have an 8-second timeout, output is constrained to a short JSON explanation, and any provider failure falls back to the rules summary. Do not put provider keys in `NEXT_PUBLIC_*` variables, source files, GitHub issues, or chat messages.

## Quick start

### Frontend only

```bash
npm install
npm run dev
```

Open http://localhost:3000. If the API is unavailable, the interface automatically uses the matching local TypeScript rules engine and labels the result `Local engine`.

### Full stack

Use two terminals from the project root:

```bash
# Terminal 1
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
npm run dev
```

Or launch both processes with one command from the project root:

```bash
npm run dev:fullstack
```

This requires the backend virtual environment to be active, or FastAPI and Uvicorn to be installed in the active Python environment.

Copy `.env.example` to `.env.local` if you want to configure the frontend API URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The backend stores local data in `backend/data/scamshield.db`. That directory is created automatically and should not be committed.

### Docker

Docker Compose runs the API with a persistent SQLite volume:

```bash
docker compose up --build
```

The API will be available at http://localhost:8000 and its interactive docs at http://localhost:8000/docs.

## API

The API is versioned under `/api/v1`.

### `GET /health`

Returns service status and the active engine version.

### `GET /metrics`

Returns in-process detector request counts by verdict. These counters reset when the API restarts and are intended for local demos until a metrics backend is added.

### `POST /api/v1/analyze`

Analyzes content and optionally saves the scan.

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
	-H 'content-type: application/json' \
	-d '{
		"type": "Message",
		"content": "Urgent: send your password and gift card payment now",
		"save_result": true
	}'
```

The response contains:

- `score`: integer from 0 to 100
- `verdict`: `Safe`, `Caution`, or `High risk`
- `summary`: short plain-language explanation
- `findings`: rule ID, label, detail, severity, matched evidence, and recommendation
- `confidence`: current engine confidence estimate
- `engine`: detector version for auditability
- `created_at` and a unique analysis `id`

### `GET /api/v1/history?limit=20`

Returns recent saved scans. `limit` accepts 1 to 100.

### `GET /api/v1/stats`

Returns total scans, high-risk count, caution count, safe count, and average score. This powers the future dashboard analytics view.

### `GET /api/v1/test-cases`

Returns public recruiter-friendly scenarios covering delivery scams, account locks, benign invoices, and prize bait.

### `POST /api/v1/reports`

Accepts a user correction with `reason` equal to `missed_scam`, `false_positive`, or `other`. Reports are stored for future evaluation and model improvement.

## Detection engine

The current engine is intentionally inspectable. It checks for:

1. Urgency and deadline pressure
2. Password, OTP, passcode, and login requests
3. Irreversible or unusual payment methods
4. Fake prizes and unrealistic rewards
5. Shortened URLs
6. Fear-based account language
7. Suspicious sender top-level domains
8. Numeric, encoded, or deceptive URL hosts

Each rule has a stable ID such as `identity.credentials` or `link.shortened`. The score is capped below 100 and starts with a small URL prior when a link is present. This is a baseline, not a guarantee of safety: a safe verdict never means a message is proven trustworthy.

## Architecture

```text
Browser (Next.js)
		|
		| POST /api/v1/analyze
		v
FastAPI application
		|
		+-- request validation and CORS
		+-- in-memory IP rate window
		+-- explainable detector
		+-- repository interface
						|
						+-- SQLite for local development
						+-- PostgreSQL adapter planned for production
```

Important code locations:

- `app/page.tsx`: dashboard and scan interaction
- `lib/api.ts`: browser-to-API client with local fallback
- `lib/analyzer.ts`: frontend fallback engine
- `backend/app/main.py`: HTTP routes, CORS, and rate limiting
- `backend/app/analyzer.py`: backend detector and public test cases
- `backend/app/schemas.py`: request and response contracts
- `backend/app/repository.py`: persistence boundary
- `backend/app/config.py`: environment-backed settings
- `backend/app/services.py`: analysis orchestration
- `backend/app/url_inspector.py`: safe lexical URL inspection
- `backend/app/rate_limit.py`: thread-safe sliding-window limiter
- `backend/app/security.py`: fingerprints and request security helpers
- `backend/app/metrics.py`: in-process detector metrics
- `scripts/check_project.py`: source structure verification
- `scripts/seed_demo.py`: local demo data seeder
- `backend/tests/test_api.py`: API behavior tests
- `backend/tests/test_analyzer.py`: detector and URL inspection tests
- `backend/tests/test_repository.py`: persistence tests

The repository intentionally contains multiple small modules instead of one giant backend file. This keeps detector, transport, persistence, security, metrics, and configuration concerns independently testable.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API URL used by the browser |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `DATABASE_URL` | `sqlite:///./data/scamshield.db` | Local persistence URL |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP API request limit |

The current repository adapter intentionally rejects non-SQLite URLs rather than silently pretending to support PostgreSQL. For production, replace `ScanRepository` with a SQLAlchemy or asyncpg adapter using the same methods and migrations.

## Development commands

```bash
# Frontend
npm run dev
npm run build

# Backend
python3 -m pytest backend/tests -q
cd backend && uvicorn app.main:app --reload
```

## Security notes

- Do not send secrets, real passwords, or private customer data to a development instance.
- The current detector does not fetch or visit submitted URLs, which avoids SSRF in the starter service.
- URL analysis is lexical only; it does not claim domain reputation, malware status, or page safety.
- Rate limiting is in-memory and per process. Use a shared Redis limiter behind a load balancer.
- SQLite is suitable for local development only. Use PostgreSQL with encrypted connections and migrations in production.
- Add authentication, audit logging, secret management, request tracing, and abuse monitoring before public deployment.
- Treat model output as advisory. Never auto-delete messages or block accounts solely from one score.

## Roadmap

### Detection

- Add a trained text classifier with calibrated probabilities
- Add URL reputation providers behind a safe, isolated fetch worker
- Add brand impersonation and homoglyph detection
- Add language detection and multilingual scam patterns
- Add evaluation datasets, precision/recall reporting, and threshold tuning

### Platform

- Replace SQLite with PostgreSQL migrations and a connection pool
- Add user accounts, workspaces, and authenticated scan history
- Add Redis-backed rate limiting and a background job queue
- Add structured logs, OpenTelemetry traces, and error monitoring
- Add CI for frontend build, API tests, linting, dependency audits, and container scans

### Product

- Build the full history and analytics views from `/history` and `/stats`
- Add report feedback flow from the result panel
- Add shareable public test-case links
- Add browser extension and email-forwarding ingestion with explicit consent

## License

See [LICENSE](LICENSE).