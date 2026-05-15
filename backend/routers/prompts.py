from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Prompt
from schemas import PromptCreate, PromptOut, PromptUpdate

router = APIRouter()


@router.get("/", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db)):
    return db.query(Prompt).order_by(Prompt.created_at.asc()).all()


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt introuvable")
    return prompt


@router.post("/", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, db: Session = Depends(get_db)):
    if payload.is_default:
        db.query(Prompt).filter(Prompt.is_default.is_(True)).update({"is_default": False})
    prompt = Prompt(**payload.model_dump())
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, payload: PromptUpdate, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt introuvable")
    data = payload.model_dump(exclude_none=True)
    if data.get("is_default"):
        db.query(Prompt).filter(Prompt.id != prompt_id, Prompt.is_default.is_(True)).update({"is_default": False})
    for field, value in data.items():
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt introuvable")
    db.delete(prompt)
    db.commit()
