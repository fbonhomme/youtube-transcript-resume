from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine
from routers import summaries, themes, search, prompts, stats, models, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="YouTube Transcript Summarizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def admin_validation_exception_handler(request: Request, exc: RequestValidationError):
    # Sur /admin-api/, Pydantic peut recopier la valeur envoyée (donc une clé
    # API) dans `input`/`ctx` d'une erreur 422 : on les retire pour ce préfixe.
    if not request.url.path.startswith("/admin-api/"):
        return await request_validation_exception_handler(request, exc)
    errors = [
        {k: v for k, v in error.items() if k not in ("input", "ctx")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


app.include_router(themes.router, prefix="/themes", tags=["themes"])
app.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(admin.router, prefix="/admin-api", tags=["admin"])


@app.get("/health")
def health():
    return {"status": "ok"}
