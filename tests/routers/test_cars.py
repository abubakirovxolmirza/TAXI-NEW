from uuid import uuid4

from app.auth import get_password_hash
from app.models import User, UserRole


def _create_user(db_session, role: UserRole, password: str, name: str = "Test User"):
    user = User(
        telephone=f"+998{uuid4().int % 1000000000:09d}",
        name=name,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login_token(client, telephone: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"telephone": telephone, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_create_update_and_delete_car(client, db_session):
    admin_password = "AdminPass123"
    admin = _create_user(db_session, UserRole.ADMIN, admin_password, name="Admin User")
    admin_token = _login_token(client, admin.telephone, admin_password)

    create_response = client.post(
        "/api/cars/",
        json={"name": "Chevrolet Cobalt", "tariff": "vip_ultra_plus"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Chevrolet Cobalt"
    assert created["tariff"] == "vip_ultra_plus"

    car_id = created["id"]

    update_response = client.put(
        f"/api/cars/{car_id}",
        json={"tariff": "night_shift_special"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["tariff"] == "night_shift_special"

    delete_response = client.delete(
        f"/api/cars/{car_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True


def test_non_admin_cannot_create_car(client, db_session):
    user_password = "UserPass123"
    regular_user = _create_user(db_session, UserRole.USER, user_password, name="Regular User")
    user_token = _login_token(client, regular_user.telephone, user_password)

    response = client.post(
        "/api/cars/",
        json={"name": "Kia K5", "tariff": "comfort_sedan"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized. Admin access required."


def test_user_can_list_and_filter_cars(client, db_session):
    admin_password = "AdminPass123"
    user_password = "UserPass123"
    admin = _create_user(db_session, UserRole.ADMIN, admin_password, name="Admin User")
    regular_user = _create_user(db_session, UserRole.USER, user_password, name="Regular User")

    admin_token = _login_token(client, admin.telephone, admin_password)
    user_token = _login_token(client, regular_user.telephone, user_password)

    client.post(
        "/api/cars/",
        json={"name": "BYD Song Plus", "tariff": "electric_plus"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    client.post(
        "/api/cars/",
        json={"name": "Damas", "tariff": "economy"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    list_response = client.get(
        "/api/cars/?tariff=electric_plus",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert len(body) == 1
    assert body[0]["name"] == "BYD Song Plus"
    assert body[0]["tariff"] == "electric_plus"


def test_user_can_get_cars_by_tariff_path(client, db_session):
    admin_password = "AdminPass123"
    user_password = "UserPass123"
    admin = _create_user(db_session, UserRole.ADMIN, admin_password, name="Admin User")
    regular_user = _create_user(db_session, UserRole.USER, user_password, name="Regular User")

    admin_token = _login_token(client, admin.telephone, admin_password)
    user_token = _login_token(client, regular_user.telephone, user_password)

    client.post(
        "/api/cars/",
        json={"name": "Nexia 3", "tariff": "standard_plus"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    client.post(
        "/api/cars/",
        json={"name": "Malibu 2", "tariff": "business_pro"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.get(
        "/api/cars/tariff/standard_plus",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Nexia 3"
    assert body[0]["tariff"] == "standard_plus"
