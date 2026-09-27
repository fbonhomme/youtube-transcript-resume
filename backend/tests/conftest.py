import os

# Évite l'exigence d'ANTHROPIC_API_KEY au chargement de config/summarizer.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from services import api_keys

# Module-scoped on purpose: shared in-memory DB via StaticPool; schema is created/dropped per test.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Les services qui ouvrent leur propre session (clés API) utilisent aussi la base de test.
api_keys._session_factory = _TestingSession


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session():
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    del app.dependency_overrides[get_db]
