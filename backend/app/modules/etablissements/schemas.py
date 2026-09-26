from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.etablissements.models import PolitiqueDepassement, StatutEtablissement, TypeEtablissement


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


class EtablissementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    type: TypeEtablissement
    statut: StatutEtablissement
    code_etablissement: str
    latitude: float | None
    longitude: float | None


class LocalisationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ClasseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: str
    capacite: int
    politique_depassement: PolitiqueDepassement
    # UC-24 : optionnel - permet a un A+/A++ de preparer les classes de l'annee suivante
    # en avance. Par defaut, l'annee academique en cours au moment de la creation.
    annee_academique: str | None = None


class ClasseOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    niveau: str
    capacite: int
    politique_depassement: PolitiqueDepassement
    annee_academique: str


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
