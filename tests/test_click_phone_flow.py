import os
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import get_async_db
from app.database import Base
from app.models import Driver, TopUpStatus, TopUpTransaction, User, UserRole
from main import app


CLICK_TEST_DB_URL = os.getenv("CLICK_TEST_DB_URL")


@pytest.mark.skipif(
    not CLICK_TEST_DB_URL or not CLICK_TEST_DB_URL.startswith("postgresql"),
    reason="CLICK_TEST_DB_URL (postgresql) required for integration tests",
)
@pytest.mark.asyncio
async def test_click_prepare_and_complete_flow():
    settings.click_disable_sign_check = True
    settings.click_service_id = 94101

    engine = create_async_engine(CLICK_TEST_DB_URL, pool_pre_ping=True, future=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_async_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_async_db] = _override_get_async_db

    async with async_session() as session:
        user = User(
            telephone="+998901234567",
            name="Test",
            hashed_password="x",
            role=UserRole.DRIVER,
        )
        session.add(user)
        await session.flush()
        driver = Driver(
            user_id=user.id,
            full_name="Driver",
            car_model="Test",
            car_number="01A000AA",
            license_photo="x",
            balance=Decimal("0.00"),
        )
        session.add(driver)
        await session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        prepare_payload = {
            "click_trans_id": "test_click_100",
            "service_id": 94101,
            "transaction_param": "+998901234567",
            "amount": 1000,
            "action": 0,
            "sign_time": "2026-02-03 10:00:00",
            "sign_string": "TEST",
        }
        prepare_resp = await client.post("/click/prepare", json=prepare_payload)
        assert prepare_resp.status_code == 200
        prepare_data = prepare_resp.json()
        assert prepare_data["error"] == 0
        merchant_prepare_id = prepare_data["merchant_prepare_id"]

        # idempotent prepare
        prepare_resp2 = await client.post("/click/prepare", json=prepare_payload)
        assert prepare_resp2.status_code == 200
        assert prepare_resp2.json()["merchant_prepare_id"] == merchant_prepare_id

        complete_payload = {
            "click_trans_id": "test_click_100",
            "service_id": 94101,
            "transaction_param": "+998901234567",
            "merchant_prepare_id": merchant_prepare_id,
            "amount": 1000,
            "action": 1,
            "error": 0,
            "sign_time": "2026-02-03 10:00:05",
            "sign_string": "TEST",
        }
        complete_resp = await client.post("/click/complete", json=complete_payload)
        assert complete_resp.status_code == 200
        assert complete_resp.json()["error"] == 0

        # idempotent complete
        complete_resp2 = await client.post("/click/complete", json=complete_payload)
        assert complete_resp2.status_code == 200
        assert complete_resp2.json()["error"] == 0

    async with async_session() as session:
        result = await session.execute(
            select(TopUpTransaction).where(TopUpTransaction.click_trans_id == "test_click_100")
        )
        topup = result.scalar_one()
        assert topup.status == TopUpStatus.PAID
        result = await session.execute(select(Driver).where(Driver.id == driver.id))
        driver_row = result.scalar_one()
        assert driver_row.balance == Decimal("1000.00")

    app.dependency_overrides.pop(get_async_db, None)

    await engine.dispose()


@pytest.mark.skipif(
    not CLICK_TEST_DB_URL or not CLICK_TEST_DB_URL.startswith("postgresql"),
    reason="CLICK_TEST_DB_URL (postgresql) required for integration tests",
)
@pytest.mark.asyncio
async def test_click_prepare_driver_not_found():
    settings.click_disable_sign_check = True
    settings.click_service_id = 94101

    engine = create_async_engine(CLICK_TEST_DB_URL, pool_pre_ping=True, future=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_async_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_async_db] = _override_get_async_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "click_trans_id": "test_click_missing_driver",
            "service_id": 94101,
            "transaction_param": "+998991112233",
            "amount": 1000,
            "action": 0,
            "sign_time": "2026-02-03 11:00:00",
            "sign_string": "TEST",
        }
        resp = await client.post("/click/prepare", json=payload)
        assert resp.status_code == 200
        assert resp.json()["error"] == -3

    app.dependency_overrides.pop(get_async_db, None)
    await engine.dispose()
