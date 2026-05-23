import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.main import app


@pytest.fixture()
def client():
    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    with TestClient(app) as test_client:
        yield test_client
    database.Base.metadata.drop_all(bind=database.engine)
