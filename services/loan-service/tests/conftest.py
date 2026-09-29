import pytest


@pytest.fixture(autouse=True)
def core_api_key(monkeypatch):
    monkeypatch.setenv("CORE_API_KEY", "test-api-key")
