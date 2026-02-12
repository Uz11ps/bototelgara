from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_cache_rooms: set[str] = set()
_cache_until: float = 0.0

_ROOM_KEYS = {
    "room",
    "roomno",
    "room_no",
    "roomnum",
    "room_num",
    "roomnumber",
    "room_number",
    "number",
}

_DEFAULT_ENDPOINTS = [
    "/api/pms/getInHouseGuests",
    "/api/pms/getGuestsInHouse",
    "/api/pms/getCurrentGuests",
    "/api/pms/getRoomingList",
]


def _normalize_room(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-я]", "", value or "")
    return cleaned.upper()


def _extract_rooms(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_norm = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            key_norm = key_norm.replace("__", "_")
            if key_norm in _ROOM_KEYS and value is not None:
                room = _normalize_room(str(value))
                if room:
                    out.add(room)
            _extract_rooms(value, out)
    elif isinstance(obj, list):
        for item in obj:
            _extract_rooms(item, out)


def _build_candidate_endpoints() -> list[str]:
    raw = os.getenv("SHELTER_PMS_INHOUSE_ENDPOINTS", "")
    custom = [x.strip() for x in raw.split(",") if x.strip()]
    return custom or _DEFAULT_ENDPOINTS


async def _fetch_rooms_from_shelter() -> set[str]:
    token = (os.getenv("SHELTER_PMS_TOKEN") or "").strip().strip('"')
    if not token:
        logger.warning("SHELTER_PMS_TOKEN is not configured")
        return set()

    base_url = (os.getenv("SHELTER_PMS_BASE_URL") or "https://cloud.shelter.ru").rstrip("/")
    endpoints = _build_candidate_endpoints()

    rooms: set[str] = set()
    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint if endpoint.startswith('/') else '/' + endpoint}"

            # 1) GET with bearer header
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        payload = await resp.json(content_type=None)
                        _extract_rooms(payload, rooms)
                        if rooms:
                            return rooms
            except Exception:
                pass

            # 2) GET with token query
            try:
                async with session.get(url, params={"token": token}, headers={"Accept": "application/json"}) as resp:
                    if resp.status == 200:
                        payload = await resp.json(content_type=None)
                        _extract_rooms(payload, rooms)
                        if rooms:
                            return rooms
            except Exception:
                pass

            # 3) POST with token in body
            try:
                async with session.post(
                    url,
                    json={"token": token, "language": "ru"},
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 200:
                        payload = await resp.json(content_type=None)
                        _extract_rooms(payload, rooms)
                        if rooms:
                            return rooms
            except Exception:
                pass

    if not rooms:
        logger.warning("Failed to parse in-house room numbers from Shelter PMS")
    return rooms


async def get_shelter_occupied_rooms(force_refresh: bool = False) -> set[str]:
    global _cache_rooms, _cache_until

    now = time.time()
    if not force_refresh and now < _cache_until and _cache_rooms:
        return set(_cache_rooms)

    rooms = await _fetch_rooms_from_shelter()
    _cache_rooms = set(rooms)
    _cache_until = now + _CACHE_TTL_SECONDS
    return set(_cache_rooms)


async def can_use_room_service(room_number: str) -> bool:
    normalized = _normalize_room(room_number)
    if not normalized:
        return False
    rooms = await get_shelter_occupied_rooms()
    return normalized in rooms


async def can_user_use_room_service(telegram_id: str) -> bool:
    """Allow access only if user's active room exists in Shelter in-house list."""
    from db.models import GuestBooking
    from db.session import SessionLocal

    with SessionLocal() as db:
        booking = (
            db.query(GuestBooking)
            .filter(GuestBooking.telegram_id == str(telegram_id), GuestBooking.is_active == True)
            .first()
        )

    if not booking or not booking.room_number:
        return False

    return await can_use_room_service(booking.room_number)
