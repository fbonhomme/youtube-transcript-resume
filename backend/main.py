from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import summaries, themes, search, prompts, stats

Base.metadata.create_all(bind=engine)

app = FastAPI(title="YouTube Transcript Summarizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(themes.router, prefix="/themes", tags=["themes"])
app.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/health")
def health():
    return {"status": "ok"}
