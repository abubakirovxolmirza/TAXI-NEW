#!/usr/bin/env python3
"""
Seed taxi pricing for all region-to-region and district-to-district routes.

Tariffs and base prices used:
- standard: 130000
- comfort: 140000
- comfort_plus: 170000
- business: 800000

By default the script updates/creates BOTH:
- region-level pricing (pricing table)
- district-level pricing (district_pricing table)

Examples:
  python scripts/seed_taxi_pricing_all_routes.py
  python scripts/seed_taxi_pricing_all_routes.py --regions-only
  python scripts/seed_taxi_pricing_all_routes.py --districts-only
"""

import argparse
import os
import sys
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

# Add project root to import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import District, DistrictPricing, Pricing, Region, Tariff


TARIFF_PRICES: Dict[Tariff, Decimal] = {
    Tariff.STANDARD: Decimal("130000.00"),
    Tariff.COMFORT: Decimal("140000.00"),
    Tariff.COMFORT_PLUS: Decimal("170000.00"),
    Tariff.BUSINESS: Decimal("800000.00"),
}


def _seat_prices_for_tariff(
    tariff: Tariff, base_price: Decimal
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    if tariff == Tariff.STANDARD:
        # Standard: front seat is base + 15000, back seat equals base.
        return base_price + Decimal("20000.00"), base_price
    return None, None


def _region_pairs(regions: List[Region]) -> Iterable[Tuple[int, int]]:
    for src in regions:
        for dst in regions:
            if src.id != dst.id:
                yield src.id, dst.id


def _district_pairs(districts: List[District]) -> Iterable[Tuple[int, int]]:
    for src in districts:
        for dst in districts:
            if src.id != dst.id:
                yield src.id, dst.id


def _key(from_id: int, to_id: int, tariff: Tariff) -> Tuple[int, int, str]:
    return from_id, to_id, tariff.value


def seed_region_pricing(db) -> Tuple[int, int, int]:
    regions = db.query(Region).filter(Region.is_active.is_(True)).all()
    if len(regions) < 2:
        return 0, 0, 0

    existing = db.query(Pricing).filter(Pricing.service_type == "taxi").all()
    existing_index: Dict[Tuple[int, int, str], Pricing] = {}
    duplicates = 0

    for row in existing:
        k = _key(row.from_region_id, row.to_region_id, row.tariff)
        if k in existing_index:
            duplicates += 1
            continue
        existing_index[k] = row

    created = 0
    updated = 0

    for from_region_id, to_region_id in _region_pairs(regions):
        for tariff, base_price in TARIFF_PRICES.items():
            k = _key(from_region_id, to_region_id, tariff)
            row = existing_index.get(k)

            if row:
                row.base_price = base_price
                front_seat_price, back_seat_price = _seat_prices_for_tariff(tariff, base_price)
                row.front_seat_price = front_seat_price
                row.back_seat_price = back_seat_price
                row.is_active = True
                updated += 1
            else:
                front_seat_price, back_seat_price = _seat_prices_for_tariff(tariff, base_price)
                db.add(
                    Pricing(
                        from_region_id=from_region_id,
                        to_region_id=to_region_id,
                        service_type="taxi",
                        tariff=tariff,
                        base_price=base_price,
                        front_seat_price=front_seat_price,
                        back_seat_price=back_seat_price,
                        is_active=True,
                    )
                )
                created += 1

    return created, updated, duplicates


def seed_district_pricing(db) -> Tuple[int, int, int]:
    districts = db.query(District).filter(District.is_active.is_(True)).all()
    if len(districts) < 2:
        return 0, 0, 0

    existing = db.query(DistrictPricing).filter(DistrictPricing.service_type == "taxi").all()
    existing_index: Dict[Tuple[int, int, str], DistrictPricing] = {}
    duplicates = 0

    for row in existing:
        k = _key(row.from_district_id, row.to_district_id, row.tariff)
        if k in existing_index:
            duplicates += 1
            continue
        existing_index[k] = row

    created = 0
    updated = 0

    for from_district_id, to_district_id in _district_pairs(districts):
        for tariff, base_price in TARIFF_PRICES.items():
            k = _key(from_district_id, to_district_id, tariff)
            row = existing_index.get(k)

            if row:
                row.base_price = base_price
                front_seat_price, back_seat_price = _seat_prices_for_tariff(tariff, base_price)
                row.front_seat_price = front_seat_price
                row.back_seat_price = back_seat_price
                row.is_active = True
                updated += 1
            else:
                front_seat_price, back_seat_price = _seat_prices_for_tariff(tariff, base_price)
                db.add(
                    DistrictPricing(
                        from_district_id=from_district_id,
                        to_district_id=to_district_id,
                        service_type="taxi",
                        tariff=tariff,
                        base_price=base_price,
                        front_seat_price=front_seat_price,
                        back_seat_price=back_seat_price,
                        is_active=True,
                    )
                )
                created += 1

    return created, updated, duplicates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed taxi pricing for all region and district routes."
    )
    parser.add_argument(
        "--regions-only",
        action="store_true",
        help="Only seed region-level pricing (pricing table).",
    )
    parser.add_argument(
        "--districts-only",
        action="store_true",
        help="Only seed district-level pricing (district_pricing table).",
    )
    args = parser.parse_args()

    if args.regions_only and args.districts_only:
        print("Error: use only one of --regions-only or --districts-only")
        return 1

    run_regions = not args.districts_only
    run_districts = not args.regions_only

    db = SessionLocal()
    try:
        region_created = region_updated = region_duplicates = 0
        district_created = district_updated = district_duplicates = 0

        if run_regions:
            (
                region_created,
                region_updated,
                region_duplicates,
            ) = seed_region_pricing(db)

        if run_districts:
            (
                district_created,
                district_updated,
                district_duplicates,
            ) = seed_district_pricing(db)

        db.commit()

        print("Taxi pricing seed completed.")
        if run_regions:
            print(
                f"Region pricing -> created: {region_created}, "
                f"updated: {region_updated}, duplicate_keys_skipped: {region_duplicates}"
            )
        if run_districts:
            print(
                f"District pricing -> created: {district_created}, "
                f"updated: {district_updated}, duplicate_keys_skipped: {district_duplicates}"
            )

        print("Applied tariff prices:")
        for tariff, price in TARIFF_PRICES.items():
            print(f"- {tariff.value}: {price}")

        return 0
    except Exception as exc:
        db.rollback()
        print(f"Failed to seed taxi pricing: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
