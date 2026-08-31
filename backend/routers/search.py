from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Summary
from schemas import SearchResult, SummaryListItem, TagCount

router = APIRouter()


@router.get("/", response_model=SearchResult)
def search(
    q: str = "",
    theme_id: int | None = None,
    tag: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Summary).options(joinedload(Summary.theme))

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
    items = query.order_by(Summary.created_at.desc()).offset(skip).limit(limit).all()

    return SearchResult(items=[SummaryListItem.model_validate(i) for i in items], total=total)


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
