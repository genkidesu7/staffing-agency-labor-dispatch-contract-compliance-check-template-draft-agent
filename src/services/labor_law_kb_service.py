"""AgentCore Platform v1.0"""

# Service layer: vector-similarity retrieval over the 労働者派遣法 labor-law corpus.
# Must NOT contain business logic, routing, or credentials.
# Nodes call this; this calls shared/services/ for external integrations.

from __future__ import annotations

import logging
from typing import Any

from src.services.mock_mode import mock_mode_enabled

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class LaborLawKbService:
    """Vector-similarity retrieval over the 労働者派遣法 KB.

    Retrieves statute passages (労働者派遣法 第26条 mandatory items, 厚労省 必要記載事項ガイド,
    同一労働同一賃金 model clauses) scoped by engagement type and clause topic.

    Usage from a node::

        service = LaborLawKbService()
        passages = await service.retrieve(engagement_type, clause_topics, credential_handle)
    """

    def __init__(self, kb_path: str = "./kb/") -> None:
        self._kb_path = kb_path
        self._mock_mode: bool = mock_mode_enabled()

    async def retrieve(
        self,
        engagement_type: str,
        clause_topics: list[str],
        credential_handle: str,
    ) -> list[dict[str, Any]]:
        """Retrieve statute passages relevant to the given clause topics.

        Args:
            engagement_type: Classified dispatch engagement (e.g. "it_engineer",
                "manufacturing") used to scope retrieval.
            clause_topics: Clause topic strings extracted from the contract to
                embed and search against the vector index.
            credential_handle: Opaque handle from InvocationContext.credential_handle.
                Never log or store this value.

        Returns:
            List of passage dicts: {source, article, text, score}.
        """
        if not credential_handle:
            raise ValueError(
                "LaborLawKbService.retrieve: credential_handle is empty — " "check InvocationContext configuration"
            )
        return await self._call_external(engagement_type, clause_topics, credential_handle)

    async def _call_external(
        self,
        engagement_type: str,
        clause_topics: list[str],
        credential_handle: str,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        if self._mock_mode:
            from src.services.mock_data import stub_retrieve_statute_context

            return await stub_retrieve_statute_context(engagement_type, clause_topics)
        raise NotImplementedError(
            "LaborLawKbService._call_external: not yet wired. "
            "Wire shared/services/<vector_client> against kb_path "
            f"({self._kb_path}) in the next sprint."
        )
