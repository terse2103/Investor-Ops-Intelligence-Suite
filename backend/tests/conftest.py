"""Shared pytest fixtures."""
import os

# Skip the startup RAG ingest during tests so TestClient instantiation stays
# fast and does not require network access.
os.environ.setdefault("SKIP_STARTUP_INGEST", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.auth import require_admin, require_auth  # noqa: E402
from app.main import app  # noqa: E402


async def _mock_user() -> dict:
    return {"id": "test-user-id", "email": "user@test.com", "role": "user"}


async def _mock_admin() -> dict:
    return {"id": "test-admin-id", "email": "admin@test.com", "role": "admin"}


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[require_auth] = _mock_user
    app.dependency_overrides[require_admin] = _mock_admin
    yield TestClient(app)
    app.dependency_overrides.clear()
