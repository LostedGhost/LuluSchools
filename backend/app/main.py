from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.modules.actes.router import router as actes_router
from app.modules.billetterie.router import router as billetterie_router
from app.modules.controle_acces.router import router as controle_acces_router
from app.modules.cours_direct.router import router as cours_direct_router
from app.modules.etablissements.router import router as etablissements_router
from app.modules.evaluations.router import router as evaluations_router
from app.modules.pedagogie.router import router as pedagogie_router
from app.modules.identite.router import auth_router, enseignant_router, me_router
from app.modules.identite.router import router as identite_router
from app.modules.inscriptions.router import mon_espace_router as inscriptions_mon_espace_router
from app.modules.inscriptions.router import router as inscriptions_router
from app.modules.messagerie.router import router as messagerie_router
from app.modules.micro_jobs.router import router as micro_jobs_router
from app.modules.paiements.router import router as kkiapay_webhook_router
from app.modules.recrutement.router import router as recrutement_router
from app.modules.services_scolaires.router import router as services_scolaires_router
from app.modules.visites_virtuelles.router import router as visites_virtuelles_router
from app.system.router import router as system_router

app = FastAPI(title="LuluSchools API", version="0.1.0")

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
                "message": "Donnees invalides.",
                "details": {"fields": jsonable_encoder(exc.errors())},
            }
        },
    )


app.include_router(system_router, prefix="/api/v1")
app.include_router(identite_router, prefix="/api/v1")
app.include_router(enseignant_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(etablissements_router, prefix="/api/v1")
app.include_router(inscriptions_router, prefix="/api/v1")
app.include_router(inscriptions_mon_espace_router, prefix="/api/v1")
app.include_router(recrutement_router, prefix="/api/v1")
app.include_router(pedagogie_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")
app.include_router(actes_router, prefix="/api/v1")
app.include_router(controle_acces_router, prefix="/api/v1")
app.include_router(services_scolaires_router, prefix="/api/v1")
app.include_router(billetterie_router, prefix="/api/v1")
app.include_router(messagerie_router, prefix="/api/v1")
app.include_router(cours_direct_router, prefix="/api/v1")
app.include_router(visites_virtuelles_router, prefix="/api/v1")
app.include_router(micro_jobs_router, prefix="/api/v1")
app.include_router(kkiapay_webhook_router, prefix="/api/v1")
