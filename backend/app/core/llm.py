import base64
import re

from openai import OpenAI, OpenAIError

from app.core.config import settings


class DocumentScoringError(Exception):
    """Levee quand FreeLLM ne peut pas noter un document (indisponibilite, reponse non
    interpretable comme un score - voir ADR-002 : pas de SLA, pas de modele frontier)."""


class FreeLLMClient:
    """Tous les appels LLM du projet passent par FreeLLM (ADR-002), jamais l'API Anthropic
    en direct. FreeLLM n'accepte que des images en vision : les PDF sont convertis en
    image avant l'appel (voir app/modules/recrutement/pdf.py)."""

    def __init__(self) -> None:
        self._client = OpenAI(base_url=settings.freellm_base_url, api_key=settings.freellm_api_key)

    def noter_document(self, image_bytes: bytes, content_type: str, critere: str) -> float:
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        prompt = (
            f"Tu evalues un document de candidature enseignant selon ce critere : {critere}. "
            "Reponds uniquement avec un nombre entier entre 0 et 100 representant la "
            "conformite du document a ce critere, sans aucun autre texte."
        )
        try:
            response = self._client.chat.completions.create(
                model="auto",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{content_type};base64,{image_b64}"},
                            },
                        ],
                    }
                ],
            )
        except OpenAIError as exc:
            raise DocumentScoringError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = (response.choices[0].message.content or "").strip()
        correspondance = re.search(r"\d+(\.\d+)?", texte)
        if correspondance is None:
            raise DocumentScoringError(f"Reponse FreeLLM non interpretable comme un score : {texte!r}")

        return max(0.0, min(100.0, float(correspondance.group())))


def get_llm_client() -> FreeLLMClient:
    return FreeLLMClient()
