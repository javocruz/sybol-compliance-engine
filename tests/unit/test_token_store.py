from src.api.token_store import AuthSession, clear_session, create_store, load_session, save_session


def test_save_and_load_session():
    store = create_store()
    sid = save_session(
        store,
        AuthSession(
            access_token="access",
            id_token="header.payload.sig",
            email="user@ie.id",
        ),
    )

    loaded = load_session(store, sid)
    assert loaded is not None
    assert loaded.email == "user@ie.id"
    assert loaded.id_token == "header.payload.sig"


def test_clear_session():
    store = create_store()
    sid = save_session(
        store,
        AuthSession(access_token="a", id_token="b", email="user@ie.id"),
    )
    clear_session(store, sid)
    assert load_session(store, sid) is None
