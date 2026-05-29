from app.ingestion.parser import PDFParser


def test_parser_normalize_text_cleans_common_mojibake():
    raw = "Harshita Bogineni \u00c2\u00a7 Github \u00c3\u00af LinkedIn \u00e2\u20ac\u00a2 Education"
    cleaned = PDFParser._normalize_text(raw)
    assert "\u00c2" not in cleaned
    assert "\u00c3\u00af" not in cleaned
    assert "\u00e2\u20ac\u00a2" not in cleaned
    assert "Github" in cleaned
    assert "Education" in cleaned
