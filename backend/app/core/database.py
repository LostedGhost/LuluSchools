from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker:
    """Injectable (Depends) pour toute execution hors du cycle de vie d'une requete HTTP
    - typiquement une BackgroundTasks : la session de la requete (get_db) est deja
    fermee une fois la reponse envoyee, il faut donc en ouvrir une nouvelle. Passer par
    Depends (plutot qu'importer SessionLocal directement dans les routers) permet aux
    tests de rediriger vers le moteur de test (voir tests/conftest.py)."""
    return SessionLocal
