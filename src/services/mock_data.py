"""AgentCore Platform v1.0"""

# Mock stubs for service external calls (USE_MOCK=true gate). Deterministic
# fixture data only — never real KB content or credentials.

from __future__ import annotations

from typing import Any


async def stub_retrieve_statute_context(
    engagement_type: str,
    clause_topics: list[str],
) -> list[dict[str, Any]]:
    """Deterministic fixture passages for LaborLawKbService in mock mode."""
    base_passages = [
        {
            "source": "労働者派遣法",
            "article": "第26条第1項第1号",
            "text": "労働者派遣の役務の提供を受ける者に関する事項として、当該者の氏名又は名称等を明示すること。",
            "score": 0.91,
        },
        {
            "source": "労働者派遣法",
            "article": "第26条第1項第8号",
            "text": "同一労働同一賃金に係る協定対象派遣労働者であるか否かの別を明示すること。",
            "score": 0.88,
        },
        {
            "source": "厚労省 必要記載事項ガイド",
            "article": "必要記載事項ガイド 3-2",
            "text": "派遣先は、比較対象労働者の待遇に関する情報を派遣元に提供しなければならない。",
            "score": 0.83,
        },
        {
            "source": "同一労働同一賃金モデル条項",
            "article": "労使協定方式モデル条項 第4条",
            "text": "労使協定方式による場合、協定に定める賃金水準が同種業務の一般労働者の平均的な賃金額以上であること。",
            "score": 0.80,
        },
    ]
    if engagement_type == "manufacturing":
        base_passages.append(
            {
                "source": "労働者派遣法",
                "article": "第26条第1項第5号",
                "text": "製造業務専門派遣元管理者の選任に関する事項を明示すること。",
                "score": 0.85,
            }
        )
    return base_passages[: max(len(clause_topics), 1) + 2]
