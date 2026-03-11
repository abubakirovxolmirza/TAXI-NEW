"""
Delete users created in a specific datetime range.

Default target ranges:
  1) 2025-12-28T06:45:15.870355Z -> 2025-12-28T07:45:41.737612Z
  2) 2026-03-04T03:24:18.880519Z -> 2026-03-04T03:32:27.152208Z

Examples:
  python3 scripts/delete_users_by_created_date.py
  python3 scripts/delete_users_by_created_date.py --from 2025-12-28T06:45:15.870355Z --to 2025-12-28T07:45:41.737612Z --yes
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import and_, or_

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    User,
    Driver,
    Permission,
    TaxiOrder,
    DeliveryOrder,
    Rating,
    DriverApplication,
    BalanceTransaction,
    Notification,
    DeviceToken,
    DriverPhotoControl,
    Feedback,
    SystemSettings,
    OrderAcceptanceHistory,
    UserRole,
)

DEFAULT_RANGES = [
    ("2025-12-28T06:45:15.870355Z", "2025-12-28T07:45:41.737612Z"),
    ("2026-03-04T03:24:18.880519Z", "2026-03-04T03:32:27.152208Z"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete NON-DRIVER users created in datetime range(s) (ISO 8601)."
    )
    parser.add_argument(
        "--from",
        dest="from_dt",
        default=None,
        help="Start datetime, inclusive. If omitted, built-in default ranges are used.",
    )
    parser.add_argument(
        "--to",
        dest="to_dt",
        default=None,
        help="End datetime, inclusive. Must be used together with --from.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually perform deletion. Without this flag, script runs in dry-run mode.",
    )
    return parser.parse_args()


def parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def main() -> None:
    args = parse_args()

    ranges = []
    if args.from_dt or args.to_dt:
        if not args.from_dt or not args.to_dt:
            print("Both --from and --to are required when overriding default ranges.")
            sys.exit(1)
        raw_ranges = [(args.from_dt, args.to_dt)]
    else:
        raw_ranges = DEFAULT_RANGES

    for raw_from, raw_to in raw_ranges:
        try:
            from_dt = parse_iso_datetime(raw_from)
            to_dt = parse_iso_datetime(raw_to)
        except ValueError:
            print(
                f"Invalid datetime format in range: {raw_from} -> {raw_to}. "
                "Use ISO 8601 (example: 2025-12-28T06:45:15.870355Z)"
            )
            sys.exit(1)
        if from_dt > to_dt:
            print(f"Invalid range: {raw_from} -> {raw_to} (from > to)")
            sys.exit(1)
        ranges.append((from_dt, to_dt))

    db = SessionLocal()
    try:
        time_conditions = [
            and_(User.created_at >= from_dt, User.created_at <= to_dt)
            for from_dt, to_dt in ranges
        ]
        users = (
            db.query(User)
            .filter(or_(*time_conditions))
            .filter(User.role != UserRole.DRIVER)
            .order_by(User.id.asc())
            .all()
        )
        user_ids = [u.id for u in users]

        print("=" * 72)
        print("Target ranges (inclusive):")
        for from_dt, to_dt in ranges:
            print(f"  - {from_dt.isoformat()} -> {to_dt.isoformat()}")
        print("Role filter: excluding DRIVER users")
        print(f"Matched non-driver users: {len(users)}")
        print("=" * 72)

        for u in users[:30]:
            print(
                f"id={u.id}, telephone={u.telephone}, name={u.name}, "
                f"role={u.role.value}, created_at={u.created_at}"
            )
        if len(users) > 30:
            print(f"... and {len(users) - 30} more")

        if not user_ids:
            print("No users found. Nothing to delete.")
            return

        if not args.yes:
            print("\nDry-run only. No data was changed.")
            print("Run with --yes to execute deletion.")
            return

        driver_ids = [
            row[0]
            for row in db.query(Driver.id).filter(Driver.user_id.in_(user_ids)).all()
        ]

        taxi_order_ids = [
            row[0]
            for row in db.query(TaxiOrder.id).filter(TaxiOrder.user_id.in_(user_ids)).all()
        ]
        delivery_order_ids = [
            row[0]
            for row in db.query(DeliveryOrder.id)
            .filter(DeliveryOrder.user_id.in_(user_ids))
            .all()
        ]

        deleted = {}
        updated = {}

        # Nullify optional references to target users in records we keep.
        updated["taxi_orders.bonus_user_id"] = (
            db.query(TaxiOrder)
            .filter(TaxiOrder.bonus_user_id.in_(user_ids))
            .update({TaxiOrder.bonus_user_id: None}, synchronize_session=False)
        )
        updated["taxi_orders.cancelled_by_user_id"] = (
            db.query(TaxiOrder)
            .filter(TaxiOrder.cancelled_by_user_id.in_(user_ids))
            .update({TaxiOrder.cancelled_by_user_id: None}, synchronize_session=False)
        )
        updated["delivery_orders.bonus_user_id"] = (
            db.query(DeliveryOrder)
            .filter(DeliveryOrder.bonus_user_id.in_(user_ids))
            .update({DeliveryOrder.bonus_user_id: None}, synchronize_session=False)
        )
        updated["delivery_orders.cancelled_by_user_id"] = (
            db.query(DeliveryOrder)
            .filter(DeliveryOrder.cancelled_by_user_id.in_(user_ids))
            .update({DeliveryOrder.cancelled_by_user_id: None}, synchronize_session=False)
        )
        updated["driver_applications.reviewed_by"] = (
            db.query(DriverApplication)
            .filter(DriverApplication.reviewed_by.in_(user_ids))
            .update({DriverApplication.reviewed_by: None}, synchronize_session=False)
        )
        updated["balance_transactions.admin_id"] = (
            db.query(BalanceTransaction)
            .filter(BalanceTransaction.admin_id.in_(user_ids))
            .update({BalanceTransaction.admin_id: None}, synchronize_session=False)
        )
        updated["system_settings.updated_by"] = (
            db.query(SystemSettings)
            .filter(SystemSettings.updated_by.in_(user_ids))
            .update({SystemSettings.updated_by: None}, synchronize_session=False)
        )

        # If targeted users have driver profiles, detach kept orders from these drivers.
        if driver_ids:
            updated["taxi_orders.driver_id"] = (
                db.query(TaxiOrder)
                .filter(TaxiOrder.driver_id.in_(driver_ids))
                .update({TaxiOrder.driver_id: None}, synchronize_session=False)
            )
            updated["delivery_orders.driver_id"] = (
                db.query(DeliveryOrder)
                .filter(DeliveryOrder.driver_id.in_(driver_ids))
                .update({DeliveryOrder.driver_id: None}, synchronize_session=False)
            )

        # Delete dependent rows.
        oah_conditions = []
        rating_conditions = []
        if driver_ids:
            oah_conditions.append(OrderAcceptanceHistory.driver_id.in_(driver_ids))
            rating_conditions.append(Rating.driver_id.in_(driver_ids))
        if taxi_order_ids:
            oah_conditions.append(OrderAcceptanceHistory.taxi_order_id.in_(taxi_order_ids))
            rating_conditions.append(Rating.taxi_order_id.in_(taxi_order_ids))
        if delivery_order_ids:
            oah_conditions.append(OrderAcceptanceHistory.delivery_order_id.in_(delivery_order_ids))
            rating_conditions.append(Rating.delivery_order_id.in_(delivery_order_ids))

        deleted["order_acceptance_history"] = (
            db.query(OrderAcceptanceHistory)
            .filter(or_(*oah_conditions))
            .delete(synchronize_session=False)
        ) if oah_conditions else 0
        deleted["ratings"] = (
            db.query(Rating)
            .filter(
                or_(Rating.user_id.in_(user_ids), *rating_conditions)
            )
            .delete(synchronize_session=False)
        )
        deleted["notifications_by_user"] = (
            db.query(Notification)
            .filter(Notification.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        if driver_ids:
            deleted["notifications_by_driver"] = (
                db.query(Notification)
                .filter(Notification.driver_id.in_(driver_ids))
                .delete(synchronize_session=False)
            )
        deleted["feedback"] = (
            db.query(Feedback)
            .filter(Feedback.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        deleted["device_tokens"] = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        deleted["permissions"] = (
            db.query(Permission)
            .filter(Permission.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        deleted["driver_applications"] = (
            db.query(DriverApplication)
            .filter(DriverApplication.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        deleted["taxi_orders"] = (
            db.query(TaxiOrder)
            .filter(TaxiOrder.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        deleted["delivery_orders"] = (
            db.query(DeliveryOrder)
            .filter(DeliveryOrder.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        if driver_ids:
            deleted["balance_transactions_by_driver"] = (
                db.query(BalanceTransaction)
                .filter(BalanceTransaction.driver_id.in_(driver_ids))
                .delete(synchronize_session=False)
            )
            deleted["driver_photo_controls"] = (
                db.query(DriverPhotoControl)
                .filter(DriverPhotoControl.driver_id.in_(driver_ids))
                .delete(synchronize_session=False)
            )
            deleted["drivers"] = (
                db.query(Driver)
                .filter(Driver.user_id.in_(user_ids))
                .delete(synchronize_session=False)
            )

        deleted["users"] = (
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        )

        db.commit()

        print("\nDeletion completed.")
        print("-" * 72)
        print("Updated rows:")
        for k, v in updated.items():
            print(f"  {k}: {v}")
        print("\nDeleted rows:")
        for k, v in deleted.items():
            print(f"  {k}: {v}")

    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
