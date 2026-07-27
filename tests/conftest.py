import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["WORKSPACE_ROOT"] = "./test-workspaces"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_data():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    Path("test.db").unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

