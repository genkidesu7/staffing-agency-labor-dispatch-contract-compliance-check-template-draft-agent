# SVC-C2-047 — Integration Test: /invoke over a real ASGI transport
#
# Regression test (test_rule.md Rule 3): src/api/server.py's /invoke route is
# `async def` and wraps agent.invoke(), which is sync and whose inner nodes
# call asyncio.run()/run in a thread pool. An in-process test that imports the
# agent and calls .invoke() directly (see test_graph_invoke.py) never enters a
# running event loop, so it cannot reproduce "asyncio.run() cannot be called
# from a running event loop" being silently swallowed into status: "error".
# Only a test that drives the ASGI app itself puts the call inside a real
# running loop, the same way uvicorn does.

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("USE_MOCK", "true")
# Mirrors deploy-stg (implementation_rule.md §4): a fresh checkout has no
# upstream auth middleware, so server.py's entry-point token check is what
# promotes the caller from ANONYMOUS to VERIFIED_EXTERNAL. Nodes require
# VERIFIED_EXTERNAL (S-1) — without this, every request is denied at S-1,
# not the async/sync boundary this test targets.
os.environ.setdefault("INVOKE_AUTH_TOKEN", "test-invoke-auth-token")

from src.api.server import app  # noqa: E402  (env must be set before import)

SAMPLE_CONTRACT = (
    "第1条 派遣期間は2026年4月1日から2027年3月31日までとする。"
    "第2条 賃金は月額25万円とする。"
    "第3条 安全衛生教育を実施する。"
)
_AUTH_HEADERS = {"Authorization": f"Bearer {os.environ['INVOKE_AUTH_TOKEN']}"}


@pytest.mark.asyncio
async def test_invoke_endpoint_succeeds_over_http():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/invoke", json={"input": SAMPLE_CONTRACT}, headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"


@pytest.mark.asyncio
async def test_invoke_endpoint_rejects_empty_input_without_crashing():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/invoke", json={"input": ""}, headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
