from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import Float, String, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Summary
from schemas import SearchResult, SummaryListItem, TagCount, ThemeStatusCounts

router = APIRouter()

SortKey = Literal["recent", "top", "densite", "niveau", "actionnable", "perennite"]
# pending = sans thème mais avec une suggestion Jev à valider ;
# unthemed = ni thème ni suggestion.
ThemeStatus = Literal["pending", "unthemed"]

PENDING_FILTER = (Summary.theme_id.is_(None), Summary.theme_suggestion_id.is_not(None))
_UNTHEMED_FILTER = (Summary.theme_id.is_(None), Summary.theme_suggestion_id.is_(None))

# Poids d'un like/dislike dans le score global (les notes Jev vont de 0 à 3).
_FEEDBACK_WEIGHT = 1.5


def _score(key: str):
    return cast(func.json_extract(Summary.scores, f"$.{key}"), Float)


def _sort_expression(sort: str):
    if sort == "top":
        return (
            _score("densite") + _score("actionnable") + _score("perennite")
            + func.coalesce(Summary.feedback, 0) * _FEEDBACK_WEIGHT
        )
    return _score(sort)


@router.get("/", response_model=SearchResult)
def search(
    q: str = "",
    theme_id: int | None = None,
    tag: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort: SortKey = "recent",
    status: ThemeStatus | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Summary).options(joinedload(Summary.theme))

    if status is not None:
        query = query.filter(*(PENDING_FILTER if status == "pending" else _UNTHEMED_FILTER))

    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Summary.title.ilike(term),
                Summary.summary_short.ilike(term),
                Summary.summary_long.ilike(term),
            )
        )

    if theme_id is not None:
        query = query.filter(Summary.theme_id == theme_id)

    if tag:
        query = query.filter(cast(Summary.tags, String).like(f'%"{tag}"%'))

    total = query.count()
    if sort == "recent":
        order = [Summary.created_at.desc()]
    else:
        # Les synthèses pas encore notées par Jev passent en fin de liste.
        expr = _sort_expression(sort)
        order = [expr.is_(None), expr.desc(), Summary.created_at.desc()]
    items = query.order_by(*order).offset(skip).limit(limit).all()

    return SearchResult(items=[SummaryListItem.model_validate(i) for i in items], total=total)


@router.get("/theme-status", response_model=ThemeStatusCounts)
def theme_status(db: Session = Depends(get_db)):
    return ThemeStatusCounts(
        pending=db.query(Summary).filter(*PENDING_FILTER).count(),
        unthemed=db.query(Summary).filter(*_UNTHEMED_FILTER).count(),
    )


@router.get("/tags", response_model=list[TagCount])
def tag_cloud(db: Session = Depends(get_db)):
    counts: dict[str, int] = {}
    for (tags,) in db.query(Summary.tags).all():
        for t in (tags or []):
            counts[t] = counts.get(t, 0) + 1
    return [
        TagCount(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
