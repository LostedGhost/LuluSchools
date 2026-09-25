from pydantic import BaseModel, ConfigDict, EmailStr

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


class EtablissementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    type: TypeEtablissement
    statut: StatutEtablissement
    code_etablissement: str


class ClasseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: str
    capacite: int
    politique_depassement: PolitiqueDepassement


class ClasseOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    niveau: str
    capacite: int
    politique_depassement: PolitiqueDepassement


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
    model_config = ConfigDict(extra="forbid")

    etablissements: list[EtablissementVitrineOut]
    postes_ouverts: list[PosteVitrineOut]
    totaux: VitrineTotauxOut
