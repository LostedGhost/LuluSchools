from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.territoires import verifier_territoire
from app.modules.etablissements.models import PolitiqueDepassement, StatutEtablissement, StatutRentree, TypeEtablissement


class AdminEtablissementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prenom: str
    email: EmailStr


class EtablissementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    type: TypeEtablissement
    statut: StatutEtablissement
    admin: AdminEtablissementCreate
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    departement: str | None = None
    commune: str | None = None

    @model_validator(mode="after")
    def _territoire_connu(self):
        verifier_territoire(self.departement, self.commune)
        return self


class TerritoireUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    departement: str
    commune: str

    @model_validator(mode="after")
    def _territoire_connu(self):
        verifier_territoire(self.departement, self.commune)
        return self


class EtablissementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    type: TypeEtablissement
    statut: StatutEtablissement
    code_etablissement: str
    latitude: float | None
    longitude: float | None
    description: str | None
    actif: bool
    admission_automatique: bool = False
    departement: str | None = None
    commune: str | None = None


class ParametresEtablissementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admission_automatique: bool


class LocalisationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DescriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None


class ActionGroupeeEtablissementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(min_length=1)
    action: str = Field(pattern="^(suspendre|reactiver)$")
    motif: str = Field(min_length=1)


class ClasseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: str
    filiere: str | None = None
    annee_academique: str | None = None
    capacite: int
    politique_depassement: PolitiqueDepassement
    enseignement: Literal["general", "technique", "professionnel"] | None = None
    # UC-24 : optionnel - permet a un A+/A++ de preparer les classes de l'annee suivante
    # en avance. Par defaut, l'annee academique en cours au moment de la creation.
    annee_academique: str | None = None


class ClasseOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    niveau: str
    filiere: str | None
    annee_academique: str
    reconduite_depuis_id: str | None
    capacite: int
    politique_depassement: PolitiqueDepassement
    annee_academique: str
    enseignement: str | None = None


class ReconduireClassesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_ids: list[str] = Field(min_length=1)
    nouvelle_annee: str = Field(min_length=1)


class AffectationEnseignantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enseignant_utilisateur_id: str


class AffectationEnseignantOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    enseignant_id: str
    classe_id: str
    est_professeur_principal: bool


class ProfesseurPrincipalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enseignant_utilisateur_id: str


class SalleEnseignantOut(BaseModel):
    """UC-24 : vue enrichie d'une classe pour l'enseignant qui la consulte (GET
    /mes-classes-affectees) - une ClasseOut ne suffit pas, il faut aussi le nom de
    l'etablissement (l'enseignant peut intervenir dans plusieurs etablissements) et
    l'effectif, sans que l'enseignant ait a faire d'appels supplementaires."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    etablissement_nom: str
    niveau: str
    capacite: int
    effectif: int
    annee_academique: str
    est_professeur_principal: bool


class EleveClasseOut(BaseModel):
    """UC-24.3 : liste des eleves d'une classe, cote enseignant - jamais plus que le
    strict necessaire pour identifier l'eleve (pas de date de naissance/nationalite ici,
    reservees aux ecrans d'inscription)."""

    model_config = ConfigDict(extra="forbid")

    eleve_id: str
    utilisateur_id: str | None
    nom: str
    prenom: str
    matricule: str | None


class EtablissementVitrineOut(BaseModel):
    """Version publique et minimale d'un etablissement, pour la vitrine marketing de la landing page
    (aucun champ interne : ni code_etablissement, ni email d'admin)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    type: TypeEtablissement
    statut: StatutEtablissement
    nb_classes: int
    nb_postes_ouverts: int
    latitude: float | None
    longitude: float | None


class PosteVitrineOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    titre: str
    etablissement_id: str
    etablissement_nom: str
    etablissement_type: TypeEtablissement


class VitrineTotauxOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    etablissements: int
    classes: int
    postes_ouverts: int


class VitrinePubliqueOut(BaseModel):
    """Teaser leger pour la landing page : quelques etablissements en avant, pas
    l'annuaire complet (voir AnnuairePubliqueOut, qui lui est fait pour ca)."""

    model_config = ConfigDict(extra="forbid")

    etablissements: list[EtablissementVitrineOut]
    postes_ouverts: list[PosteVitrineOut]
    totaux: VitrineTotauxOut


class EtablissementPhotoOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    ordre: int


class EtablissementPhotoPubliqueOut(BaseModel):
    """Version publique d'une photo : url signee resolue a la demande, jamais l'id LuluFiles brut."""

    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    ordre: int


class AnnuairePubliqueOut(BaseModel):
    """Annuaire public paginable des etablissements (page dediee, pas la landing
    page) : la plateforme a vocation nationale, le nombre d'etablissements ne
    doit jamais etre suppose petit."""

    model_config = ConfigDict(extra="forbid")

    items: list[EtablissementVitrineOut]
    total: int
    limit: int
    offset: int


# ═══════════════════════════════════════════════════════════════
# Lot admin etablissement (Phase 6) : rentree scolaire (UC-39/40/55/56)
# ═══════════════════════════════════════════════════════════════


class RentreeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annee_academique: str = Field(min_length=1)


class RentreeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    annee_academique: str
    statut: StatutRentree
    created_at: datetime


class InviterTuteursResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nb_tuteurs_notifies: int


# ═══════════════════════════════════════════════════════════════
# Vie scolaire (UC-41/42/57)
# ═══════════════════════════════════════════════════════════════


class InscriptionVieScolaireOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    etablissement_id: str
    etablissement_nom: str
    classe_niveau: str
    classe_filiere: str | None
    annee_academique: str
    statut: str
    created_at: datetime


class BulletinVieScolaireOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    etablissement_nom: str
    periode: str
    moyenne_generale: float
    decision_passage: str | None


class VieScolaireOut(BaseModel):
    """UC-41/42/57 : vue agregee en lecture, aucune nouvelle table - `photo_url` n'est
    renseignee que si l'eleve est un etudiant (derniere inscription validee dans un
    etablissement de type UP), jamais pour un eleve EP/ES (regle appliquee cote routeur,
    jamais devinable depuis ce seul schema)."""

    model_config = ConfigDict(extra="forbid")

    eleve_id: str
    nom: str
    prenom: str
    date_naissance: date
    matricule: str | None
    est_etudiant: bool
    photo_url: str | None
    inscriptions: list[InscriptionVieScolaireOut]
    bulletins: list[BulletinVieScolaireOut]


# ═══════════════════════════════════════════════════════════════
# Console etablissement (UC-45/46/60/61) : filtre classe et/ou annee, objet au choix
# ═══════════════════════════════════════════════════════════════


class ConsoleEleveOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_id: str
    nom: str
    prenom: str
    matricule: str | None
    classe_id: str
    classe_niveau: str
    classe_filiere: str | None
    statut_inscription: str


class ConsoleEnseignantOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utilisateur_id: str
    nom: str
    prenom: str
    classe_id: str
    classe_niveau: str
    classe_filiere: str | None


class ConsoleTuteurOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utilisateur_id: str
    nom: str
    prenom: str
    email: str | None
    nb_enfants_dans_le_perimetre: int


class ConsoleCoursOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    titre: str
    chapitre: str
    classe_id: str
    classe_niveau: str
    enseignant_nom: str
    enseignant_prenom: str


class ConsoleNoteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_id: str
    eleve_nom: str
    eleve_prenom: str
    classe_id: str
    classe_niveau: str
    periode: str
    moyenne_generale: float
    decision_passage: str | None


class ConsoleElevesPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsoleEleveOut]
    total: int
    limit: int
    offset: int


class ConsoleEnseignantsPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsoleEnseignantOut]
    total: int
    limit: int
    offset: int


class ConsoleTuteursPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsoleTuteurOut]
    total: int
    limit: int
    offset: int


class ConsoleCoursPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsoleCoursOut]
    total: int
    limit: int
    offset: int


class ConsoleNotesPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsoleNoteOut]
    total: int
    limit: int
    offset: int


class PropositionAffectationOut(BaseModel):
    classe_id: str
    classe: str
    enseignant_utilisateur_id: str
    enseignant: str
    matiere: str | None
    principal: bool
    motif: str


class LigneAffectation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    classe_id: str
    enseignant_utilisateur_id: str
    principal: bool = False


class AppliquerAffectationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lignes: list[LigneAffectation] = Field(min_length=1, max_length=1000)


class ResultatAffectationsAuto(BaseModel):
    affectations_creees: int
