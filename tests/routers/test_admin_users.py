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


def test_admin_can_get_user_by_id(client, db_session):
    admin_password = "AdminPass123"
    admin = _create_user(db_session, UserRole.ADMIN, admin_password, name="Admin User")
    target = _create_user(db_session, UserRole.USER, "UserPass123", name="Target User")

    token = _login_token(client, admin.telephone, admin_password)
    response = client.get(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target.id
    assert body["name"] == "Target User"
    assert body["telephone"] == target.telephone


def test_admin_get_user_by_id_returns_404_for_missing_user(client, db_session):
    admin_password = "AdminPass123"
    admin = _create_user(db_session, UserRole.ADMIN, admin_password, name="Admin User")
    token = _login_token(client, admin.telephone, admin_password)

    response = client.get(
        "/api/admin/users/99999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_non_admin_cannot_get_user_by_id(client, db_session):
    user_password = "UserPass123"
    regular_user = _create_user(db_session, UserRole.USER, user_password, name="Regular User")
    target = _create_user(db_session, UserRole.USER, "TargetPass123", name="Target User")

    token = _login_token(client, regular_user.telephone, user_password)
    response = client.get(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized. Admin access required."
