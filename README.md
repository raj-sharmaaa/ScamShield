# ScamShield

ScamShield is an explainable scam and phishing detector for URLs, emails, SMS, WhatsApp messages, and suspicious text. Paste something that feels wrong and get a risk score, a verdict, the signals that influenced it, and a practical next step.

This repository contains a working full-stack foundation:

- Next.js 16 + TypeScript frontend dashboard
- FastAPI + Pydantic 2 backend API
- A deterministic, explainable rules engine with rule IDs, evidence, severity, confidence, and recommendations
- SQLAlchemy persistence with SQLite for local development and PostgreSQL for hosted deployments
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

Open http://localhost:3000. If the API is unavailable, the interface automatically uses its local TypeScript rules engine and labels the result `Local engine`.

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

The backend stores local data in `backend/data/scamshield.db`. That directory is created automatically and should not be committed. Hosted environments can use PostgreSQL through `DATABASE_URL`.

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

Returns recent saved scans. `limit` accepts 1 to 100. In production, history is disabled until authentication is integrated; this prevents anonymous visitors from reading shared scan content.

### `GET /api/v1/stats`

Returns total scans, high-risk count, caution count, safe count, and average score. In production this endpoint is also disabled until authentication and per-user authorization are configured.

### `GET /api/v1/test-cases`

Returns public recruiter-friendly scenarios covering delivery scams, account locks, benign invoices, and prize bait.

### `POST /api/v1/reports`

Accepts a correction with `reason` equal to `missed_scam`, `false_positive`, or `other`. Report submission is disabled in production until authentication is integrated.

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
		+-- in-memory rate limiting locally, with optional Redis-backed shared rate limiting
		+-- explainable detector
		+-- repository interface
						|
						+-- SQLite for local development
						+-- PostgreSQL for hosted deployments
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

The repository supports SQLite locally and PostgreSQL in hosted environments. Set `DATABASE_URL` to the provider's PostgreSQL connection string for persistent production storage. Set `REDIS_URL` to a managed Redis connection string for shared rate limits across API instances; without it, limits are process-local.

## Development commands

```bash
# Frontend
npm run dev
npm run build

# Backend
python3 -m pytest backend/tests -q
cd backend && uvicorn app.main:app --reload
```

## Deployment readiness

The Next.js dashboard can be deployed to Vercel as a frontend. The FastAPI service is a separate application and must be deployed to a Python-capable host; Vercel does not automatically deploy the `backend/` directory as part of this Next.js app.

For a connected deployment:

1. Deploy the FastAPI service from `backend/` on a Python-capable host.
2. Configure that service with a persistent database. The current SQLite adapter is for local development and is not suitable for serverless production storage.
3. Set `CORS_ORIGINS` on the API to the exact deployed frontend origin (for example, `https://your-app.vercel.app`).
4. Set `NEXT_PUBLIC_API_URL` in Vercel to the public HTTPS URL of the API, then redeploy the frontend.
5. Keep `OPENAI_API_KEY` only in the backend environment. Enable `AI_ANALYSIS_ENABLED=true` only if users have been clearly informed that up to 10,000 characters of submitted content may be sent to OpenAI for explanation.

If `NEXT_PUBLIC_API_URL` is not configured, the dashboard uses its local TypeScript rules engine. Backend history, reports, and aggregate statistics will not be available in that mode. Do not present local fallback scans as cloud-persisted or AI-powered.

This repository is a development-ready foundation, not a production security service. Before opening it to public traffic, add persistent PostgreSQL storage, authentication and per-user authorization, shared rate limiting, monitoring, and a security/privacy review. The detector is heuristic and cannot certify that a message or URL is safe.

## Hosted backend (Render blueprint)

A `render.yaml` blueprint is included to provision a Docker-based FastAPI service and a managed PostgreSQL database. Review the plan and estimated costs in Render before applying it. After deployment, copy the API's public HTTPS URL into Vercel as `NEXT_PUBLIC_API_URL`, and set `CORS_ORIGINS` in Render to the exact Vercel origin. Keep AI explanations disabled unless the privacy notice and consent flow are appropriate for submitted data.

The blueprint does not create a Vercel project or set Vercel environment variables automatically. It also does not provide user authentication. In production, anonymous scan persistence, history, statistics, and reports are disabled by default. Add an identity provider and per-user authorization before enabling stored user data. Set `REDIS_URL` to a managed Redis connection string to use the distributed limiter; otherwise the limiter is process-local.

## Security notes

- Do not send secrets, real passwords, or private customer data to a development instance.
- The current detector does not fetch or visit submitted URLs, which avoids SSRF in the starter service.
- URL analysis is lexical only; it does not claim domain reputation, malware status, or page safety.
- Rate limiting is in-memory and per process. Use a shared Redis limiter behind a load balancer.
- Use PostgreSQL with encrypted connections for hosted deployments. Add formal schema migrations before evolving the database schema.
- Add an identity provider, per-user authorization, audit logging, secret management, request tracing, and abuse monitoring before enabling user-specific data features. Anonymous scan persistence, history, statistics, and reports are disabled in production by default.
- Treat model output as advisory. Never auto-delete messages or block accounts solely from one score.

## Roadmap

### Detection

- Add a trained text classifier with calibrated probabilities
- Add URL reputation providers behind a safe, isolated fetch worker
- Add brand impersonation and homoglyph detection
- Add language detection and multilingual scam patterns
- Add evaluation datasets, precision/recall reporting, and threshold tuning

### Platform

- Add formal PostgreSQL schema migrations and a connection pool
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