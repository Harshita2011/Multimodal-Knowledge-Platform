import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def test_token_budget_prefers_max_context_tokens():
    s = Settings(MAX_CONTEXT_TOKENS=6000, MAX_PROMPT_TOKENS=8000, RESERVED_RESPONSE_TOKENS=1500)
    assert s.resolved_context_token_budget == 6000


def test_token_budget_fallback_uses_prompt_minus_reserved():
    s = Settings(MAX_CONTEXT_TOKENS=None, MAX_PROMPT_TOKENS=8000, RESERVED_RESPONSE_TOKENS=1500)
    assert s.resolved_context_token_budget == 6500


def test_token_budget_validation_fails_when_missing_configs():
    with pytest.raises(ValidationError):
        Settings(MAX_CONTEXT_TOKENS=None, MAX_PROMPT_TOKENS=None, RESERVED_RESPONSE_TOKENS=None)
