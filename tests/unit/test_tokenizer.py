from app.utils.tokenizer import HeuristicTokenizer


def test_heuristic_tokenizer_counts_tokens_deterministically():
    tok = HeuristicTokenizer()
    text = "Hello, world!"
    assert tok.count_tokens(text) == tok.count_tokens(text)


def test_heuristic_tokenizer_truncates_sentence_safely():
    tok = HeuristicTokenizer()
    text = "First sentence. Second sentence is long."
    out = tok.truncate_to_tokens(text, 3)
    assert "First" in out
