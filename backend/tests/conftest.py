import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.email import EmailDeliveryError, get_email_client
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


@pytest.fixture()
def client(db_session, fake_email_client):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_client] = lambda: fake_email_client
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
