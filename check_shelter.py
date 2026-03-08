from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from datetime import timedelta

from sqlalchemy.exc import OperationalError

from db.models import GuestBooking
from db.session import SessionLocal
from services.guest_context import get_local_now, get_local_today
from services.shelter import ShelterAPIError, get_shelter_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def print_booking_row(prefix: str, booking: GuestBooking) -> None:
    print(
        f"{prefix} id={booking.id} tg={booking.telegram_id} room={booking.room_number} "
        f"stay={booking.check_in_date}..{booking.check_out_date} "
        f"active={booking.is_active} "
        f"checkin_notified={getattr(booking, 'checkin_notified', 'n/a')} "
        f"checkout_notified={getattr(booking, 'checkout_notified', 'n/a')}"
    )


def describe_error(exc: BaseException) -> str:
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message.strip():
        return message.strip()
    return str(exc).strip() or repr(exc)


async def run_shelter_checks() -> bool:
    print_section("Shelter API")
    today = get_local_today()
    tomorrow = today + timedelta(days=1)
    shelter = get_shelter_client()
    success = True

    try:
        ping_result = await shelter.ping()
        print(f"Ping: {ping_result}")
    except ShelterAPIError as exc:
        success = False
        print(f"Ping failed: {describe_error(exc)}")

    try:
        params = await shelter.get_hotel_params()
        categories = params.get("categories", []) or []
        rates = params.get("rates", []) or []
        print(f"Hotel params: categories={len(categories)} rates={len(rates)}")
    except ShelterAPIError as exc:
        success = False
        print(f"Hotel params failed: {describe_error(exc)}")

    try:
        variants = await shelter.get_variants(today, tomorrow, adults=2)
        print(f"Variants for {today}..{tomorrow}: {len(variants)}")
        for variant in variants[:5]:
            print(
                "  "
                f"signature={variant.signature_id or '-'} "
                f"category={variant.category_name or '-'} "
                f"price={variant.price} "
                f"available={variant.available_count}"
            )
    except ShelterAPIError as exc:
        success = False
        print(f"Variants failed: {describe_error(exc)}")

    try:
        availability = await shelter.get_room_availability()
        print(f"Availability categories: {len(availability)}")
        for room in availability[:5]:
            print(
                "  "
                f"room={room.room_name or '-'} "
                f"available={room.is_available} "
                f"price={room.price} "
                f"capacity={room.capacity}"
            )
    except ShelterAPIError as exc:
        success = False
        print(f"Availability failed: {describe_error(exc)}")

    return success


def run_database_checks() -> bool:
    print_section("Guest Bookings DB")
    today = get_local_today()
    print(f"Hotel local date: {today} ({get_local_now().tzinfo})")

    try:
        with SessionLocal() as db:
            active_bookings = db.query(GuestBooking).filter(GuestBooking.is_active == True).all()
            expired_active = db.query(GuestBooking).filter(
                GuestBooking.is_active == True,
                GuestBooking.check_out_date < today,
            ).all()
            arrivals_today = db.query(GuestBooking).filter(
                GuestBooking.is_active == True,
                GuestBooking.check_in_date == today,
            ).all()
            departures_today = db.query(GuestBooking).filter(
                GuestBooking.is_active == True,
                GuestBooking.check_out_date == today,
            ).all()
            pending_checkin = db.query(GuestBooking).filter(
                GuestBooking.is_active == True,
                GuestBooking.check_in_date == today,
                GuestBooking.checkin_notified == False,
            ).all()
            pending_checkout = db.query(GuestBooking).filter(
                GuestBooking.is_active == True,
                GuestBooking.check_out_date == today,
                GuestBooking.checkout_notified == False,
            ).all()

        print(f"Active bookings: {len(active_bookings)}")
        print(f"Expired but still active: {len(expired_active)}")
        print(f"Arrivals today: {len(arrivals_today)}")
        print(f"Departures today: {len(departures_today)}")
        print(f"Pending check-in notifications: {len(pending_checkin)}")
        print(f"Pending check-out notifications: {len(pending_checkout)}")

        if expired_active:
            print("Expired bookings that should be deactivated:")
            for booking in expired_active[:10]:
                print_booking_row("  ", booking)

        if arrivals_today:
            print("Today's arrivals:")
            for booking in arrivals_today[:10]:
                print_booking_row("  ", booking)

        if departures_today:
            print("Today's departures:")
            for booking in departures_today[:10]:
                print_booking_row("  ", booking)

        return not expired_active
    except OperationalError as exc:
        print("Database check failed. The schema may be outdated.")
        print(describe_error(exc))
        return False


def run_log_checks() -> bool:
    print_section("Bot Logs")
    if not shutil.which("journalctl"):
        print("journalctl is not available on this machine, skipping log inspection.")
        return True

    command = ["journalctl", "-u", "gora_bot", "-n", "200", "--no-pager"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(result.stderr.strip() or "Failed to read gora_bot logs.")
        return False

    log_output = result.stdout
    markers = [
        "Guest notification loop started",
        "Sent check-in notification",
        "Sent check-out notification",
        "Guest notification loop error",
    ]
    matching_lines = [
        line for line in log_output.splitlines()
        if any(marker in line for marker in markers)
    ]

    if not matching_lines:
        print("No guest notification log lines found in the last 200 entries.")
    else:
        print("Relevant log lines:")
        for line in matching_lines[-20:]:
            print(f"  {line}")

    return True


async def main() -> int:
    shelter_ok = await run_shelter_checks()
    db_ok = run_database_checks()
    logs_ok = run_log_checks()

    print_section("Summary")
    print(f"Shelter API OK: {shelter_ok}")
    print(f"Guest bookings DB OK: {db_ok}")
    print(f"Log inspection OK: {logs_ok}")

    if shelter_ok and db_ok and logs_ok:
        print("Diagnostics completed successfully.")
        return 0

    print("Diagnostics completed with warnings or failures.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
