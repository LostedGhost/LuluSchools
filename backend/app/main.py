import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.messages_validation import message_validation
from app.modules.actes.router import router as actes_router
from app.modules.audit.router import router as audit_router
from app.modules.billetterie.router import router as billetterie_router
from app.modules.coffre_fort.router import router as coffre_fort_router
from app.modules.controle_acces.router import router as controle_acces_router
from app.modules.cours_direct.router import router as cours_direct_router
from app.modules.etablissements.router import classes_router as etablissements_classes_router
from app.modules.etablissements.router import router as etablissements_router
from app.modules.evaluations.router import router as evaluations_router
from app.core.files import get_files_client
from app.core.llm import get_llm_client
from app.modules.recrutement.automatisation import renoter_tache
from app.modules.administration.a_traiter import router as a_traiter_router
from app.modules.administration.compteurs import router as compteurs_router
from app.modules.saisie_papier.router import router as saisie_papier_router
from app.modules.pedagogie.el_professor_chat import router as el_professor_chat_router
from app.modules.pedagogie.router import router as pedagogie_router
from app.modules.identite.router import admin_router as identite_admin_router
from app.modules.identite.router import auth_router, enseignant_router, me_router
from app.modules.identite.router import router as identite_router
from app.modules.inscriptions.router import mon_espace_router as inscriptions_mon_espace_router
from app.modules.inscriptions.router import router as inscriptions_router
from app.modules.marketplace.router import router as marketplace_router
from app.modules.messagerie.router import router as messagerie_router
from app.modules.micro_jobs.router import router as micro_jobs_router
from app.modules.paiements.router import router as kkiapay_webhook_router
from app.modules.passeport_competences.router import router as passeport_competences_router
from app.modules.radar_familial.router import router as radar_familial_router
from app.modules.recrutement.router import router as recrutement_router
from app.modules.services_scolaires.router import router as services_scolaires_router
from app.modules.vie_scolaire.router import router as vie_scolaire_router
from app.modules.visites_virtuelles.router import router as visites_virtuelles_router
from app.system.router import router as system_router



def _purger_casiers_expires_tache() -> None:
    from app.core.database import SessionLocal
    from app.modules.recrutement.router import purger_casiers_expires

    db = SessionLocal()
    try:
        nombre = purger_casiers_expires(db)
        if nombre:
            logger.info("purge casiers judiciaires : %s contenu(s) expire(s) supprime(s)", nombre)
    except Exception:
        logger.exception("purge des casiers judiciaires expires en echec")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Taches periodiques (APScheduler en process, ADR-001) uniquement en production :
    la suite de tests ne doit jamais toucher la vraie base."""
    planificateur = None
    if settings.environment == "production":
        from apscheduler.schedulers.background import BackgroundScheduler

        from app.core.database import SessionLocal

        planificateur = BackgroundScheduler(timezone="UTC")
        planificateur.add_job(_purger_casiers_expires_tache, "interval", hours=6)
        # Fabriques et non instances : un client cree au demarrage fait echouer tout le
        # serveur si une cle manque (incident Render du 2026-09-28, FREELLM_API_KEY vide).
        planificateur.add_job(renoter_tache, "interval", hours=1, args=[SessionLocal, get_llm_client, get_files_client])
        planificateur.start()
        _purger_casiers_expires_tache()
    yield
    if planificateur is not None:
        planificateur.shutdown(wait=False)


app = FastAPI(title="LuluSchools API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail), "details": {}}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": message_validation(exc.errors()),
                "details": {"fields": jsonable_encoder(exc.errors())},
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Contrainte d'unicite violee (ex. deux requetes concurrentes, identifiant de
    transaction deja rattache) : un conflit metier, pas une panne serveur."""
    logger.warning("Contrainte d'integrite violee sur %s %s : %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "conflit", "message": "Cette opération entre en conflit avec des données existantes.", "details": {}}},
    )


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
    logger.warning("Donnee refusee par la base sur %s %s : %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "donnee_invalide", "message": "Une valeur fournie est invalide ou trop longue.", "details": {}}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Filet de secours : sans lui, toute exception non prevue (bug reel, panne d'un
    service externe non couverte par un except specifique) atterrit sur le handler par
    defaut de Starlette - une reponse SANS la forme {"error": {...}} du contrat, que le
    frontend (messageErreur()) ne sait pas interpreter et remplace silencieusement par
    un message generique ("reessayez"), sans jamais rien logger de son cote. Loggee ici
    (visible dans les logs Render) pour rester diagnostiquable en production."""
    logger.exception("Exception non geree sur %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "erreur_interne", "message": "Une erreur inattendue est survenue.", "details": {}}},
    )


app.include_router(system_router, prefix="/api/v1")
app.include_router(identite_router, prefix="/api/v1")
app.include_router(enseignant_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(identite_admin_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(etablissements_router, prefix="/api/v1")
app.include_router(etablissements_classes_router, prefix="/api/v1")
app.include_router(inscriptions_router, prefix="/api/v1")
app.include_router(inscriptions_mon_espace_router, prefix="/api/v1")
app.include_router(recrutement_router, prefix="/api/v1")
app.include_router(pedagogie_router, prefix="/api/v1")
app.include_router(el_professor_chat_router, prefix="/api/v1")
app.include_router(a_traiter_router, prefix="/api/v1")
app.include_router(compteurs_router, prefix="/api/v1")
app.include_router(saisie_papier_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")
app.include_router(actes_router, prefix="/api/v1")
app.include_router(controle_acces_router, prefix="/api/v1")
app.include_router(services_scolaires_router, prefix="/api/v1")
app.include_router(vie_scolaire_router, prefix="/api/v1")
app.include_router(billetterie_router, prefix="/api/v1")
app.include_router(messagerie_router, prefix="/api/v1")
app.include_router(cours_direct_router, prefix="/api/v1")
app.include_router(visites_virtuelles_router, prefix="/api/v1")
app.include_router(micro_jobs_router, prefix="/api/v1")
app.include_router(marketplace_router, prefix="/api/v1")
app.include_router(coffre_fort_router, prefix="/api/v1")
app.include_router(radar_familial_router, prefix="/api/v1")
app.include_router(passeport_competences_router, prefix="/api/v1")
app.include_router(kkiapay_webhook_router, prefix="/api/v1")
