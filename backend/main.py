"""Evidence Graph — FastAPI entrypoint."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import get_settings
from backend.routers import audit, claims, compare, media, projects, report, search

app = FastAPI(
    title="Evidence Graph API",
    description=(
        "Media intelligence for impact evidence. All outputs are evidence "
        "assessments, not proof."
    ),
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.demo_mode:
    # Serve locally-stored demo media (stands in for Cloudinary URLs)
    from backend.core.demo_media import DEMO_DIR, ensure_dirs

    ensure_dirs()
    app.mount("/demo-files", StaticFiles(directory=str(DEMO_DIR / "uploads")), name="demo-files")

    @app.on_event("startup")
    def _seed_demo_data() -> None:
        """Seed sample data so the demo is clickable immediately after restart."""
        from backend.core.seed_demo import seed_if_empty

        seeded = seed_if_empty()
        print(f"[demo-mode] {'seeded sample project + media + claim' if seeded else 'existing demo data kept'}")

app.include_router(projects.router)
app.include_router(media.router)
app.include_router(search.router)
app.include_router(compare.router)
app.include_router(claims.router)
app.include_router(audit.router)
app.include_router(report.router)


@app.exception_handler(RuntimeError)
async def unconfigured_service_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Surface missing-credential errors as 503 with a readable message."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "config": {
            "groq": settings.groq_configured,
            "cloudinary": settings.cloudinary_configured,
            "firebase": settings.firebase_configured,
        },
        "disclaimer": "This is an evidence assessment, not proof of impact.",
    }
