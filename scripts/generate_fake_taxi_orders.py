#!/usr/bin/env python3
"""
Lightweight helper to seed the backend with fake taxi orders.

Usage:
  python scripts/generate_fake_taxi_orders.py --count 5 --base-url http://localhost:8000
  python scripts/generate_fake_taxi_orders.py --count 10 --token YOUR_JWT_TOKEN
  python scripts/generate_fake_taxi_orders.py --count 3 --login-phone +998901234567 --login-password secret

Notes:
- If no token/login is provided the script will create guest orders (backend supports this).
- Regions and districts are pulled from the backend so IDs always match the database.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib import error, request


def _http_json(
    url: str,
    method: str = "GET",
    payload: Optional[dict] = None,
    token: Optional[str] = None,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except error.HTTPError as exc:
        try:
            detail = exc.read().decode()
        except Exception:
            detail = ""
        raise RuntimeError(
            f"HTTP {exc.code} {exc.reason} for {url}: {detail}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


def _login(base_url: str, phone: str, password: str) -> str:
    url = f"{base_url}/api/auth/login"
    payload = {"telephone": phone, "password": password}
    resp = _http_json(url, method="POST", payload=payload)
    token = resp.get("access_token") or resp.get("token")
    if not token:
        raise RuntimeError("Login succeeded but no token returned.")
    return str(token)


def _fetch_regions(base_url: str) -> List[dict]:
    url = f"{base_url}/api/regions/"
    resp = _http_json(url)
    if not isinstance(resp, list):
        raise RuntimeError("Unexpected regions payload; expected list.")
    return resp


def _pick_route(regions: List[dict]) -> Tuple[dict, dict]:
    if len(regions) < 2:
        raise RuntimeError("Need at least two regions to generate routes.")
    src, dst = random.sample(regions, 2)
    return src, dst


def _pick_district(region: dict) -> dict:
    districts = region.get("districts") or []
    if not districts:
        raise RuntimeError(f"Region {region.get('id')} has no districts.")
    return random.choice(districts)


def _random_phone() -> str:
    return "+998" + "".join(str(random.randint(0, 9)) for _ in range(9))


def _random_name() -> str:
    first = random.choice(
        ["Ali", "Jasur", "Sarvar", "Otabek", "Javohir", "Malika", "Dilnoza"]
    )
    last = random.choice(
        ["Karimov", "Abdullayev", "Rustamov", "Tursunov", "Ismoilova", "Rahimova"]
    )
    return f"{first} {last}"


def _time_window() -> Tuple[datetime, datetime]:
    start = datetime.now(timezone.utc) + timedelta(minutes=random.randint(10, 90))
    end = start + timedelta(minutes=random.randint(15, 45))
    return start, end


def _build_order_payload(regions: List[dict]) -> dict:
    src_region, dst_region = _pick_route(regions)
    src_district = _pick_district(src_region)
    dst_district = _pick_district(dst_region)
    start, end = _time_window()

    return {
        "username": _random_name(),
        "telephone": _random_phone(),
        "from_region_id": src_region["id"],
        "from_district_id": src_district["id"],
        "to_region_id": dst_region["id"],
        "to_district_id": dst_district["id"],
        "pickup_latitude": f"{random.uniform(41.0, 42.5):.6f}",
        "pickup_longitude": f"{random.uniform(69.0, 73.0):.6f}",
        "pickup_address": f"{src_district.get('name_uz_latin', 'Street')} {random.randint(1, 200)}",
        "passengers": random.randint(1, 4),
        "is_mail_delivery": random.choice([False, False, True]),
        "date": start.strftime("%d.%m.%Y"),
        "time_start": start.strftime("%H:%M"),
        "time_end": end.strftime("%H:%M"),
        "scheduled_datetime": start.isoformat(),
        "note": random.choice(
            [
                "Please call on arrival",
                "I have luggage",
                "Need a child seat",
                "In a hurry",
                "",
            ]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate fake taxi orders against the running backend."
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL, e.g. http://localhost:8000")
    parser.add_argument("--count", type=int, default=5, help="How many orders to create")
    parser.add_argument("--token", help="Bearer token to use (optional)")
    parser.add_argument("--login-phone", help="Login phone; if provided, will fetch token")
    parser.add_argument("--login-password", help="Login password; used with --login-phone")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = args.token

    if not token and args.login_phone and args.login_password:
        print("Logging in to fetch token...")
        token = _login(base_url, args.login_phone, args.login_password)
        print("Authenticated.")

    try:
        regions = _fetch_regions(base_url)
    except Exception as exc:  # pragma: no cover - CLI helper
        print(f"Failed to fetch regions: {exc}")
        return 1

    created = 0
    for idx in range(args.count):
        payload = _build_order_payload(regions)
        try:
            resp = _http_json(
                f"{base_url}/api/taxi-orders/",
                method="POST",
                payload=payload,
                token=token,
            )
            order_id = resp.get("id")
            created += 1
            print(f"[{idx+1}/{args.count}] Created order #{order_id or '?'} from {payload['from_region_id']} to {payload['to_region_id']}")
        except Exception as exc:  # pragma: no cover - CLI helper
            print(f"[{idx+1}/{args.count}] Failed: {exc}")

    print(f"Done. Created {created}/{args.count} orders.")
    return 0 if created == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
