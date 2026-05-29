from app.utils.ids import make_chunk_id


def test_chunk_id_is_deterministic():
    assert make_chunk_id("doc1", 2, 5) == "doc1_p2_c5"
