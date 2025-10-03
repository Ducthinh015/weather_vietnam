import os
import pytest
from backend.app import create_app


@pytest.fixture()
def client():
    os.environ["OPENWEATHER_API_KEY"] = os.getenv("OPENWEATHER_API_KEY", "test")
    app = create_app()
    app.config.update({"TESTING": True})
    return app.test_client()


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json.get("status") == "ok"
