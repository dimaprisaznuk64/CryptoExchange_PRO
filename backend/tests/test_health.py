import pytest


@pytest.mark.asyncio
async def test_health_status_fields(client, db_session):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "CryptoExchange_PRO"
    assert body["database"] in ("connected", "error")
    assert body["redis"] in ("connected", "disabled", "error")


@pytest.mark.asyncio
async def test_health_redis_reports_state(client, db_session):
    import app.core.cache as cache_module

    if cache_module.redis_client is not None:
        resp = await client.get("/api/v1/health")
        assert resp.json()["redis"] in ("connected", "error")