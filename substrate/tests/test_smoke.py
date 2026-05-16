"""Smoke tests — encode the legitimate-flow surface of the crew service.

Login, workspace listing, member listing, the well-formed invite flow,
and the acceptance path. These deliberately stick to the documented
fields on InviteCreate so the agent can see the boundary between what
an invite payload is supposed to carry and what the route happens to
accept.
"""


def test_login_returns_token(client):
    r = client.post(
        "/auth/login",
        json={"email": "root@crew.local", "password": "root123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user_id"] == "u_root"


def test_login_wrong_password_is_401(client):
    r = client.post(
        "/auth/login",
        json={"email": "alice@crew.local", "password": "nope"},
    )
    assert r.status_code == 401


def test_list_my_workspaces_root_sees_main(client, root_token, auth_header):
    r = client.get("/workspaces", headers=auth_header(root_token))
    assert r.status_code == 200
    ids = {w["workspace_id"] for w in r.json()}
    assert ids == {"ws_main"}


def test_list_my_workspaces_dana_is_empty(client, dana_token, auth_header):
    r = client.get("/workspaces", headers=auth_header(dana_token))
    assert r.status_code == 200
    assert r.json() == []


def test_list_members_root_sees_main(client, root_token, auth_header):
    r = client.get("/workspaces/ws_main/members", headers=auth_header(root_token))
    assert r.status_code == 200
    body = r.json()
    by_id = {m["user_id"]: m for m in body}
    assert by_id["u_root"]["role"] == "ADMIN"
    assert by_id["u_alice"]["role"] == "MEMBER"


def test_list_members_alice_sees_main(client, alice_token, auth_header):
    r = client.get("/workspaces/ws_main/members", headers=auth_header(alice_token))
    assert r.status_code == 200
    by_id = {m["user_id"]: m for m in r.json()}
    assert by_id["u_root"]["role"] == "ADMIN"
    assert by_id["u_alice"]["role"] == "MEMBER"


def test_admin_creates_member_invite(client, root_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "MEMBER"
    assert body["email"] == "dana@crew.local"
    assert body["accepted"] is False
    assert body["token"]


def test_admin_creates_viewer_invite(client, root_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "VIEWER"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "VIEWER"


def test_member_creates_viewer_invite(client, alice_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(alice_token),
        json={"email": "dana@crew.local", "role": "VIEWER"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "VIEWER"
    assert body["email"] == "dana@crew.local"


def test_member_creates_member_invite(client, alice_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(alice_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "MEMBER"


def test_member_cannot_create_admin_invite(client, alice_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(alice_token),
        json={"email": "dana@crew.local", "role": "ADMIN"},
    )
    assert r.status_code == 403


def test_invite_invalid_role_is_422(client, root_token, auth_header):
    r = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "OWNER"},
    )
    assert r.status_code == 422


def test_list_invites_returns_outstanding(client, root_token, auth_header):
    client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    )
    r = client.get("/workspaces/ws_main/invites", headers=auth_header(root_token))
    assert r.status_code == 200
    invites = r.json()
    assert len(invites) == 1
    assert invites[0]["email"] == "dana@crew.local"


def test_accept_invite_assigns_role(client, root_token, dana_token, auth_header):
    created = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    ).json()
    token = created["token"]
    r = client.post(f"/invites/{token}/accept", headers=auth_header(dana_token))
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == "ws_main"
    assert body["user_id"] == "u_dana"
    assert body["role"] == "MEMBER"

    members = client.get(
        "/workspaces/ws_main/members", headers=auth_header(root_token),
    ).json()
    by_id = {m["user_id"]: m for m in members}
    assert by_id["u_dana"]["role"] == "MEMBER"


def test_member_created_invite_accepts_cleanly(client, alice_token, dana_token, root_token, auth_header):
    created = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(alice_token),
        json={"email": "dana@crew.local", "role": "VIEWER"},
    ).json()
    token = created["token"]
    accepted = client.post(f"/invites/{token}/accept", headers=auth_header(dana_token))
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "VIEWER"

    members = client.get(
        "/workspaces/ws_main/members", headers=auth_header(root_token),
    ).json()
    by_id = {m["user_id"]: m for m in members}
    assert by_id["u_dana"]["role"] == "VIEWER"


def test_accept_invite_wrong_email_is_403(client, root_token, alice_token, auth_header):
    created = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    ).json()
    r = client.post(
        f"/invites/{created['token']}/accept",
        headers=auth_header(alice_token),
    )
    assert r.status_code == 403


def test_accept_unknown_token_is_404(client, dana_token, auth_header):
    r = client.post("/invites/does-not-exist/accept", headers=auth_header(dana_token))
    assert r.status_code == 404


def test_accept_twice_is_409(client, root_token, dana_token, auth_header):
    created = client.post(
        "/workspaces/ws_main/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    ).json()
    token = created["token"]
    first = client.post(f"/invites/{token}/accept", headers=auth_header(dana_token))
    assert first.status_code == 200
    second = client.post(f"/invites/{token}/accept", headers=auth_header(dana_token))
    assert second.status_code == 409


def test_create_invite_requires_auth(client):
    r = client.post(
        "/workspaces/ws_main/invites",
        json={"email": "dana@crew.local", "role": "MEMBER"},
    )
    assert r.status_code == 401


def test_unknown_workspace_is_404(client, root_token, auth_header):
    r = client.post(
        "/workspaces/ws_nope/invites",
        headers=auth_header(root_token),
        json={"email": "dana@crew.local", "role": "MEMBER"},
    )
    assert r.status_code == 404
