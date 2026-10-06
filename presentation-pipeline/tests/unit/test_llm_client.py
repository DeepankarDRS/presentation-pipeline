"""get_llm / extract_usage / get_pricing for chat vs reasoning models (no API calls)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.utils import llm_client
from src.utils.llm_client import extract_usage, get_llm, get_pricing


@pytest.mark.parametrize("model", ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"])
def test_chat_model_gets_temperature(model):
    with patch.object(llm_client, "ChatOpenAI") as chat:
        get_llm("plan_reviewer", model=model, temperature=0.1)
    kwargs = chat.call_args.kwargs
    assert kwargs["temperature"] == 0.1
    assert "reasoning_effort" not in kwargs


@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "o3", "o4-mini", "GPT-5"])
def test_reasoning_model_drops_temperature(model):
    with patch.object(llm_client, "ChatOpenAI") as chat:
        get_llm("plan_reviewer", model=model, temperature=0.1, max_tokens=16000)
    kwargs = chat.call_args.kwargs
    assert "temperature" not in kwargs
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["max_tokens"] == 16000


def test_reasoning_effort_from_config():
    with patch.object(llm_client, "ChatOpenAI") as chat:
        get_llm("plan_reviewer", model="gpt-5-mini", reasoning_effort="high")
    assert chat.call_args.kwargs["reasoning_effort"] == "high"


def test_azure_reasoning_model_drops_temperature():
    with patch.object(llm_client, "AzureChatOpenAI") as azure:
        get_llm("plan_reviewer", provider="azure_openai", model="gpt-5-mini", reasoning_effort="low")
    kwargs = azure.call_args.kwargs
    assert "temperature" not in kwargs
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["azure_deployment"] == "gpt-5-mini"


def test_azure_chat_model_gets_temperature():
    with patch.object(llm_client, "AzureChatOpenAI") as azure:
        get_llm("plan_reviewer", provider="azure_openai", model="gpt-4.1", temperature=0.1)
    kwargs = azure.call_args.kwargs
    assert kwargs["temperature"] == 0.1
    assert "reasoning_effort" not in kwargs


def test_extract_usage_reads_reasoning_tokens():
    response = SimpleNamespace(response_metadata={
        "model_name": "gpt-5-mini",
        "token_usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 3000,
            "completion_tokens_details": {"reasoning_tokens": 2500},
        },
    })
    assert extract_usage(response) == {
        "tokens_in": 1200, "tokens_out": 3000, "tokens_reasoning": 2500, "tokens_cached": 0, "model": "gpt-5-mini",
    }


@pytest.mark.parametrize("token_usage", [
    {"prompt_tokens": 10, "completion_tokens": 20},
    {"prompt_tokens": 10, "completion_tokens": 20, "completion_tokens_details": None},
    {"prompt_tokens": 10, "completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": None}},
])
def test_extract_usage_without_reasoning_tokens(token_usage):
    response = SimpleNamespace(response_metadata={"model_name": "gpt-4.1", "token_usage": token_usage})
    assert extract_usage(response)["tokens_reasoning"] == 0


def test_pricing_for_reasoning_models():
    assert get_pricing("gpt-5-mini") == {"input": 0.25, "output": 2.00}
    assert get_pricing("gpt-5-mini-2025-08-07")["input"] == 0.25  # dated name -> longest prefix
    assert get_pricing("gpt-5")["input"] == 1.25
    assert get_pricing("o4-mini")["output"] == 4.40
