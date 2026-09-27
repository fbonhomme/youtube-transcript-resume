from fastapi import APIRouter

from schemas import ModelOut
from services.llm_models import DEFAULT_MODEL, MODELS, is_available

router = APIRouter()


@router.get("/", response_model=list[ModelOut])
def list_models():
    return [
        ModelOut(
            id=m.id,
            label=m.label,
            provider=m.provider,
            input_price=m.input_price,
            output_price=m.output_price,
            available=is_available(m),
            is_default=m.id == DEFAULT_MODEL,
        )
        for m in MODELS
    ]
