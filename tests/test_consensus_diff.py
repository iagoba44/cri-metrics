"""Tests para Consensus Diff Service."""
import pytest
from app.services.consensus_diff import FallbackClient, ConsensusDiff

def test_fallback_client_extracts_cri():
    client = FallbackClient()
    prompt = "CRI: 45.50, TMI: 52.00, modo REAL"
    result = None
    import asyncio
    result = asyncio.run(client.evaluate(prompt))
    assert result is not None
    assert "ai_risk_score" in result
    assert 0 <= result["ai_risk_score"] <= 100
    assert "reasoning_summary" in result

def test_fallback_client_high_divergence():
    client = FallbackClient()
    prompt = "CRI: 20.00, TMI: 80.00, modo REAL"
    import asyncio
    result = asyncio.run(client.evaluate(prompt))
    assert result is not None
    assert result["ai_risk_score"] > 20  # Divergence boosts score

def test_consensus_diff_build_prompt():
    consensus = ConsensusDiff()
    snapshot = {
        "cri_score": 45.0,
        "cri_zone": "MODERATE",
        "tmi_score": 52.0,
        "cri_delta_24h": 5.0,
        "mode": "REAL",
        "validated_news": [
            {"title": "GPU market crash", "semantic_score": 0.8},
        ],
    }
    prompt = consensus.build_prompt(snapshot)
    assert "45.0" in prompt
    assert "GPU market crash" in prompt
    assert "MODERATE" in prompt
