from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Summary
from schemas import StatsOut

router = APIRouter()


@router.get("/", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    row = db.query(
        func.count(Summary.id),
        func.coalesce(func.sum(Summary.cost_usd), 0.0),
        func.coalesce(func.sum(Summary.input_tokens), 0),
        func.coalesce(func.sum(Summary.output_tokens), 0),
        func.coalesce(func.sum(Summary.duration_read), 0),
    ).one()

    distinct_tags: set[str] = set()
    for (tags,) in db.query(Summary.tags).all():
        if tags:
            distinct_tags.update(tags)

    return StatsOut(
        total_summaries=row[0],
        total_cost_usd=float(row[1]),
        total_input_tokens=int(row[2]),
        total_output_tokens=int(row[3]),
        total_read_minutes=int(row[4]),
        total_tags=len(distinct_tags),
    )
