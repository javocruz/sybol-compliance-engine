from src.credentials.auth_tokens import is_valid_jwt, normalize_token


def test_normalize_token_strips_whitespace():
    assert normalize_token("  abc  ") == "abc"
    assert normalize_token("") is None
    assert normalize_token(None) is None


def test_is_valid_jwt():
    assert is_valid_jwt("aaa.bbb.ccc") is True
    assert is_valid_jwt("not-a-jwt") is False
    assert is_valid_jwt("only.two") is False
    assert is_valid_jwt(None) is False
