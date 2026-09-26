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


class ResumeSessionLiveError(Exception):
    """Levee quand FreeLLM ne peut pas generer le resume d'une session live (UC-33)."""


class DigestFamilleError(Exception):
    """Levee quand FreeLLM ne peut pas generer le digest hebdomadaire du Radar familial (UC-36)."""


def _texte_ou_erreur(response, erreur_cls: type[Exception]) -> str:
    """`response.choices[0]` peut lever IndexError si FreeLLM renvoie une liste `choices`
    vide (routage "auto" qui echoue silencieusement plutot que de renvoyer une erreur
    HTTP) - non couvert par le `except OpenAIError` qui entoure uniquement l'appel HTTP
    lui-meme. Sans ce garde-fou, cette IndexError remontait non geree jusqu'au handler
    Starlette par defaut, qui renvoie une reponse SANS la forme {"error": {...}} du
    contrat - le frontend (messageErreur()) ne peut alors qu'afficher son message
    generique de secours, sans aucune trace exploitable cote serveur non plus."""
    if not response.choices:
        raise erreur_cls("Reponse FreeLLM sans contenu (aucun choix retourne).")
    return (response.choices[0].message.content or "").strip()


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

        texte = _texte_ou_erreur(response, DocumentScoringError)
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

        texte = _texte_ou_erreur(response, CorrectionError)
        correspondance = re.search(r"\d+(\.\d+)?", texte)
        if correspondance is None:
            raise CorrectionError(f"Reponse FreeLLM non interpretable comme un score : {texte!r}")

        return max(0.0, min(points_max, float(correspondance.group())))

    def corriger_copie_image(
        self, consigne_globale: str, points_max_total: float, image_bytes: bytes, content_type: str, strict: bool
    ) -> float:
        """UC-26.4/26.5 : correction holistique d'une copie entierement imagee/scannee -
        une seule note globale (pas de decoupage par question, contrairement a
        corriger_reponse), a partir du/des bareme(s) fournis par l'enseignant
        (bareme_reponse par question et/ou bareme_document du devoir, concatenes en
        amont par l'appelant dans consigne_globale)."""
        consigne_notation = (
            f"Attribue soit {points_max_total} (travail globalement correct et complet) soit 0, "
            "sans note intermediaire."
            if strict
            else f"Attribue une note entre 0 et {points_max_total}, avec credit partiel si le "
            "raisonnement est correct mais incomplet ou partiellement illisible."
        )
        prompt = (
            f"Bareme de correction attendu par l'enseignant : {consigne_globale}\n\n"
            f"{consigne_notation} Reponds uniquement avec la note obtenue, sans aucun autre texte."
        )
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        try:
            response = self._client.chat.completions.create(
                model="auto",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_b64}"}},
                        ],
                    }
                ],
            )
        except OpenAIError as exc:
            raise CorrectionError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, CorrectionError)
        correspondance = re.search(r"\d+(\.\d+)?", texte)
        if correspondance is None:
            raise CorrectionError(f"Reponse FreeLLM non interpretable comme une note : {texte!r}")

        return max(0.0, min(points_max_total, float(correspondance.group())))

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

        texte = _texte_ou_erreur(response, QuizGenerationError)
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

        texte = _texte_ou_erreur(response, ElProfessorError)
        if not texte:
            raise ElProfessorError("Reponse FreeLLM vide.")
        return texte

    def conseiller_tuteur(self, contexte_eleve: str | None, historique: list[dict], question: str) -> str:
        """UC-32 : El Professor cote tuteur - conseille un parent/tuteur sur son enfant
        (scolarite, comportement, orientation, tensions familiales). Persona distincte de
        conseiller_enseignant (parent, pas professionnel de l'education) mais meme
        garde-fou de securite applique cote routeur."""
        consigne = (
            "Tu es 'El Professor', un assistant qui conseille un tuteur/parent sur la "
            "scolarite, le comportement ou l'orientation de son enfant. Tu paries sur la "
            "bienveillance et le dialogue plutot que la sanction. Tu n'es ni un "
            "professionnel de sante mentale ni un juriste : pour toute situation grave ou "
            "potentiellement dangereuse (maltraitance, violence, detresse psychologique, "
            "urgence), tu recommandes explicitement et sans delai d'en parler a "
            "l'administration de l'etablissement ou aux autorites competentes - tu ne "
            "traites jamais seul ce genre de situation."
        )
        if contexte_eleve:
            consigne += f"\n\nContexte disponible sur l'enfant (vie scolaire) :\n{contexte_eleve}"

        messages = [{"role": "system", "content": consigne}]
        for tour in historique:
            role = "assistant" if tour["role"] == "assistant" else "user"
            messages.append({"role": role, "content": tour["contenu"]})
        messages.append({"role": "user", "content": question})

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise ElProfessorError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, ElProfessorError)
        if not texte:
            raise ElProfessorError("Reponse FreeLLM vide.")
        return texte

    def conseiller_enseignant(self, contexte_eleve: str | None, historique: list[dict], question: str) -> str:
        """UC-27 : El Professor cote enseignant - conseille sur des questions educatives,
        morales, professionnelles ou humaines concernant ses eleves ou sa pratique.
        Persona distincte de repondre_question_el_professor (cote eleve, ancre au contenu
        d'un cours) : ici, un coach pedagogique, pas un tuteur de matiere. Le garde-fou de
        securite (detection de signaux de danger -> escalade) est applique cote routeur
        (voir pedagogie/router.py::_detecter_signal_alerte), pas ici - le prompt le
        rappelle neanmoins pour renforcer la reponse elle-meme."""
        consigne = (
            "Tu es 'El Professor', un assistant qui conseille un enseignant sur des questions "
            "educatives, morales, professionnelles ou humaines concernant ses eleves ou sa "
            "propre pratique. Tu n'es ni un professionnel de sante mentale ni un juriste : pour "
            "toute situation grave ou potentiellement dangereuse (maltraitance, violence, "
            "detresse psychologique, urgence), tu recommandes explicitement et sans delai d'en "
            "parler a l'administration de l'etablissement ou aux autorites competentes - tu ne "
            "traites jamais seul ce genre de situation, meme si l'enseignant ne le demande pas."
        )
        if contexte_eleve:
            consigne += f"\n\nContexte disponible sur l'eleve concerne (vie scolaire) :\n{contexte_eleve}"

        messages = [{"role": "system", "content": consigne}]
        for tour in historique:
            role = "assistant" if tour["role"] == "assistant" else "user"
            messages.append({"role": role, "content": tour["contenu"]})
        messages.append({"role": "user", "content": question})

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise ElProfessorError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, ElProfessorError)
        if not texte:
            raise ElProfessorError("Reponse FreeLLM vide.")
        return texte


    def conseiller_famille(
        self, contexte_eleve: str | None, historique: list[dict], question: str, qui_parle: str
    ) -> str:
        """UC-37 : El Professor Famille - fil partage entre un tuteur et son enfant, les
        deux posant des questions dans le meme fil. Contrairement a conseiller_tuteur/
        conseiller_enseignant (un seul interlocuteur), l'historique melange des tours
        'tuteur' et 'eleve' : le prompt precise systematiquement `qui_parle` pour que la
        reponse s'adresse explicitement au bon interlocuteur plutot que de rester
        generique."""
        consigne = (
            "Tu es 'El Professor', un assistant qui conseille CONJOINTEMENT un tuteur/"
            "parent et son enfant dans un meme fil de discussion sur la scolarite, le "
            "comportement ou l'orientation de l'enfant. Chaque message precise qui parle "
            "('tuteur' ou 'eleve') : adresse-toi explicitement et nommement a cette "
            "personne dans ta reponse (par exemple 'Pour vous, [tuteur]...' ou "
            "'De ton cote, [eleve]...'), sans jamais ignorer l'autre partie presente dans "
            "la conversation. Tu n'es ni un professionnel de sante mentale ni un juriste : "
            "pour toute situation grave ou potentiellement dangereuse (maltraitance, "
            "violence, detresse psychologique, urgence), tu recommandes explicitement et "
            "sans delai d'en parler a l'administration de l'etablissement ou aux autorites "
            "competentes - tu ne traites jamais seul ce genre de situation."
        )
        if contexte_eleve:
            consigne += f"\n\nContexte disponible sur l'enfant (vie scolaire) :\n{contexte_eleve}"

        messages = [{"role": "system", "content": consigne}]
        for tour in historique:
            role = "assistant" if tour["role"] == "assistant" else "user"
            prefixe = "" if role == "assistant" else f"[{tour['role']}] "
            messages.append({"role": role, "content": f"{prefixe}{tour['contenu']}"})
        messages.append({"role": "user", "content": f"[{qui_parle}] {question}"})

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise ElProfessorError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, ElProfessorError)
        if not texte:
            raise ElProfessorError("Reponse FreeLLM vide.")
        return texte

    def generer_digest_famille(self, eleve_nom: str, sources: list[str]) -> str:
        """UC-36 : Radar familial - digest hebdomadaire narratif genere UNIQUEMENT a
        partir des faits deja factuellement etablis ailleurs sur la plateforme (vie
        scolaire, devoirs corriges, sessions live suivies, activite financiere si le
        Coffre-fort est actif), fournis ici sous forme de lignes de citation
        pre-formatees (voir radar_familial/service.py). UC-36.2 : le resume doit citer
        ces sources textuellement (dates, matieres) plutot que rester dans le vague, et
        ne jamais affirmer un fait absent de la liste fournie."""
        consigne = (
            f"Tu rediges pour un tuteur/parent un resume hebdomadaire narratif et "
            f"bienveillant de la semaine ecoulee de son enfant {eleve_nom}, en 5 phrases "
            "maximum. Tu ne disposes QUE des faits ci-dessous (chacun deja date et "
            "source) : tu dois t'appuyer explicitement dessus (cite la date et le sujet), "
            "et tu n'as strictement rien d'autre a ta disposition - n'invente et n'suppose "
            "jamais un fait qui n'y figure pas. Si la liste est courte, dis-le simplement "
            "plutot que de meubler."
        )
        faits = "\n".join(f"- {source}" for source in sources) if sources else "(aucun fait cette semaine)"
        messages = [
            {"role": "system", "content": consigne},
            {"role": "user", "content": f"Faits de la semaine :\n{faits}"},
        ]

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise DigestFamilleError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, DigestFamilleError)
        if not texte:
            raise DigestFamilleError("Reponse FreeLLM vide.")
        return texte

    def resumer_session_live(self, messages_chat: list[str], contenu_tableau: str) -> str:
        """UC-33.1 : observation asynchrone du tuteur - un resume texte factuel de ce qui
        s'est passe pendant une session live, genere UNIQUEMENT a partir du chat texte et
        du contenu final du tableau (jamais d'un flux video/audio, qui n'existe pas cote
        serveur - voir realtime.py, le WebRTC est un relais pair-a-pair non enregistre)."""
        consigne = (
            "Tu resumes pour un parent/tuteur ce qui s'est passe pendant une session de "
            "cours en direct, a partir uniquement du chat texte de la session et du contenu "
            "final du tableau ci-dessous. Reste factuel et concis (5 phrases maximum), cite "
            "les elements precis dont tu disposes (sujets abordes, questions posees), et "
            "n'invente jamais de detail que ces sources ne contiennent pas."
        )
        chat = "\n".join(messages_chat) if messages_chat else "(aucun message dans le chat)"
        contenu = (
            f"Messages du chat de la session :\n{chat}\n\n"
            f"Contenu final du tableau :\n{contenu_tableau or '(tableau vide)'}"
        )
        messages = [
            {"role": "system", "content": consigne},
            {"role": "user", "content": contenu},
        ]

        try:
            response = self._client.chat.completions.create(model="auto", messages=messages)
        except OpenAIError as exc:
            raise ResumeSessionLiveError("FreeLLM indisponible ou a refuse la requete.") from exc

        texte = _texte_ou_erreur(response, ResumeSessionLiveError)
        if not texte:
            raise ResumeSessionLiveError("Reponse FreeLLM vide.")
        return texte


def get_llm_client() -> FreeLLMClient:
    return FreeLLMClient()
