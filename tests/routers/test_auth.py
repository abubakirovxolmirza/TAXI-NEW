from uuid import uuid4


def _register_user(client, telephone: str, password: str, name: str = "Test User"):
    payload = {
        "telephone": telephone,
        "name": name,
        "password": password,
        "confirm_password": password,
    }
    return client.post("/api/auth/register", json=payload)


def test_register(client):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    response = _register_user(client, telephone, "StrongPass1", name="Alice")

    assert response.status_code == 201
    body = response.json()
    assert body["telephone"] == telephone
    assert body["name"] == "Alice"
    assert body["is_active"] is True


def test_register_existing_user(client):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    first = _register_user(client, telephone, "Password1!")
    assert first.status_code == 201

    second = _register_user(client, telephone, "Password1!")
    assert second.status_code == 400


def test_login(client):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    password = "VerySecret123"
    register_response = _register_user(client, telephone, password)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"telephone": telephone, "password": password},
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert "access_token" in login_body
    assert login_body["token_type"] == "bearer"
    assert login_body["user"]["telephone"] == telephone


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={"telephone": "+998000000000", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_sms_verify_test_phone_returns_token_without_otp_record(client):
    response = client.post(
        "/api/auth/sms/verify-code",
        json={"telephone": "+998935204050", "code": "123321"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["telephone"] == "+998935204050"
