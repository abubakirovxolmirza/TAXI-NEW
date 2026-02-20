from decimal import Decimal
from uuid import uuid4

from app.auth import get_password_hash
from app.models import BalanceTransaction, Driver, User, UserRole


def _create_driver_user(db_session, bonus_ball: Decimal, balance: Decimal):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    password = "DriverPass123"
    user = User(
        telephone=telephone,
        name="Driver Test",
        hashed_password=get_password_hash(password),
        role=UserRole.DRIVER,
        bonus_ball=bonus_ball,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    driver = Driver(
        user_id=user.id,
        full_name="Driver Test",
        car_model="Chevrolet Cobalt",
        car_number="01A123BC",
        license_photo="/uploads/license.jpg",
        balance=balance,
    )
    db_session.add(driver)
    db_session.commit()
    db_session.refresh(driver)
    return user, driver, password


def _driver_token(client, telephone: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"telephone": telephone, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_convert_bonus_to_balance_success(client, db_session):
    user, driver, password = _create_driver_user(
        db_session, bonus_ball=Decimal("50.00"), balance=Decimal("10.00")
    )
    token = _driver_token(client, user.telephone, password)

    response = client.post(
        "/api/driver/bonus/convert",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": "25.50"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["transferred_amount"] == "25.50"
    assert body["bonus_ball"] == "24.50"
    assert body["balance"] == "35.50"

    db_session.refresh(user)
    db_session.refresh(driver)
    assert user.bonus_ball == Decimal("24.50")
    assert driver.balance == Decimal("35.50")

    tx = db_session.query(BalanceTransaction).filter(BalanceTransaction.id == body["transaction_id"]).first()
    assert tx is not None
    assert tx.driver_id == driver.id
    assert tx.amount == Decimal("25.50")
    assert tx.transaction_type == "credit"


def test_convert_bonus_to_balance_rejects_if_amount_exceeds_bonus(client, db_session):
    user, _, password = _create_driver_user(
        db_session, bonus_ball=Decimal("10.00"), balance=Decimal("1.00")
    )
    token = _driver_token(client, user.telephone, password)

    response = client.post(
        "/api/driver/bonus/convert",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": "10.01"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Requested amount exceeds available bonus ball"
