"""Classement et notation des synthèses via Jev (typesafe-ai/jev) sur Vercel AI Gateway.

Jev ne génère pas de texte : il répond à des questions typées (choice / score)
sur un état partagé, toutes évaluées en parallèle dans une seule requête.
"""
import httpx

from config import settings

EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
MODEL = "typesafe-ai/jev"

# Au-dessus : thème appliqué d'office. Entre les deux : simple suggestion.
AUTO_APPLY_THRESHOLD = 0.8
SUGGEST_THRESHOLD = 0.5

_NO_THEME = "aucun"

# Chaque critère est noté de 0 (premier niveau) à 3 (dernier niveau) ; Jev
# renvoie la moyenne pondérée par les probabilités, donc un float.
SCORE_CRITERIA: dict[str, tuple[str, list[str]]] = {
    "densite": (
        "Quelle est la densité d'information de la vidéo ?",
        [
            "Beaucoup de remplissage, très peu d'idées concrètes",
            "Quelques idées utiles noyées dans du contenu secondaire",
            "Riche : la plupart du contenu apporte de l'information",
            "Très dense : chaque minute apporte des idées ou faits nouveaux",
        ],
    ),
    "niveau": (
        "Quel niveau de connaissances préalables la vidéo suppose-t-elle ?",
        [
            "Grand public, aucune connaissance requise",
            "Intermédiaire, notions de base du domaine requises",
            "Avancé, bonne pratique du domaine requise",
            "Expert, destiné aux spécialistes du domaine",
        ],
    ),
    "actionnable": (
        "Dans quelle mesure peut-on appliquer directement le contenu ?",
        [
            "Purement informatif ou divertissant, rien à appliquer",
            "Quelques conseils généraux",
            "Plusieurs conseils concrets et applicables",
            "Démarche pas-à-pas directement applicable",
        ],
    ),
    "perennite": (
        "Combien de temps le contenu restera-t-il pertinent ?",
        [
            "Actualité éphémère, obsolète en quelques semaines",
            "Pertinent quelques mois",
            "Pertinent environ un an ou plus",
            "Intemporel : principes et concepts durables",
        ],
    ),
}


def is_enabled() -> bool:
    return bool(settings.ai_gateway_api_key)


async def evaluate(state: str, questions: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            EVALUATE_URL,
            headers={"Authorization": f"Bearer {settings.ai_gateway_api_key}"},
            json={"model": MODEL, "state": state, "questions": questions},
        )
        resp.raise_for_status()
    return resp.json()["answers"]


def build_state(title: str, summary_short: str, key_points: list[str], tags: list[str]) -> str:
    points = "\n".join(f"- {p}" for p in key_points)
    return (
        f"Titre de la vidéo : {title}\n\n"
        f"Résumé : {summary_short}\n\n"
        f"Points clés :\n{points}\n\n"
        f"Tags : {', '.join(tags)}"
    )


def build_questions(themes: list) -> dict:
    questions: dict = {
        key: {"type": "score", "instructions": instructions, "criteria": levels}
        for key, (instructions, levels) in SCORE_CRITERIA.items()
    }
    if themes:
        criteria = {
            f"t{t.id}": f"{t.name} — {t.description}" if t.description else t.name
            for t in themes
        }
        criteria[_NO_THEME] = "Aucun des thèmes ci-dessus ne correspond au sujet de la vidéo"
        questions["theme"] = {
            "type": "choice",
            "instructions": "Dans quel thème de la bibliothèque ranger cette vidéo ?",
            "criteria": criteria,
        }
    return questions


def parse_answers(answers: dict) -> dict:
    scores = {
        key: round(float(answers[key]["score"]), 2)
        for key in SCORE_CRITERIA
        if key in answers
    }
    theme_id = None
    confidence = None
    theme = answers.get("theme")
    if theme and theme.get("choice") and theme["choice"] != _NO_THEME:
        theme_id = int(theme["choice"][1:])
        confidence = float(theme.get("probabilities", {}).get(theme["choice"], 0.0))
    return {"scores": scores, "theme_id": theme_id, "theme_confidence": confidence}


async def analyze_summary(summary, themes: list) -> dict:
    state = build_state(summary.title, summary.summary_short, summary.key_points or [], summary.tags or [])
    answers = await evaluate(state, build_questions(themes))
    return parse_answers(answers)


def apply_analysis(summary, analysis: dict) -> None:
    """Enregistre les notes ; ne touche jamais à un thème déjà choisi."""
    summary.scores = analysis["scores"]
    if summary.theme_id is not None:
        return
    theme_id = analysis["theme_id"]
    confidence = analysis["theme_confidence"]
    summary.theme_suggestion_id = None
    summary.theme_confidence = None
    if theme_id is None or confidence is None or confidence < SUGGEST_THRESHOLD:
        return
    summary.theme_confidence = round(confidence, 3)
    if confidence >= AUTO_APPLY_THRESHOLD:
        summary.theme_id = theme_id
    else:
        summary.theme_suggestion_id = theme_id
