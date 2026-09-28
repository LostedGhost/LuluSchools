import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormatCours(str, enum.Enum):
    TEXTE = "texte"
    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"  # UC-15 (Phase 3) : meme circuit qu'un cours audio/pdf, taille/duree limitees a l'upload


class Cours(Base):
    __tablename__ = "cours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    chapitre: Mapped[str] = mapped_column(String(200))
    format: Mapped[FormatCours] = mapped_column(Enum(FormatCours))
    contenu_texte: Mapped[str | None] = mapped_column(Text, nullable=True)
    lulufiles_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Texte extrait d'un cours PDF (a la publication, ou a la premiere demande pour les cours
    # plus anciens) : donne a El Professor et a la generation de quiz le contenu reel du
    # document, que contenu_texte laisse vide pour ce format.
    texte_extrait: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lot 7.3 (handicap auditif) : transcription obligatoire pour publier un cours audio ou
    # video, et sous-titres WebVTT facultatifs (texte court, garde en base pour etre servi
    # et mis en cache hors ligne sans passer par LuluFiles). La transcription nourrit aussi
    # El Professor et la generation de quiz, jusque-la aveugles sur ces formats.
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    sous_titres_vtt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # UC-37/53 (lot admin ministeriel) : masquage non destructif d'un contenu signale, meme
    # pattern que Message.masque_par en messagerie (Phase 2/3) - jamais une suppression.
    masque_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    masque_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def a_des_sous_titres(self) -> bool:
        return bool(self.sous_titres_vtt)


class Quiz(Base):
    """UC-07 : seuil de reussite configurable (defaut 80%), tentatives illimitees. Les
    questions sont generees par le LLM (FreeLLM) a partir du contenu texte du cours,
    format QCM impose (voir app.core.llm.FreeLLMClient.generer_quiz)."""

    __tablename__ = "quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    cours_id: Mapped[str] = mapped_column(ForeignKey("cours.id"), index=True)
    seuil_reussite: Mapped[float] = mapped_column(Float, default=80.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    questions: Mapped[list["QuestionQuiz"]] = relationship(back_populates="quiz")


class QuestionQuiz(Base):
    __tablename__ = "questions_quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quiz.id"), index=True)
    ordre: Mapped[int] = mapped_column(Integer)
    enonce: Mapped[str] = mapped_column(Text)
    choix: Mapped[list] = mapped_column(JSON)
    reponse_correcte_index: Mapped[int] = mapped_column(Integer)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")


class TentativeQuiz(Base):
    __tablename__ = "tentatives_quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quiz.id"), index=True)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    reponses: Mapped[list] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    reussie: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RoleMessageElProfessor(str, enum.Enum):
    ELEVE = "eleve"
    ASSISTANT = "assistant"


class SessionElProfessor(Base):
    """UC-14 : une session par (eleve, cours) - upsert, reutilisee a chaque nouvelle
    question pour garder l'historique de continuite pedagogique (delegue). Sans cours
    (cours_id NULL) : conversation d'aide generale, l'eleve peut en ouvrir plusieurs
    (l'unicite ne porte que sur les couples ou cours_id est renseigne)."""

    __tablename__ = "sessions_el_professor"
    __table_args__ = (UniqueConstraint("eleve_utilisateur_id", "cours_id", name="uq_session_el_professor"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    cours_id: Mapped[str | None] = mapped_column(ForeignKey("cours.id"), nullable=True, index=True)
    sujet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["MessageElProfessor"]] = relationship(
        back_populates="session", order_by="MessageElProfessor.created_at"
    )
    cours: Mapped["Cours | None"] = relationship()

    @property
    def cours_titre(self) -> str | None:
        return self.cours.titre if self.cours is not None else None


class MessageElProfessor(Base):
    __tablename__ = "messages_el_professor"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_el_professor.id"), index=True)
    role: Mapped[RoleMessageElProfessor] = mapped_column(Enum(RoleMessageElProfessor))
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Piece jointe de la question (image ou PDF). L'image n'est jamais conservee
    # (minimisation, Art. 383 du Code du numerique) : seuls son nom et son type restent ;
    # d'un PDF, seul le texte extrait est garde, pour que la suite de la conversation
    # puisse encore s'y referer.
    piece_jointe_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    piece_jointe_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    piece_jointe_texte: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionElProfessor] = relationship(back_populates="messages")


class RoleMessageElProfessorEnseignant(str, enum.Enum):
    ENSEIGNANT = "enseignant"
    ASSISTANT = "assistant"


class SessionElProfessorEnseignant(Base):
    """UC-27 : El Professor cote enseignant - conseil educatif/moral/professionnel sur un
    eleve ou une question generale de pratique. Contrairement a SessionElProfessor (cote
    eleve, upsert unique par cours), un enseignant peut ouvrir plusieurs sessions
    distinctes (un fil par sujet/eleve) - c'est un historique de conversations, pas un
    fil de continuite pedagogique unique."""

    __tablename__ = "sessions_el_professor_enseignant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True, index=True)
    sujet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["MessageElProfessorEnseignant"]] = relationship(
        back_populates="session", order_by="MessageElProfessorEnseignant.created_at"
    )


class MessageElProfessorEnseignant(Base):
    __tablename__ = "messages_el_professor_enseignant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_el_professor_enseignant.id"), index=True)
    role: Mapped[RoleMessageElProfessorEnseignant] = mapped_column(Enum(RoleMessageElProfessorEnseignant))
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Piece jointe de la question (image ou PDF). L'image n'est jamais conservee
    # (minimisation, Art. 383 du Code du numerique) : seuls son nom et son type restent ;
    # d'un PDF, seul le texte extrait est garde, pour que la suite de la conversation
    # puisse encore s'y referer.
    piece_jointe_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    piece_jointe_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    piece_jointe_texte: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionElProfessorEnseignant] = relationship(back_populates="messages")


class RoleMessageElProfessorTuteur(str, enum.Enum):
    TUTEUR = "tuteur"
    ASSISTANT = "assistant"


class SessionElProfessorTuteur(Base):
    """UC-32 : El Professor cote tuteur - conseil sur SON enfant (contrairement au fil
    enseignant, eleve_utilisateur_id est toujours requis : un tuteur ne consulte jamais
    "en general", toujours a propos d'un enfant precis). Meme logique de fils multiples
    que SessionElProfessorEnseignant (pas d'upsert unique)."""

    __tablename__ = "sessions_el_professor_tuteur"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    sujet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["MessageElProfessorTuteur"]] = relationship(
        back_populates="session", order_by="MessageElProfessorTuteur.created_at"
    )


class MessageElProfessorTuteur(Base):
    __tablename__ = "messages_el_professor_tuteur"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_el_professor_tuteur.id"), index=True)
    role: Mapped[RoleMessageElProfessorTuteur] = mapped_column(Enum(RoleMessageElProfessorTuteur))
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Piece jointe de la question (image ou PDF). L'image n'est jamais conservee
    # (minimisation, Art. 383 du Code du numerique) : seuls son nom et son type restent ;
    # d'un PDF, seul le texte extrait est garde, pour que la suite de la conversation
    # puisse encore s'y referer.
    piece_jointe_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    piece_jointe_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    piece_jointe_texte: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionElProfessorTuteur] = relationship(back_populates="messages")


class OrigineAlerteElProfessor(str, enum.Enum):
    ENSEIGNANT = "enseignant"
    TUTEUR = "tuteur"
    FAMILLE = "famille"
    # Conversation d'un eleve avec El Professor : comme FAMILLE, jamais montree au tuteur
    # (il peut etre la source du danger), uniquement a l'administration.
    ELEVE = "eleve"


class AlerteElProfessor(Base):
    """UC-27.3/UC-32.2 : garde-fou de securite - quand une conversation (cote enseignant
    OU cote tuteur, voir `origine`) contient un signal de danger (voir
    pedagogie/router.py::_detecter_signal_alerte), El Professor ne traite jamais seul :
    une alerte est preparee ici pour l'administration, en plus d'une recommandation
    explicite d'escalade dans la reponse elle-meme. `session_id` n'est PAS une vraie
    ForeignKey (reference soit sessions_el_professor_enseignant soit
    sessions_el_professor_tuteur selon `origine` - meme choix que
    DesignationControleur.evenement_id) : verification applicative uniquement.
    `eleve_utilisateur_id` est denormalise (redondant avec la session referencee) pour
    permettre une requete directe "les alertes concernant MON enfant" cote tuteur, sans
    jointure polymorphe. etablissement_id reste NULL si aucun eleve precis n'est
    concerne (question generale cote enseignant), auquel cas seul l'audit interne (pas
    d'ecran admin/tuteur) la conserve."""

    __tablename__ = "alertes_el_professor"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    origine: Mapped[OrigineAlerteElProfessor] = mapped_column(
        Enum(OrigineAlerteElProfessor), default=OrigineAlerteElProfessor.ENSEIGNANT
    )
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    etablissement_id: Mapped[str | None] = mapped_column(ForeignKey("etablissements.id"), nullable=True, index=True)
    eleve_utilisateur_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True, index=True)
    motif: Mapped[str] = mapped_column(Text)
    traite: Mapped[bool] = mapped_column(Boolean, default=False)
    traite_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# --- UC-37 : El Professor Famille (fil partage tuteur + enfant) ---


class RoleMessageElProfessorFamille(str, enum.Enum):
    TUTEUR = "tuteur"
    ELEVE = "eleve"
    ASSISTANT = "assistant"


class SessionElProfessorFamille(Base):
    """UC-37 : fil El Professor partage entre un tuteur et son enfant, contrairement aux
    fils strictement individuels SessionElProfessorTuteur/SessionElProfessor - les deux
    posent des questions dans le meme fil, l'IA s'adresse explicitement a l'un ou
    l'autre (voir role sur MessageElProfessorFamille). Toujours cree par le tuteur (qui
    "invite" son enfant) ; `rejointe_le` reste NULL tant que l'enfant n'a pas
    explicitement rejoint (voir router.py::rejoindre_session_el_professor_famille) -
    aucun message ne peut etre poste avant, ni par l'un ni par l'autre (R3 : jamais l'IA
    ne bascule seule un fil individuel existant vers le mode famille, la co-initiation
    est toujours explicite des deux cotes)."""

    __tablename__ = "sessions_el_professor_famille"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    sujet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rejointe_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["MessageElProfessorFamille"]] = relationship(
        back_populates="session", order_by="MessageElProfessorFamille.created_at"
    )


class MessageElProfessorFamille(Base):
    __tablename__ = "messages_el_professor_famille"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_el_professor_famille.id"), index=True)
    role: Mapped[RoleMessageElProfessorFamille] = mapped_column(Enum(RoleMessageElProfessorFamille))
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Piece jointe de la question (image ou PDF). L'image n'est jamais conservee
    # (minimisation, Art. 383 du Code du numerique) : seuls son nom et son type restent ;
    # d'un PDF, seul le texte extrait est garde, pour que la suite de la conversation
    # puisse encore s'y referer.
    piece_jointe_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    piece_jointe_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    piece_jointe_texte: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionElProfessorFamille] = relationship(back_populates="messages")
