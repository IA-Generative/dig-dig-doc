import importlib


def test_client_sends_app_token_header(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://backend:8000")
    monkeypatch.setenv("INTERNAL_WORKER_TOKEN", "test-token")
    from app import api_client, config

    importlib.reload(config)
    importlib.reload(api_client)
    client = api_client.get_client()
    try:
        assert str(client.base_url) == "http://backend:8000/api/internal/"
        assert client.headers["x-app-token"] == "test-token"
    finally:
        client.close()


def test_client_falls_back_to_localhost(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_INTERNAL_URL", raising=False)
    monkeypatch.delenv("INTERNAL_WORKER_TOKEN", raising=False)
    from app import api_client, config

    importlib.reload(config)
    importlib.reload(api_client)
    assert config.settings.BACKEND_INTERNAL_URL == "http://localhost:8000"
    assert config.settings.INTERNAL_WORKER_TOKEN == ""


def test_act_for_sends_the_acting_person_on_every_following_call(monkeypatch) -> None:
    """L'agent assistant agit au nom d'une personne (issue #222) : l'en-tête part avec tous les appels du client."""
    monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://backend:8000")
    monkeypatch.setenv("INTERNAL_WORKER_TOKEN", "test-token")
    from app import api_client, config

    importlib.reload(config)
    importlib.reload(api_client)
    client = api_client.get_client()
    try:
        api_client.act_for(client, "alice-sub")

        assert client.headers["x-acting-user"] == "alice-sub"
        assert client.headers["x-app-token"] == "test-token"  # le jeton du worker reste là
    finally:
        client.close()
