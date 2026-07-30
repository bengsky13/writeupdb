from app.search.query_parser import parse_query


def test_parse_query_maps_aliases_and_constraints() -> None:
    parsed = parse_query("ret2libc 32 bit no leak")
    assert parsed["category"] == "pwn"
    assert "return to libc" in parsed["techniques"]
    assert "i386" in parsed["architectures"]
    assert "no information leak" in parsed["constraints"]

