"""Aides partagées des tests d'accès aux dossiers (issue #177) : personnes, « agir en tant que », fixtures."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security.factory import RequestContext, get_current_user
from app.main import app


def _person(label: str, groups: list[str], *, admin: bool = False) -> RequestContext:
    suffix = uuid.uuid4().hex[:8]
    return RequestContext(
        user_id=f"acc-{label}-{suffix}",
        email=f"{label}{suffix}@example.org",
        roles=["admin"] if admin else [],
        is_admin=admin,
        first_name=label,
        last_name=suffix,
        groups=groups,
    )


class As:
    """Exécute des appels « en tant que » une personne, puis revient à la précédente."""

    def __init__(self, person: RequestContext):
        self.person = person

    def __enter__(self):
        self.previous = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: self.person
        return self.person

    def __exit__(self, *exc):
        if self.previous is None:
            del app.dependency_overrides[get_current_user]
        else:
            app.dependency_overrides[get_current_user] = self.previous


@pytest.fixture
def world(client: TestClient) -> dict:
    """Quatre personnes connues de l'annuaire, groupes distincts : /a, /b, /a et /b, et un administrateur."""
    group_a, group_b = f"/a-{uuid.uuid4().hex[:6]}", f"/b-{uuid.uuid4().hex[:6]}"
    people = {
        "alice": _person("alice", [group_a]),
        "bob": _person("bob", [group_b]),
        "carol": _person("carol", [group_a, group_b]),
        "root": _person("root", [group_a, f"/ops-{uuid.uuid4().hex[:6]}"], admin=True),
    }
    for person in people.values():
        with As(person):
            client.get("/api/auth/me")
    return {**people, "a": group_a, "b": group_b}


@pytest.fixture
def analyse(client: TestClient) -> dict:
    created = client.post("/api/analyses", json={"name": f"Accès {uuid.uuid4().hex[:6]}", "description": "T"}).json()
    return client.get(f"/api/analyses/{created['id']}").json()
