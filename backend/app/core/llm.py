import base64
import json
import re

from openai import OpenAI, OpenAIError

from app.core.config import settings


class DocumentScoringError(Exception):
    """Levee quand FreeLLM ne peut pas noter un document (indisponibilite, reponse non
    interpretable comme un score - voir ADR-002 : pas de SLA, pas de modele frontier)."""


class CorrectionError(Exception):
    """Levee quand FreeLLM ne peut pas corriger une reponse de formulaire d'evaluation."""


class QuizGenerationError(Exception):
    """Levee quand FreeLLM ne peut pas generer un quiz exploitable a partir d'un cours."""


class ElProfessorError(Exception):
    """Levee quand FreeLLM ne peut pas repondre a une question de l'assistant El Professor."""


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

    def corriger_reponse(
        self, enonce: str, bareme_reponse: str, points_max: float, reponse_eleve: str, strict: bool
    ) -> float:
        """UC-08 : les evaluations sont corrigees par le LLM selon le bareme fourni par
        l'enseignant. bareme='rigide' => tout ou rien (points_max ou 0) ; 'flexible' =>
        credit partiel selon la qualite du raisonnement."""
        consigne_notation = (
            f"Attribue soit {points_max} (reponse correcte) soit 0 (reponse incorrecte), rien entre les deux."
            if strict
            else f"Attribue un score entre 0 et {points_max}, avec credit partiel si le raisonnement est "
            "correct mais incomplet."
        )
        prompt = (
            f"Question posee a un eleve : {enonce}\n"
            f"Bareme de correction attendu par l'enseignant : {bareme_reponse}\n"
            f"Reponse de l'eleve : {reponse_eleve}\n\n"
            f"{consigne_notation} Reponds uniquement avec le nombre de points obtenus, sans aucun autre texte."
        )
        try:
            response = self._client.chat.completions.create(
                model="auto", messages=[{"role": "user", "content": prompt}]
            )
        except OpenAIError as exc:
            raise CorrectionError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = (response.choices[0].message.content or "").strip()
        correspondance = re.search(r"\d+(\.\d+)?", texte)
        if correspondance is None:
            raise CorrectionError(f"Reponse FreeLLM non interpretable comme un score : {texte!r}")

        return max(0.0, min(points_max, float(correspondance.group())))

    def generer_quiz(self, contenu_cours: str, nombre_questions: int = 5) -> list[dict]:
        """UC-07 : le quiz est genere par le LLM a partir du contenu du cours. Format
        impose : QCM a 4 choix, une seule bonne reponse par question."""
        prompt = (
            f"A partir du contenu de cours suivant, genere exactement {nombre_questions} questions a choix "
            "multiple (4 choix chacune, une seule bonne reponse) pour verifier la comprehension d'un eleve.\n\n"
            f"Contenu du cours :\n{contenu_cours}\n\n"
            "Reponds UNIQUEMENT avec un tableau JSON valide, sans texte autour, au format exact : "
            '[{"enonce": "...", "choix": ["...", "...", "...", "..."], "reponse_correcte_index": 0}, ...]'
        )
        try:
            response = self._client.chat.completions.create(
                model="auto", messages=[{"role": "user", "content": prompt}]
            )
        except OpenAIError as exc:
            raise QuizGenerationError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = (response.choices[0].message.content or "").strip()
        debut, fin = texte.find("["), texte.rfind("]")
        if debut == -1 or fin == -1:
            raise QuizGenerationError(f"Reponse FreeLLM non interpretable comme un quiz JSON : {texte!r}")
        try:
            questions = json.loads(texte[debut : fin + 1])
        except json.JSONDecodeError as exc:
            raise QuizGenerationError(f"JSON de quiz invalide : {texte!r}") from exc

        for question in questions:
            if (
                not isinstance(question.get("enonce"), str)
                or not isinstance(question.get("choix"), list)
                or len(question["choix"]) < 2
                or not isinstance(question.get("reponse_correcte_index"), int)
            ):
                raise QuizGenerationError(f"Question de quiz mal formee : {question!r}")

        if not questions:
            raise QuizGenerationError("FreeLLM a renvoye un quiz vide.")

        return questions

    def repondre_question_el_professor(
        self, contenu_cours: str, historique: list[dict], question: str
    ) -> str:
        """UC-14 : assistant pedagogique conversationnel, portee V1 volontairement
        etroite (delegue) - repond uniquement sur le contenu du cours, ne donne jamais
        la reponse d'un devoir en cours (garde-fou de prompt, cf. UC-08)."""
        consigne = (
            "Tu es 'El Professor', un assistant pedagogique qui aide un eleve a comprendre le "
            "contenu de son cours. Reponds uniquement a partir du contenu de cours fourni "
            "ci-dessous. Si la question sort du sujet du cours, dis-le poliment plutot que "
            "d'inventer une reponse. Tu ne donnes jamais la reponse toute faite d'un devoir ou "
            "d'un exercice note : tu expliques la notion pour que l'eleve trouve lui-meme.\n\n"
            f"Contenu du cours :\n{contenu_cours}"
        )
        messages = [{"role": "system", "content": consigne}]
        for tour in historique:
            role = "assistant" if tour["role"] == "assistant" else "user"
            messages.append({"role": role, "content": tour["contenu"]})
        messages.append({"role": "user", "content": question})

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise ElProfessorError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = (response.choices[0].message.content or "").strip()
        if not texte:
            raise ElProfessorError("Reponse FreeLLM vide.")
        return texte


def get_llm_client() -> FreeLLMClient:
    return FreeLLMClient()
