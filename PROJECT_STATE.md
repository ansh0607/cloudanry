# PROJECT_STATE.md — Evidence Graph

> Handoff document. Source of truth for what is built and decided.
> Update the relevant section after EVERY meaningful change (feature, file, bug fix, decision). Keep entries short and factual. Do not redo or contradict completed work without explaining why.

## Overview
Hackathon project "Evidence Graph": AI-powered media intelligence platform for NGOs, governments, and sustainability orgs. Field teams upload photos/videos tied to a project; the system (1) organizes media by project/location/timeline, (2) scores each upload's relevance via Claude vision, (3) compares before/after media with simple pixel metrics, (4) makes media searchable via Cloudinary auto-tags + keyword search, (5) runs a dual-AI "Evidence Graph" analysis (Supporting AI + Adversarial AI) producing a transparent, weighted Confidence Score for impact claims, (6) exports a shareable visual report, (7) keeps a full audit trail to original source assets.
**Hard rule:** never claim to "prove"/"verify" truth — only assess evidence strength and disclose contradictions. Language: "consistent with" / "contradiction detected"; never "verified" / "fake" / "fraud". Persistent UI banner: "This is an evidence assessment, not proof of impact."

## Tech decisions made
Fixed stack — do not substitute:
- Backend: FastAPI (Python), async endpoints
- Frontend: React + Tailwind CSS
- Media: Cloudinary (upload, EXIF/GPS extraction, AI auto-tagging, video thumbnail/frame extraction)
- Database: Firebase Firestore
- AI: Groq API (user does not use Claude; "free AI / multiple AI") — one key `GROQ_API_KEY` via env var only, never hardcoded
- Multi-AI design: different model per role (all OpenAI-compatible via https://api.groq.com/openai/v1/chat/completions, called with httpx — no vendor SDK)
  - Vision/relevance: `qwen/qwen3.8-27b` (current Groq vision model; Llama 4 Scout/Maverick deprecated as of Mar 2026 — verified from Groq docs)
  - Supporting AI: `openai/gpt-oss-120b`
  - Adversarial AI: `llama-3.3-70b-versatile`
  - All model IDs overridable via env (GROQ_MODEL_VISION / GROQ_MODEL_SUPPORTING / GROQ_MODEL_ADVERSARIAL)
- Duplicates: `imagehash` perceptual hash, ~90% similarity threshold, scanned across ALL projects
- Before/after diff: simple color-threshold metrics (green-pixel ratio / pixel-diff %) with Pillow/OpenCV, <2s, local, no ML
- Search: keyword/substring over tags + image_description, structured so embeddings can be swapped in later
- Confidence score: deterministic weighted merge (base + weighted supporting − weighted adversarial by severity), returns itemized breakdown — NOT an AI call
- Build order fixed: 1 Projects → 2 Upload → 3 Gallery → 4 Relevance → 5 Tags/Search → 6 Compare → 7 Deterministic checks → 8 Dual AI → 9 Confidence → 10 Claim dashboard → 11 Report → 12 Audit
- DEMO_MODE (env `DEMO_MODE=1`): run the ENTIRE app with zero credentials — in-memory Firestore stub (`backend/core/memory_db.py`) behind `get_db()`, local media storage (`backend/core/demo_media.py`, files in `backend/core/demo_media/uploads/` served at `/demo-files`), auto-seeded sample project/media/claim (`backend/core/seed_demo.py`, Pillow-synthesized before/after hillside images). Honesty rules kept: AI fields stay empty/None with "unavailable in demo mode" notes, descriptions prefixed "DEMO", confidence still computed by the real deterministic scorer; seed runs on startup only when DB is empty, so data re-seeds after restarts but never duplicates
- Dual-AI system prompts: USER WILL SUPPLY VERBATIM for feature #8. Ship clearly-marked placeholder defaults in `backend/prompts/claim_prompts.py` so the demo runs; replace as-is when user pastes theirs

## Features completed
Backend (FastAPI, all endpoints verified: `from backend.main import app` OK, 12 routes; 19/19 unit tests pass):
- 1 Projects CRUD — `backend/routers/projects.py`
- 2 Upload flow — `backend/routers/media.py` `POST /api/media/upload` (Cloudinary → EXIF/GPS → phash → relevance → Firestore + audit)
- 3 Gallery — `GET /api/media?project_id=&group_by=date|location` (server-side grouping)
- 4 Relevance scoring — `backend/services/relevance.py` via Groq vision `qwen/qwen3.8-27b`
- 5 Search — `backend/services/search.py` + `GET /api/search?q=&project_id=` (keyword backend, embeddings-swappable interface)
- 6 Compare — `backend/services/compare.py` + `POST /api/compare` (green-pixel ratio + pixel diff, Pillow/NumPy only — opencv dropped from deps)
- 7 Deterministic checks — `backend/services/dedup.py` (phash, 90%), `backend/services/evidence_checks.py` (EXIF/GPS)
- 8 Dual AI — `backend/services/dual_ai.py` (asyncio.gather, Supporting=openai/gpt-oss-120b, Adversarial=llama-3.3-70b-versatile) + `POST /api/claims`
- 9 Confidence — `backend/services/confidence.py` `compute_confidence()` (deterministic, itemized breakdown; base 50, supporting +15%×strength capped +40, adversarial −6/−12/−20 capped −50)
- 10 Claims API — `GET /api/claims`, `GET /api/claims/{id}`
- 11 Report — `backend/services/report.py` + `GET /api/projects/{id}/report` (self-contained HTML, donor-clean)
- 12 Audit — `backend/core/audit.py` choke point; `GET /api/media/{id}/audit`, `GET /api/audit`
- Tests: `tests/test_confidence.py`, `tests/test_search.py`, `tests/test_compare_and_dedup.py`, `tests/test_memory_db.py` (25/25 passing)
- Env: venv at `.venv/` (Python 3.14 — pins relaxed in requirements.txt; Pillow/pydantic-core have no cp314 wheels for old pins)

## Features in progress
- (nothing in progress — all 12 features have first-pass implementations)

## Frontend (built)
React 19 + Vite 8 + Tailwind v4 (v4 style: `@tailwindcss/vite` plugin + `@import "tailwindcss"` in index.css — NO tailwind.config.js). `npm run build` passes.
- `frontend/src/api.js` — fetch wrapper (VITE_API_BASE, default http://localhost:8000)
- Pages: `Dashboard.jsx` (project list + create), `ProjectDetail.jsx` (upload + search + gallery grouped by date/location + tabs to Compare/Claims/Report), `ComparePage.jsx` (dual selects + slider + metric cards), `Claims.jsx` (create claim w/ media multiselect; cards with big score, expandable itemized breakdown, contradiction trace), `MediaDetail.jsx` (media + full audit trail)
- Components: `DisclaimerBanner.jsx` (persistent), `RelevanceBadge.jsx` (green >75 / amber 40-75 / red <40), `UploadWidget.jsx` (device GPS attach, shows relevance + duplicate warning)
- Run: `cd frontend && npm run dev` (Vite on :5173)

## Run commands
- Backend: `.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000` (Windows venv path)
- Backend DEMO MODE (no credentials needed): `DEMO_MODE=1 .venv/Scripts/python -m uvicorn backend.main:app --port 8000`
- Tests: `.venv/Scripts/python -m pytest tests -q`
- Frontend: `cd frontend && npm run dev`

## Known issues
- `/api/media` list endpoint fetches up to 500 docs then groups in Python — fine for hackathon volume, would need aggregation/pagination at scale
- AI-dependent flows (relevance scoring, dual-AI claim analysis) return graceful fallbacks when `GROQ_API_KEY` is unset — no crash, scores null
- Cloudinary `eager` transformation availability for `thumbnail_url` can vary by plan; UI falls back to full URL
- Confidence formula weights are first-pass guesses (base 50, +15%×strength capped +40, −6/12/20 capped −50) — tune after demo dry-run

## Features not started
1. Project setup — CRUD (name, description, lat/lng + place, expected_activity_type)
2. Upload flow — project-scoped upload → Cloudinary, EXIF/GPS extraction, Firestore `media` record
3. Media organization view — per-project gallery auto-grouped by date + location, thumbnails, tags, relevance badges
4. Relevance scoring — Groq vision model (image or 1–3 video frames) → JSON {image_description, relevance_score 0–100, reasoning, location_match, content_match}; badge green >75 / amber 40–75 / red <40
5. AI tagging + semantic search — Cloudinary auto-tags on upload; search bar over tags + image_description
6. Before/after comparison — pick 2 media (same project, different dates), slider/side-by-side, change metric <2s
7. Deterministic evidence checks — phash duplicates (all projects), EXIF timestamp/GPS consistency across claim's linked media
8. Dual AI claim analysis — Supporting AI + Adversarial AI (different Groq models) in parallel via asyncio.gather; supporting signals strength 0–100, adversarial signals severity low/medium/high
9. Confidence scoring function — deterministic weighted 0–100 score + itemized breakdown
10. Claim dashboard UI — score, color green >80 / amber 60–80 / red <60, expandable signal breakdown, contradiction trace, disclaimer banner
11. Visual report generator — one-click per-project HTML (or PDF) export: gallery + before/after + claim scores, donor-clean
12. Audit trail — `audit_log` writes on every upload/tag/transformation/comparison with before/after state + timestamp; per-media history view

## AI verification (Sep 29, 2026 — LIVE credentials)
`.env` now has real Groq + Cloudinary + Firebase creds; backend runs LIVE (`demo_mode:false`, all config true). Verified end-to-end:
- **Groq model fix**: `llama-3.3-70b-versatile` was RETIRED from Groq (404). Key's available models: gpt-oss-120b/20b/safeguard-20b, qwen/qwen3.8-27b, allam-2-7b (+audio/guard). New roles: vision=qwen/qwen3.8-27b, supporting=openai/gpt-oss-120b, adversarial=openai/gpt-oss-20b (updated in code defaults, .env, .env.example)
- **Cloudinary fix**: free plan lacks Google Auto Tagging add-on — `categorization=google_tagging` raised hard RateLimited → `upload_media` now retries WITHOUT tagging on that error; router maps SDK errors to readable 502
- **Vision corruption root-caused (2 bugs)**: (1) ANY Cloudinary transform (q_auto thumbnail OR c_limit/w_* resize) re-encodes small images to palette-mode files the vision encoder reads as noise → pipeline now sends the ORIGINAL `cloudinary_url` (`_vision_url` in media.py, no transforms); (2) strict system message + temp 0.1 made qwen hallucinate "panel grids" → JSON contract moved into USER text, temp 0.7 (see relevance.py comment)
- **Verified good**: real-photo upload → faithful description, honest score 0 (no planting visible = correct conservative behavior); claim on terrain-matching photo → supporting +85 (grounded, cites description), 3 adversarial signals (low severity), confidence 44.8 matches hand-computed 50+12.75−18; phash dedup correctly flagged 3 duplicate uploads (−20 each → floor 0); Firebase reads/writes OK; 429 rate limits handled as graceful fallbacks
- NOTE: synthetic/flat-color test images can still score low — qwen honestly calls them "illustrations, not photographic evidence"; test with real photos

## Run status (last verified session)
- Backend: uvicorn on :8000 LIVE mode (credentials loaded, `demo_mode:false`)
- Frontend: Vite on :5173 — **live UI verified in browser against real Firestore**: Dashboard lists real project, ProjectDetail gallery shows 5 media with AI descriptions/relevance badges/duplicate flags, Claims tab renders score 44.8 card + score-0 card with contradiction trace, report page loads with all 5 Cloudinary images
- Restart both after any Freebuff restart (`netstat -ano | grep LISTENING` for real PIDs; nohup `$!` reports wrong PID on Windows)
- Demo mode (`DEMO_MODE=1`) still available as zero-credential fallback — seed + local media verified earlier
- Test data in Firestore: project "AI Test Planting" (py9bAij922FLD7E3VaQx) with 5 media + 2 claims is synthetic test junk — safe to delete via API before final demo

## Next steps
- USER: paste exact Supporting/Adversarial AI system prompts — replace the PLACEHOLDER strings at top of `backend/services/dual_ai.py` VERBATIM (note: prompts live in dual_ai.py, not claim_prompts.py)
- Cloudinary auto-tagging needs the paid Google Auto Tagging add-on — either upgrade plan or accept empty `cloudinary_tags` (search still works over AI descriptions)
- SECURITY: real Cloudinary credentials were previously pasted in `.env.example` (git-tracked, now removed) — rotate them in the Cloudinary console if they were live; `.env` itself is untracked and safe
- Optional hardening: video phash (currently images only), refresh-tags endpoint, PDF export, deployment
