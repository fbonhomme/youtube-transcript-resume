from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Summary, Theme
from schemas import ThemeCreate, ThemeOut, ThemeUpdate

router = APIRouter()


def _theme_with_count(theme: Theme, db: Session) -> ThemeOut:
    count = db.query(func.count(Summary.id)).filter(Summary.theme_id == theme.id).scalar()
    out = ThemeOut.model_validate(theme)
    out.summary_count = count or 0
    return out


@router.get("/", response_model=list[ThemeOut])
def list_themes(db: Session = Depends(get_db)):
    themes = db.query(Theme).order_by(Theme.name).all()
    return [_theme_with_count(t, db) for t in themes]


@router.post("/", response_model=ThemeOut, status_code=201)
def create_theme(payload: ThemeCreate, db: Session = Depends(get_db)):
    if db.query(Theme).filter(Theme.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Un thème avec ce nom existe déjà")
    theme = Theme(**payload.model_dump())
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return _theme_with_count(theme, db)


@router.put("/{theme_id}", response_model=ThemeOut)
def update_theme(theme_id: int, payload: ThemeUpdate, db: Session = Depends(get_db)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Thème introuvable")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(theme, field, value)
    db.commit()
    db.refresh(theme)
    return _theme_with_count(theme, db)


@router.delete("/{theme_id}", status_code=204)
def delete_theme(theme_id: int, db: Session = Depends(get_db)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Thème introuvable")
    # Détacher les synthèses avant suppression
    db.query(Summary).filter(Summary.theme_id == theme_id).update({"theme_id": None})
    db.delete(theme)
    db.commit()
