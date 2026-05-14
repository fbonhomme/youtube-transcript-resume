from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Summary
from schemas import SearchResult, SummaryListItem

router = APIRouter()


@router.get("/", response_model=SearchResult)
def search(
    q: str = "",
    theme_id: int | None = None,
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

    total = query.count()
    items = query.order_by(Summary.created_at.desc()).offset(skip).limit(limit).all()

    return SearchResult(items=[SummaryListItem.model_validate(i) for i in items], total=total)
