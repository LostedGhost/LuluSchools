from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


class _FakeSession:
    def __init__(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def execute(self, *_args, **_kwargs):
        if self._should_fail:
            raise RuntimeError("base de donnees injoignable (simulee)")
        return None

    def close(self) -> None:
        pass


def _override_get_db(should_fail: bool):
    def _dependency():
        session = _FakeSession(should_fail)
        try:
            yield session
        finally:
            session.close()

    return _dependency


def test_health_ok_when_database_reachable():
    app.dependency_overrides[get_db] = _override_get_db(should_fail=False)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "checks": {"database": True}}
    finally:
        app.dependency_overrides.clear()


def test_health_degraded_when_database_unreachable():
    app.dependency_overrides[get_db] = _override_get_db(should_fail=True)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert response.json() == {"status": "degraded", "checks": {"database": False}}
    finally:
        app.dependency_overrides.clear()


def test_health_does_not_require_authentication():
    app.dependency_overrides[get_db] = _override_get_db(should_fail=False)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code != 401
    finally:
        app.dependency_overrides.clear()
