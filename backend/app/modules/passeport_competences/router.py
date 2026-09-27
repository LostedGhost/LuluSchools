from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.passeport_competences.pdf import generer_pdf_passeport
from app.modules.passeport_competences.schemas import PasseportExportOut, PasseportOut
from app.modules.passeport_competences.service import construire_passeport

router = APIRouter(tags=["passeport-competences"])


def _verifier_tuteur_de_l_eleve(db: Session, tuteur: Utilisateur, eleve_utilisateur_id: str) -> None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte tuteur.")


def _obtenir_ou_404(db: Session, eleve_utilisateur_id: str) -> dict:
    passeport = construire_passeport(db, eleve_utilisateur_id)
    if passeport is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Compte eleve introuvable.")
    return passeport


def _exporter_pdf(db: Session, files_client: LuluFilesClient, eleve_utilisateur_id: str) -> PasseportExportOut:
    passeport = _obtenir_ou_404(db, eleve_utilisateur_id)
    pdf_bytes = generer_pdf_passeport(passeport)
    try:
        file_id = files_client.upload(pdf_bytes, "passeport-competences.pdf", "application/pdf")
        lien = files_client.get_signed_link(file_id)
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_indisponible", "Impossible de generer le PDF, veuillez reessayer."
        ) from exc
    return PasseportExportOut(lulufiles_file_id=file_id, lien=lien)


@router.get("/eleves/me/passeport", response_model=PasseportOut)
def obtenir_mon_passeport(
    db: Session = Depends(get_db), eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> dict:
    return _obtenir_ou_404(db, eleve.id)


@router.post("/eleves/me/passeport/export-pdf", response_model=PasseportExportOut)
def exporter_mon_passeport(
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> PasseportExportOut:
    return _exporter_pdf(db, files_client, eleve.id)


@router.get("/mes-enfants/{eleve_utilisateur_id}/passeport", response_model=PasseportOut)
def obtenir_passeport_de_mon_enfant(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> dict:
    _verifier_tuteur_de_l_eleve(db, tuteur, eleve_utilisateur_id)
    return _obtenir_ou_404(db, eleve_utilisateur_id)


@router.post("/mes-enfants/{eleve_utilisateur_id}/passeport/export-pdf", response_model=PasseportExportOut)
def exporter_passeport_de_mon_enfant(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> PasseportExportOut:
    _verifier_tuteur_de_l_eleve(db, tuteur, eleve_utilisateur_id)
    return _exporter_pdf(db, files_client, eleve_utilisateur_id)
