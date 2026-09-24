import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import uuid

from app.core.database import Base, get_db
from app.core.email import EmailDeliveryError, get_email_client
from app.core.files import get_files_client
from app.core.llm import DocumentScoringError, get_llm_client
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.identite.models import RoleUtilisateur, Utilisateur


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class FakeEmailClient:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.should_fail = False

    def send_otp_email(self, to_email: str, to_name: str, code: str) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append({"to_email": to_email, "to_name": to_name, "code": code})

    def send_temporary_credentials_email(
        self, to_email: str, to_name: str, login_id: str, mot_de_passe: str
    ) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append(
            {
                "to_email": to_email,
                "to_name": to_name,
                "login_id": login_id,
                "mot_de_passe": mot_de_passe,
            }
        )


@pytest.fixture()
def fake_email_client() -> FakeEmailClient:
    return FakeEmailClient()


class FakeFilesClient:
    def __init__(self) -> None:
        self.uploaded: list[dict] = []

    def upload(self, content: bytes, filename: str, content_type: str) -> str:
        file_id = str(uuid.uuid4())
        self.uploaded.append({"file_id": file_id, "filename": filename, "content_type": content_type})
        return file_id

    def get_signed_link(self, file_id: str, disposition: str = "attachment") -> str:
        return f"https://lulufiles-api.onrender.com/files/{file_id}/content?signed=1"


@pytest.fixture()
def fake_files_client() -> FakeFilesClient:
    return FakeFilesClient()


class FakeLLMClient:
    def __init__(self) -> None:
        self.scores_par_type: dict[str, float] = {}
        self.score_par_defaut = 90.0
        self.types_en_echec: set[str] = set()

    def noter_document(self, image_bytes: bytes, content_type: str, critere: str) -> float:
        for type_document in self.types_en_echec:
            if type_document in critere:
                raise DocumentScoringError("echec simule")
        for type_document, score in self.scores_par_type.items():
            if type_document in critere:
                return score
        return self.score_par_defaut


@pytest.fixture()
def fake_llm_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture()
def client(db_session, fake_email_client, fake_files_client, fake_llm_client):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_client] = lambda: fake_email_client
    app.dependency_overrides[get_files_client] = lambda: fake_files_client
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def creer_utilisateur_direct(
    db_session, *, role: RoleUtilisateur, login_id: str, nom: str = "Test", prenom: str = "Test"
) -> Utilisateur:
    """Insere un utilisateur directement en base, pour les roles sans auto-inscription
    (admin ministeriel, admin etablissement provisionne autrement que via le flux teste)."""
    utilisateur = Utilisateur(
        nom=nom,
        prenom=prenom,
        login_id=login_id,
        email=login_id,
        mot_de_passe_hash=hash_password("Password1"),
        role=role,
        email_verifie=True,
    )
    db_session.add(utilisateur)
    db_session.commit()
    db_session.refresh(utilisateur)
    return utilisateur


def token_pour(utilisateur: Utilisateur) -> str:
    return create_access_token(utilisateur.id, utilisateur.role.value)


@pytest.fixture()
def admin_ministeriel(db_session):
    return creer_utilisateur_direct(
        db_session, role=RoleUtilisateur.ADMIN_MINISTERIEL, login_id="ministere@example.com"
    )


@pytest.fixture()
def admin_ministeriel_headers(admin_ministeriel):
    return {"Authorization": f"Bearer {token_pour(admin_ministeriel)}"}


@pytest.fixture()
def tuteur_headers(client, fake_email_client):
    payload = {
        "nom": "Dossou",
        "prenom": "Awa",
        "email": "awa.tuteur.fixture@example.com",
        "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=payload)
    code = fake_email_client.sent[-1]["code"]
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture()
def enseignant_headers(client, fake_email_client):
    payload = {
        "nom": "Traore",
        "prenom": "Moussa",
        "email": "moussa.traore.fixture@example.com",
        "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/enseignants", json=payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == payload["email"])
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture()
def etablissement_avec_classe(client, fake_email_client, admin_ministeriel_headers):
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Ecole Primaire Test",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone.fixture@example.com"},
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"]
        for m in fake_email_client.sent
        if m.get("to_email") == "fatou.kone.fixture@example.com"
    )
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "fatou.kone.fixture@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    admin_headers = {"Authorization": f"Bearer {login_admin['access_token']}"}

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 1, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    return {"etablissement": etablissement, "classe": classe, "admin_headers": admin_headers}
