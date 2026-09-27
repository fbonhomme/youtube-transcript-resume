import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Prompt, Summary, Theme
from schemas import (
    AnalyzeReport,
    ImportPreviewItem,
    ImportPreviewResult,
    SummarizeRequest,
    SummaryListItem,
    SummaryOut,
    SummaryUpdate,
)
from services.transcript import extract_video_id, fetch_title, fetch_transcript
from services import evaluator
from services.llm_models import DEFAULT_MODEL, get_model, is_available
from services.summarizer import SummaryGenerationError, generate_summary

logger = logging.getLogger(__name__)

router = APIRouter()

# Nombre d'appels Jev simultanés lors d'une ré-analyse de la bibliothèque.
_ANALYZE_CONCURRENCY = 5


def _load_summary(db: Session, summary_id: int) -> Summary:
    return db.query(Summary).options(joinedload(Summary.theme)).filter(Summary.id == summary_id).first()


@router.post("/", response_model=SummaryOut, status_code=201)
async def summarize(payload: SummarizeRequest, db: Session = Depends(get_db)):
    llm = get_model(payload.model or DEFAULT_MODEL)
    if llm is None:
        raise HTTPException(status_code=422, detail=f"Modèle inconnu : {payload.model}")
    if not is_available(llm):
        raise HTTPException(
            status_code=422,
            detail=f"Modèle indisponible : clé API manquante pour {llm.label}",
        )

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
    try:
        result, usage = await generate_summary(
            transcript=transcript_data["transcript"],
            title=transcript_data["title"],
            language=payload.language,
            system_prompt=prompt.system_prompt if prompt else None,
            existing_tags=existing_tags,
            model=llm.id,
        )
    except SummaryGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
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
        model=llm.id,
    )
    if evaluator.is_enabled():
        # Jev est un bonus : une panne ne doit jamais faire perdre la synthèse.
        try:
            analysis = await evaluator.analyze_summary(summary, db.query(Theme).all())
            evaluator.apply_analysis(summary, analysis)
        except Exception:
            logger.warning("Analyse Jev échouée pour %s", payload.url, exc_info=True)
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return _load_summary(db, summary.id)


def _require_jev() -> None:
    if not evaluator.is_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Jev non configuré : renseignez une clé OpenRouter ou Vercel AI Gateway "
                "dans l'Administration (ou le fichier .env)"
            ),
        )


@router.post("/analyze", response_model=AnalyzeReport)
async def analyze_library(db: Session = Depends(get_db)):
    """Ré-analyse toute la bibliothèque : notes recalculées, thème proposé aux synthèses sans thème."""
    _require_jev()
    themes = db.query(Theme).all()
    summaries = db.query(Summary).all()
    semaphore = asyncio.Semaphore(_ANALYZE_CONCURRENCY)

    async def _analyze(summary: Summary):
        async with semaphore:
            try:
                return await evaluator.analyze_summary(summary, themes)
            except Exception:
                logger.warning("Analyse Jev échouée pour la synthèse %s", summary.id, exc_info=True)
                return None

    analyses = await asyncio.gather(*(_analyze(s) for s in summaries))

    report = AnalyzeReport(analyzed=0, auto_classified=0, suggested=0, failed=0)
    for summary, analysis in zip(summaries, analyses):
        if analysis is None:
            report.failed += 1
            continue
        had_theme = summary.theme_id is not None
        evaluator.apply_analysis(summary, analysis)
        report.analyzed += 1
        if not had_theme and summary.theme_id is not None:
            report.auto_classified += 1
        elif summary.theme_suggestion_id is not None:
            report.suggested += 1
    db.commit()
    return report


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


@router.post("/{summary_id}/analyze", response_model=SummaryOut)
async def analyze_one(summary_id: int, db: Session = Depends(get_db)):
    _require_jev()
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    try:
        analysis = await evaluator.analyze_summary(summary, db.query(Theme).all())
    except Exception as exc:
        logger.warning("Analyse Jev échouée pour la synthèse %s", summary_id, exc_info=True)
        raise HTTPException(status_code=502, detail="Échec de l'analyse Jev") from exc
    evaluator.apply_analysis(summary, analysis)
    db.commit()
    return _load_summary(db, summary_id)


@router.patch("/{summary_id}", response_model=SummaryOut)
def update_summary(summary_id: int, payload: SummaryUpdate, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    if payload.theme_id is not None and not db.get(Theme, payload.theme_id):
        raise HTTPException(status_code=404, detail="Thème introuvable")
    changes = payload.model_dump(exclude_unset=True)
    if "theme_id" in changes:
        # Choix manuel du thème : la suggestion Jev n'a plus lieu d'être.
        changes["theme_suggestion_id"] = None
        changes["theme_confidence"] = None
    for field, value in changes.items():
        setattr(summary, field, value)
    db.commit()
    db.refresh(summary)
    return _load_summary(db, summary_id)


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Synthèse introuvable")
    db.delete(summary)
    db.commit()
