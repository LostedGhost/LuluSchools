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
