from orbit_remote_mcp.auth.middleware import issue_session_token, verify_session_token


def test_session_tokens_roundtrip():
    secret = "test-secret"
    token = issue_session_token(secret, ttl_seconds=60)
    assert verify_session_token(token, secret)
