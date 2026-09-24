"""AgentCore Platform v1.0"""

import os

import pytest

os.environ.setdefault("USE_MOCK", "true")


@pytest.fixture
def base_state() -> dict:
    """Minimal state dict with the 4 fields InvocationContext.from_state() requires."""
    return {
        "correlation_id": "test-correlation-id",
        "session_id": "test-session-id",
        "thread_id": "test-thread-id",
        "trace_id": "test-trace-id",
        "caller_trust_level": "VERIFIED_EXTERNAL",
        "node_history": [],
        "error_log": [],
    }


@pytest.fixture
def bound_test_secrets():
    """Bind mock secrets for the duration of a test."""
    from framework.secrets.context import bound_secrets
    from shared.secrets.inmemory_provider import InMemoryProvider

    provider = InMemoryProvider(
        {
            "LABOR_LAW_KB_API_KEY": "mock-key-for-testing",
            "AZURE_OPENAI_API_KEY": "mock-key-for-testing",
        }
    )
    with bound_secrets(provider):
        yield provider
