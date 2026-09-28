from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EleveCandidat(BaseModel):
    eleve_id: str
    nom: str
    prenom: str
    matricule: str | None


class LigneLue(BaseModel):
    nom_lu: str
    eleve_id: str | None
    confiance: Literal["sur", "probable", "non_trouve"]
    note: float | None = None
    absent: bool = False
    statut: Literal["absent", "retard"] | None = None
    commentaire: str | None = None
    lisible: bool = True


class LectureOut(BaseModel):
    document_id: str
    type: str
    # null si l'IA n'a pas pu lire : l'administrateur saisit alors a la main, la photo sous les yeux.
    lecture: dict | None
    erreur_lecture: str | None = None
    lignes: list[LigneLue] = []
    eleves: list[EleveCandidat] = []
    classe_proposee_id: str | None = None


class LigneNote(BaseModel):
    eleve_id: str
    note: float | None = Field(default=None, ge=0)
    absent: bool = False


class NotesEnregistrement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_id: str
    enseignant_id: str
    matiere: str = Field(min_length=1, max_length=100)
    titre: str = Field(min_length=1, max_length=200)
    date_evaluation: date
    note_sur: float = Field(gt=0, le=1000)
    nature: Literal["sommative", "formative"] = "sommative"
    lignes: list[LigneNote] = Field(min_length=1)


class LigneAppel(BaseModel):
    eleve_id: str
    statut: Literal["absent", "retard"]
    commentaire: str | None = Field(default=None, max_length=300)


class AppelEnregistrement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_id: str
    date: date
    matiere: str | None = Field(default=None, max_length=100)
    lignes: list[LigneAppel]


class CoursEnregistrement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_id: str
    enseignant_id: str
    titre: str = Field(min_length=1, max_length=200)
    chapitre: str = Field(min_length=1, max_length=200)
    contenu: str = Field(min_length=1)


class InscriptionGuichet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_id: str
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    date_naissance: date
    nationalite: Literal["nationale", "etrangere"] = "nationale"
    sexe: Literal["F", "M"] | None = None
    tuteur_nom: str = Field(min_length=1, max_length=200)
    tuteur_telephone: str | None = Field(default=None, max_length=30)
    # Pour un eleve de moins de 16 ans : la fiche porte la signature du parent (Art. 446).
    consentement_signe: bool = False


class InscriptionGuichetOut(BaseModel):
    inscription_id: str
    eleve_id: str
    matricule: str | None
    mot_de_passe_provisoire: str | None
    fiche_identifiants_pdf: str | None  # base64, a imprimer et remettre a la famille


class CopieLue(BaseModel):
    document_id: str
    nom_fichier: str
    nom_lu: str | None
    eleve_id: str | None
    confiance: Literal["sur", "probable", "non_trouve"]


class CopiesLectureOut(BaseModel):
    copies: list[CopieLue]
    eleves: list[EleveCandidat]  # eleves de la classe qui n'ont pas encore de copie


class AffectationCopie(BaseModel):
    document_id: str
    eleve_id: str


class CopiesEnregistrement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    affectations: list[AffectationCopie] = Field(min_length=1)


class ResultatEnregistrement(BaseModel):
    objet_id: str | None
    nombre: int
    message: str


class DocumentPapierOut(BaseModel):
    id: str
    type: str
    statut: str
    nombre_fichiers: int
    objet_type: str | None
    objet_id: str | None
    saisi_par: str
    created_at: datetime
    enregistre_le: datetime | None
    resume: str | None


class EnseignantCandidat(BaseModel):
    id: str
    nom: str
    prenom: str
    matiere: str | None


class DevoirCandidat(BaseModel):
    id: str
    titre: str
    matiere: str
    date_limite: datetime
    copies: int


class ContexteClasse(BaseModel):
    eleves: list[EleveCandidat]
    enseignants: list[EnseignantCandidat]
    devoirs: list[DevoirCandidat]


class ConsentementEnAttente(BaseModel):
    inscription_id: str
    eleve: str
    classe: str
    depose_le: datetime
