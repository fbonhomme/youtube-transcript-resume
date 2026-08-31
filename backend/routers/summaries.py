from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Prompt, Summary, Theme
from schemas import (
    ImportPreviewItem,
    ImportPreviewResult,
    SummarizeRequest,
    SummaryListItem,
    SummaryOut,
    SummaryUpdate,
)
from services.transcript import extract_video_id, fetch_title, fetch_transcript
from services.summarizer import generate_summary

router = APIRouter()


@router.post("/", response_model=SummaryOut, status_code=201)
async def summarize(payload: SummarizeRequest, db: Session = Depends(get_db)):
    if payload.theme_id and not db.get(Theme, payload.theme_id):
        raise HTTPException(status_code=404, detail="Thème introuvable")

    prompt = None
    if payload.prompt_id:
        prompt = db.get(Prompt, payload.prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt introuvable")
    else:
        prompt = db.query(Prompt).filter(Prompt.is_default.is_(True)).first()

    try:
        transcript_data = await fetch_transcript(payload.url)
    except ValueError as exc:
        # transcript désactivé / introuvable / URL invalide : erreur
        # attendue et actionnable côté client, pas un 500 opaque.
        raise HTTPException(status_code=422, detail=str(exc))

    existing_tags = sorted({tag for (tags,) in db.query(Summary.tags).all() for tag in (tags or [])})
    result, usage = await generate_summary(
        transcript=transcript_data["transcript"],
        title=transcript_data["title"],
        language=payload.language,
        system_prompt=prompt.system_prompt if prompt else None,
        existing_tags=existing_tags,
    )
    tags = list(dict.fromkeys([*payload.tags, *result["tags"]]))

    summary = Summary(
        title=transcript_data["title"],
        youtube_url=payload.url,
        youtube_id=transcript_data["video_id"],
        language=payload.language,
        transcript=transcript_data["transcript"],
        summary_short=result["summary_short"],
        summary_long=result["summary_long"],
        key_points=result["key_points"],
        sections=result["sections"],
        tags=tags,
        duration_read=result["duration_read"],
        theme_id=payload.theme_id,
        prompt_id=prompt.id if prompt else None,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cost_usd=usage["cost_usd"],
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return db.query(Summary).options(joinedload(Summary.theme)).filter(Summary.id == summary.id).first()


@router.get("/", response_model=list[SummaryListItem])
def list_summaries(
    theme_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Summary).options(joinedload(Summary.theme))
    if theme_id is not None:
        q = q.filter(Summary.theme_id == theme_id)
    return q.order_by(Summary.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/import/preview", response_model=ImportPreviewResult)
async def import_preview(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = (await file.read()).decode("utf-8", errors="ignore")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    existing = {s.youtube_id: s.title for s in db.query(Summary.youtube_id, Summary.title).all()}

    items: list[ImportPreviewItem] = []
    seen: set[str] = set()
    for url in lines:
        try:
            video_id = extract_video_id(url)
        except ValueError:
            items.append(ImportPreviewItem(url=url, error="URL YouTube invalide"))
            continue
        if video_id in seen:
            continue
        seen.add(video_id)

        already_imported = video_id in existing
        title = existing[video_id] if already_imported else await fetch_title(url, video_id)
        items.append(ImportPreviewItem(
            url=url,
            video_id=video_id,
            title=title,
            already_imported=already_imported,
        ))

    return ImportPreviewResult(items=items)


@router.get("/export")
def export_summaries(theme_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Summary)
    if theme_id is not None:
        q = q.filter(Summary.theme_id == theme_id)
    urls = [s.youtube_url for s in q.order_by(Summary.created_at.desc()).all()]
    content = "\n".join(urls) + ("\n" if urls else "")
    return PlainTextResponse(
        content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=youtube_urls.txt"},
    )


@router.get("/{summary_id}", response_model=SummaryOut)
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    summary = (
        db.query(Summary)
        .options(joinedload(Summary.theme))
        .filter(Summary.id == summary_id)
        .first()
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    return summary


@router.patch("/{summary_id}", response_model=SummaryOut)
def update_summary(summary_id: int, payload: SummaryUpdate, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    if payload.theme_id is not None and not db.get(Theme, payload.theme_id):
        raise HTTPException(status_code=404, detail="Thème introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(summary, field, value)
    db.commit()
    db.refresh(summary)
    return db.query(Summary).options(joinedload(Summary.theme)).filter(Summary.id == summary_id).first()


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    db.delete(summary)
    db.commit()
