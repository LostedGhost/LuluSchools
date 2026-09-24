import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.email import EmailDeliveryError, get_email_client
from app.main import app


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
