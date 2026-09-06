import pytest
from httpx import AsyncClient, ASGITransport
from app.ui.api import app


@pytest.mark.asyncio
async def test_health_ok():
    # Use ASGITransport to call the FastAPI app in-process (no network)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    # Accept any version string but require the key to exist
    assert "version" in data and isinstance(data["version"], str)
