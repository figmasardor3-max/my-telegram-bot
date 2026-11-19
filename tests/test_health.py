import pytest
from aiohttp import web
from app.main import health_check


@pytest.mark.asyncio
async def test_health_check_endpoint():
    request = None
    response = await health_check(request)
    assert response.status == 200
    assert response.content_type == "application/json"
