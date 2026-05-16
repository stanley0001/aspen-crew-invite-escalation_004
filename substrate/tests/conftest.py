from typing import Callable, Dict

import pytest
from fastapi.testclient import TestClient

from crew import auth, models
from crew.main import app


@pytest.fixture(autouse=True)
def _reset_state():
    """Clear store + tokens between tests so order does not matter."""
    models.store.reset()
    models.seed(models.store)
    auth._clear_tokens()
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture()
def root_token(client: TestClient) -> str:
    return _login(client, "root@crew.local", "root123")


@pytest.fixture()
def alice_token(client: TestClient) -> str:
    return _login(client, "alice@crew.local", "alice123")


@pytest.fixture()
def bob_token(client: TestClient) -> str:
    return _login(client, "bob@crew.local", "bob123")


@pytest.fixture()
def dana_token(client: TestClient) -> str:
    return _login(client, "dana@crew.local", "dana123")


@pytest.fixture()
def auth_header() -> Callable[[str], Dict[str, str]]:
    def _h(token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}"}
    return _h
