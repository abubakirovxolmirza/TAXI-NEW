from decimal import Decimal

from app.models import Pricing, Region, SystemSettings
from app.utils import calculate_delivery_price, calculate_service_fee, calculate_taxi_price


def _create_region(db_session, name_suffix: str) -> Region:
    region = Region(
        name_uz_latin=f"Region {name_suffix} UZ",
        name_uz_cyrillic=f"Region {name_suffix} UZC",
        name_russian=f"Region {name_suffix} RU",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()
    return region


def _reset_service_fee_percentage(db_session) -> None:
    db_session.query(SystemSettings).filter(
        SystemSettings.setting_key == "service_fee_percentage"
    ).delete()
    db_session.commit()


def test_calculate_taxi_price_scales_with_passengers(db_session):
    region_a = _create_region(db_session, "A")
    region_b = _create_region(db_session, "B")

    pricing = Pricing(
        from_region_id=region_a.id,
        to_region_id=region_b.id,
        service_type="taxi",
        base_price=Decimal("50000.00"),
        discount_1_passenger=Decimal("5.00"),
        discount_2_passengers=Decimal("10.00"),
        discount_3_passengers=Decimal("15.00"),
        discount_full_car=Decimal("20.00"),
        is_active=True,
    )
    db_session.add(pricing)
    db_session.commit()

    _reset_service_fee_percentage(db_session)

    price = calculate_taxi_price(db_session, region_a.id, region_b.id, passengers=2)
    assert price == Decimal("90000.00")

    service_fee, driver_earnings = calculate_service_fee(price, db_session)
    assert service_fee == Decimal("9000.00")
    assert driver_earnings == Decimal("81000.00")


def test_calculate_taxi_price_fallback_respects_passengers(db_session):
    _reset_service_fee_percentage(db_session)
    price = calculate_taxi_price(db_session, 999, 1000, passengers=3)
    assert price == Decimal("150000.00")


def test_calculate_service_fee_rounding(db_session):
    _reset_service_fee_percentage(db_session)

    db_session.add(
        SystemSettings(
            setting_key="service_fee_percentage",
            setting_value="7.5",
        )
    )
    db_session.commit()

    price = Decimal("10001.00")
    service_fee, driver_earnings = calculate_service_fee(price, db_session)
    assert service_fee == Decimal("750.08")
    assert driver_earnings == Decimal("9250.92")

    _reset_service_fee_percentage(db_session)


def test_calculate_delivery_price_rounding(db_session):
    region_a = _create_region(db_session, "C")
    region_b = _create_region(db_session, "D")

    pricing = Pricing(
        from_region_id=region_a.id,
        to_region_id=region_b.id,
        service_type="delivery",
        base_price=Decimal("12345.67"),
        is_active=True,
    )
    db_session.add(pricing)
    db_session.commit()

    _reset_service_fee_percentage(db_session)

    price = calculate_delivery_price(db_session, region_a.id, region_b.id)
    assert price == Decimal("12345.67")
