# SVC-C2-047 — Unit Tests: LaborLawKbService

import asyncio

import pytest

from src.services.labor_law_kb_service import LaborLawKbService


class TestLaborLawKbService:
    def setup_method(self):
        self.service = LaborLawKbService()

    def test_retrieve_mock_mode_returns_passages(self):
        result = asyncio.run(
            self.service.retrieve("it_engineer", ["wage", "equal_pay"], "mock-key-for-testing")
        )
        assert len(result) > 0
        assert all("source" in p and "article" in p and "text" in p for p in result)

    def test_retrieve_requires_credential_handle(self):
        with pytest.raises(ValueError):
            asyncio.run(self.service.retrieve("general", ["wage"], ""))

    def test_manufacturing_engagement_includes_extra_passage(self):
        general = asyncio.run(
            self.service.retrieve("general", ["wage"] * 5, "mock-key-for-testing")
        )
        manufacturing = asyncio.run(
            self.service.retrieve("manufacturing", ["wage"] * 5, "mock-key-for-testing")
        )
        assert len(manufacturing) >= len(general)
