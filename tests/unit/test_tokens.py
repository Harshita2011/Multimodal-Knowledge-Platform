from app.utils.tokens import estimate_token_count, pack_context_by_tokens, truncate_text_to_tokens


def test_token_count_basic():
    assert estimate_token_count("hello, world!") >= 3


def test_truncate_prefers_sentence_boundaries():
    text = "First sentence. Second sentence should be truncated."
    out = truncate_text_to_tokens(text, 3)
    assert "First" in out


def test_pack_context_respects_budget():
    packed = pack_context_by_tokens(["one two three", "four five six"], max_tokens=4)
    assert len(packed) >= 1
