from decimal import Decimal
from uuid import uuid4

from app.auth import get_password_hash
from app.models import (
    DeliveryOrder,
    District,
    Driver,
    ItemType,
    OrderStatus,
    Region,
    Tariff,
    TaxiOrder,
    User,
    UserRole,
)


def _create_driver(db_session, tariff: Tariff):
    telephone = f"+998{uuid4().int % 1000000000:09d}"
    password = "DriverPass123"
    user = User(
        telephone=telephone,
        name=f"Driver {tariff.value}",
        hashed_password=get_password_hash(password),
        role=UserRole.DRIVER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    driver = Driver(
        user_id=user.id,
        full_name=f"Driver {tariff.value}",
        car_model="Chevrolet Cobalt",
        car_number=f"01A{uuid4().int % 900000 + 100000}BC",
        license_photo="/uploads/license.jpg",
        tariff=tariff,
        is_blocked=False,
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


def _seed_regions_districts(db_session):
    region = Region(
        name_uz_latin="Toshkent",
        name_uz_cyrillic="Тошкент",
        name_russian="Ташкент",
        is_active=True,
    )
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)

    from_district = District(
        region_id=region.id,
        name_uz_latin="Yunusobod",
        name_uz_cyrillic="Юнусобод",
        name_russian="Юнусабад",
        is_active=True,
    )
    to_district = District(
        region_id=region.id,
        name_uz_latin="Chilonzor",
        name_uz_cyrillic="Чилонзор",
        name_russian="Чиланзар",
        is_active=True,
    )
    db_session.add_all([from_district, to_district])
    db_session.commit()
    db_session.refresh(from_district)
    db_session.refresh(to_district)
    return region, from_district, to_district


def _seed_pending_orders(db_session, region, from_district, to_district):
    customer = User(
        telephone=f"+998{uuid4().int % 1000000000:09d}",
        name="Customer",
        hashed_password=get_password_hash("Customer123"),
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    taxi_orders = []
    for tariff in [Tariff.STANDARD, Tariff.COMFORT, Tariff.COMFORT_PLUS, Tariff.BUSINESS]:
        taxi_orders.append(
            TaxiOrder(
                user_id=customer.id,
                username="Customer",
                telephone=customer.telephone,
                from_region_id=region.id,
                from_district_id=from_district.id,
                to_region_id=region.id,
                to_district_id=to_district.id,
                passengers=1,
                tariff=tariff,
                date="20.02.2026",
                time_start="10:00",
                time_end="11:00",
                price=Decimal("30000.00"),
                status=OrderStatus.PENDING,
                public_order=True,
                is_confirmed=False,
            )
        )

    delivery_order = DeliveryOrder(
        user_id=customer.id,
        username="Customer",
        sender_telephone=customer.telephone,
        receiver_telephone="+998901234567",
        from_region_id=region.id,
        from_district_id=from_district.id,
        to_region_id=region.id,
        to_district_id=to_district.id,
        item_type=ItemType.DOCUMENT,
        date="20.02.2026",
        time_start="12:00",
        time_end="13:00",
        price=Decimal("20000.00"),
        status=OrderStatus.PENDING,
        public_order=True,
        is_confirmed=False,
    )
    db_session.add_all(taxi_orders + [delivery_order])
    db_session.commit()
    return taxi_orders, delivery_order


def test_driver_orders_new_filtered_by_tariff(client, db_session):
    region, from_district, to_district = _seed_regions_districts(db_session)
    _seed_pending_orders(db_session, region, from_district, to_district)

    cases = [
        (Tariff.STANDARD, {"standard"}),
        (Tariff.COMFORT, {"standard", "comfort"}),
        (Tariff.COMFORT_PLUS, {"standard", "comfort", "comfort_plus"}),
        (Tariff.BUSINESS, {"standard", "comfort", "comfort_plus", "business"}),
    ]

    for driver_tariff, expected_taxi_tariffs in cases:
        user, _, password = _create_driver(db_session, driver_tariff)
        token = _driver_token(client, user.telephone, password)
        response = client.get(
            "/api/driver/orders/new",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        actual_taxi_tariffs = {order["tariff"] for order in body["taxi_orders"]}
        assert actual_taxi_tariffs == expected_taxi_tariffs
        assert len(body["delivery_orders"]) == 1


def test_driver_cannot_accept_higher_tariff_taxi_order(client, db_session):
    region, from_district, to_district = _seed_regions_districts(db_session)
    taxi_orders, _ = _seed_pending_orders(db_session, region, from_district, to_district)
    business_order = next(order for order in taxi_orders if order.tariff == Tariff.BUSINESS)

    user, _, password = _create_driver(db_session, Tariff.STANDARD)
    token = _driver_token(client, user.telephone, password)

    response = client.post(
        f"/api/driver/orders/accept/taxi/{business_order.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Order is not visible to this driver"


def test_blocked_driver_cannot_view_new_orders(client, db_session):
    region, from_district, to_district = _seed_regions_districts(db_session)
    _seed_pending_orders(db_session, region, from_district, to_district)

    user, driver, password = _create_driver(db_session, Tariff.STANDARD)
    driver.is_blocked = True
    db_session.commit()

    token = _driver_token(client, user.telephone, password)
    response = client.get(
        "/api/driver/orders/new",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Blocked drivers cannot view new orders"
