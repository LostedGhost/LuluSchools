from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.inscriptions.models import Nationalite, StatutInscription


class InscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prenom: str
    date_naissance: date
    classe_id: str
    nationalite: Nationalite = Nationalite.NATIONALE
    consentement_parental_donne: bool = False


class InscriptionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    classe_id: str
    statut: StatutInscription
    consentement_parental_horodatage: datetime | None = None
    motif_rejet: str | None = None


class RejetInscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str


class InscriptionAvecEleveOut(InscriptionOut):
    """Utilise par GET /tuteurs/me/inscriptions : le tuteur n'a pas besoin de faire un
    aller-retour par eleve pour afficher la liste de ses enfants et leurs demarches."""

    eleve_nom: str
    eleve_prenom: str
    eleve_matricule: str | None
    eleve_utilisateur_id: str | None


class EleveMeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    matricule: str | None
    nationalite: Nationalite
    classe_id: str | None = None
    niveau: str | None = None
    etablissement_id: str | None = None
