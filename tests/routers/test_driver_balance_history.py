from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth import get_password_hash
from app.models import BalanceTransaction, Driver, User, UserRole


def _create_driver_with_token(client, db_session):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    password = "DriverPass123"
    user = User(
        telephone=telephone,
        name="Driver Balance User",
        hashed_password=get_password_hash(password),
        role=UserRole.DRIVER,
        bonus_ball=Decimal("100.00"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    driver = Driver(
        user_id=user.id,
        full_name="Driver Balance User",
        car_model="Chevrolet Cobalt",
        car_number="01A555BC",
        license_photo="/uploads/license.jpg",
        balance=Decimal("500.00"),
    )
    db_session.add(driver)
    db_session.commit()
    db_session.refresh(driver)

    login = client.post(
        "/api/auth/login",
        json={"telephone": telephone, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return user, driver, token


def test_driver_balance_history_includes_expected_sources(client, db_session):
    _, driver, token = _create_driver_with_token(client, db_session)

    admin = User(
        telephone=f"+998{uuid4().int % 1000000000:09d}",
        name="Admin Balance",
        hashed_password=get_password_hash("AdminPass123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    db_session.add_all(
        [
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("10000.00"),
                transaction_type="credit",
                description="Admin topup",
                admin_id=admin.id,
            ),
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("20000.00"),
                transaction_type="credit",
                description="Click topup via Click. click_trans_id=12345",
            ),
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("5000.00"),
                transaction_type="credit",
                description="Bonus ball converted to driver balance",
            ),
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("1200.00"),
                transaction_type="debit",
                description="Service fee for taxi order #10",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/driver/balance/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    sources = {item["source"] for item in body["transactions"]}
    assert "admin" in sources
    assert "click" in sources
    assert "bonus_convert" in sources
    assert "order_fee" in sources


def test_driver_balance_history_filter_by_source(client, db_session):
    _, driver, token = _create_driver_with_token(client, db_session)
    db_session.add_all(
        [
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("20000.00"),
                transaction_type="credit",
                description="Click topup via Click. click_trans_id=555",
            ),
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("8000.00"),
                transaction_type="credit",
                description="Bonus ball converted to driver balance",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/driver/balance/history?source=click",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["transactions"]) == 1
    assert body["transactions"][0]["source"] == "click"


def test_driver_balance_history_filter_by_day_period(client, db_session):
    _, driver, token = _create_driver_with_token(client, db_session)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("12000.00"),
                transaction_type="credit",
                description="Click topup via Click. click_trans_id=today",
                created_at=now,
            ),
            BalanceTransaction(
                driver_id=driver.id,
                amount=Decimal("9000.00"),
                transaction_type="credit",
                description="Click topup via Click. click_trans_id=old",
                created_at=now - timedelta(days=2),
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/driver/balance/history?period=day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["transactions"]) == 1
