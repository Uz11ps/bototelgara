"""
Shelter Cloud PMS API Integration
Provides hotel room availability and booking data
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date, time, timedelta
from dataclasses import dataclass
import aiohttp

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RoomVariant:
    """Room variant data from getVariants"""
    signature_id: str
    category_id: int
    category_name: str
    category_description: str
    price: float
    available_count: int
    capacity: int
    images: List[str]
    rate_id: int
    rate_name: str


@dataclass
class HotelStats:
    """Hotel statistics for admin dashboard"""
    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    occupancy_rate: float
    last_updated: datetime


@dataclass
class RoomAvailability:
    """Room availability info for admin dashboard"""
    room_name: str
    is_available: bool
    price: Optional[float]
    capacity: Optional[int]


@dataclass
class ShelterAPIError(Exception):
    """Shelter API error"""
    code: Optional[str] = None
    message: Optional[str] = None
    description: Optional[str] = None


@dataclass
class PMSReservation:
    id: str
    status: str
    check_in: date
    check_out: date
    room_number: str | None
    guest_name: str | None
    is_annulled: bool
    guests: list[dict[str, Any]]


@dataclass
class PMSGuest:
    id: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    email: str | None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "annulled", "cancelled"}
    return False


def _parse_date_value(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    for candidate in (normalized, normalized.split("T")[0], normalized.split(" ")[0]):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.date()
        except ValueError:
            pass
        try:
            return datetime.strptime(candidate, "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("data", "items", "results", "reservations", "value"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_items(value)
            if nested:
                return nested

    return [payload]


def _extract_room_number(item: dict[str, Any]) -> str | None:
    direct = _coerce_str(
        item.get("roomNumber")
        or item.get("roomNo")
        or item.get("room_number")
        or item.get("number")
    )
    if direct:
        return direct

    room_data = item.get("room")
    if isinstance(room_data, dict):
        return _coerce_str(
            room_data.get("roomNumber")
            or room_data.get("roomNo")
            or room_data.get("number")
            or room_data.get("name")
        )
    return _coerce_str(room_data)


def _extract_guest_items(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_guests = item.get("guests")
    if isinstance(raw_guests, list):
        return [guest for guest in raw_guests if isinstance(guest, dict)]
    return []


class ShelterClient:
    """
    Shelter Cloud PMS API Client for Booking Widget v2
    Documentation: https://shelter.ru/knowledge/api-dlya-vidzhetov-bronirovaniya-na-sayte-dlya-shelter-cloud/
    """
    
    def __init__(
        self,
        base_url: str = "https://pms.frontdesk24.ru",
        widget_token: Optional[str] = None,
    ):
        self.base_url = base_url
        self.widget_token = widget_token or os.getenv("SHELTER_WIDGET_TOKEN")
        self._timeout = aiohttp.ClientTimeout(total=8, connect=4, sock_read=6)
        
        if not self.widget_token:
            logger.warning("No Shelter Widget API token configured. API calls will fail.")
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict] = None,
    ) -> Any:
        """Make HTTP request to Shelter API"""
        url = f"{self.base_url}{endpoint}"
        
        if not self.widget_token:
            raise ShelterAPIError(message="No API token configured")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Shelter API often expects token and language in the body or as a query param
        request_data = data or {}
        if "token" not in request_data:
            request_data["token"] = self.widget_token
        if "language" not in request_data:
            request_data["language"] = "ru"
            
        params = {
            "token": self.widget_token,
            "language": "ru"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=request_data,
                    params=params,
                    timeout=self._timeout
                ) as response:
                    raw_body = await response.text()
                    content_type = response.headers.get("Content-Type", "")
                    result: Any = None

                    if "application/json" in content_type.lower():
                        try:
                            result = json.loads(raw_body)
                        except json.JSONDecodeError:
                            result = None
                    else:
                        # Some Shelter endpoints may return JSON with incorrect MIME type.
                        stripped = raw_body.lstrip()
                        if stripped.startswith("{") or stripped.startswith("["):
                            try:
                                result = json.loads(raw_body)
                            except json.JSONDecodeError:
                                result = None
                    
                    if response.status != 200:
                        error_data = result.get("error", {}) if isinstance(result, dict) else {}
                        snippet = (raw_body or "").strip().replace("\n", " ")[:300]
                        if response.status == 401:
                            raise ShelterAPIError(
                                code="401",
                                message="Ошибка авторизации Shelter API (401). Проверьте SHELTER_WIDGET_TOKEN.",
                                description=snippet or "Unauthorized"
                            )
                        raise ShelterAPIError(
                            code=str(error_data.get("code", response.status)),
                            message=error_data.get("message", f"API Error ({response.status})"),
                            description=error_data.get("description") or snippet
                        )
                    
                    if isinstance(result, dict) and "error" in result:
                        error_data = result["error"]
                        raise ShelterAPIError(
                            code=str(error_data.get("code", "0")),
                            message=error_data.get("message", "Unknown API error"),
                            description=error_data.get("description")
                        )
                        
                    # Fallback to raw text if API returns non-JSON successful body.
                    return result if result is not None else raw_body
        
        except aiohttp.ClientError as e:
            raise ShelterAPIError(message=f"Network error: {str(e)}")
        except Exception as e:
            if isinstance(e, ShelterAPIError):
                raise
            raise ShelterAPIError(message=f"Unexpected error: {str(e)}")

    async def ping(self) -> str:
        """Test API connection using getHotelParams"""
        try:
            await self.get_hotel_params()
            return "OK"
        except Exception as e:
            raise ShelterAPIError(message=f"Ping failed: {str(e)}")

    async def get_hotel_params(self) -> Dict[str, Any]:
        """
        Get hotel parameters and settings (getHotelParams)
        Returns categories, rates, payment options, settings, etc.
        """
        result = await self._make_request("/api/online/getHotelParams")
        
        # Structure the data for easier consumption
        if result and result.get("data") and isinstance(result["data"], list):
            d = result["data"]
            return {
                "settings": d[0][0] if len(d) > 0 and len(d[0]) > 0 else {},
                "languages": d[2] if len(d) > 2 else [],
                "amenities": d[3] if len(d) > 3 else [],
                "rates": d[4] if len(d) > 4 else [],
                "categories": d[6] if len(d) > 6 else [],
                "hotel_info": d[7][0] if len(d) > 7 and len(d[7]) > 0 else {},
                "raw": result
            }
        return result

    async def get_variants(
        self,
        check_in: date,
        check_out: date,
        adults: int = 1,
        children_ages: Optional[List[int]] = None,
    ) -> List[RoomVariant]:
        """
        Search for available room variants (getVariants)
        """
        data = {
            "checkIn": check_in.strftime("%Y-%m-%d"),
            "checkOut": check_out.strftime("%Y-%m-%d"),
            "adults": adults,
            "childrenAges": children_ages or []
        }
        
        result = await self._make_request("/api/online/getVariants", data=data)
        
        variants = []
        
        # API returns a dict with a 'data' array
        items_list = []
        if isinstance(result, dict) and "data" in result:
            items_list = result["data"]
        elif isinstance(result, list):
            items_list = result
            
        for item in items_list:
            # Skip empty items (API sometimes returns [[], [], ...])
            if not item or not isinstance(item, dict):
                continue
                
            variants.append(RoomVariant(
                signature_id=item.get("signatureId", ""),
                category_id=item.get("categoryId", 0),
                category_name=item.get("categoryName", ""),
                category_description=item.get("categoryDescription", ""),
                price=float(item.get("price", 0)),
                available_count=item.get("availableCount", 0),
                capacity=item.get("capacity", 0),
                images=item.get("images", []),
                rate_id=item.get("rateId", 0),
                rate_name=item.get("rateName", "")
            ))
        return variants

    async def get_payment_options(self, signature_id: str) -> List[Dict[str, Any]]:
        """
        Get available payment options for a specific variant (getPaymentOptions)
        """
        data = {"signatureId": signature_id}
        return await self._make_request("/api/online/getPaymentOptions", data=data)

    async def put_order(
        self,
        signature_id: str,
        payment_type_id: int,
        customer: Dict[str, Any],
        guests: List[Dict[str, Any]],
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new booking (putOrder)
        """
        data = {
            "signatureId": signature_id,
            "paymentTypeId": payment_type_id,
            "customer": customer,
            "guests": guests,
            "comment": comment or ""
        }
        return await self._make_request("/api/online/putOrder", data=data)

    async def get_order(self, order_token: str) -> Dict[str, Any]:
        """
        Get order details (getOrder)
        """
        data = {"orderToken": order_token}
        return await self._make_request("/api/online/getOrder", data=data)

    async def annul_order(self, order_token: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an order (annulOrder)
        """
        data = {
            "orderToken": order_token,
            "reason": reason or "Cancelled via Telegram Bot"
        }
        return await self._make_request("/OnlineWidget3/online/v3/annulOrder", data=data)

    async def get_hotel_stats(self) -> HotelStats:
        """
        Get hotel stats using available endpoints (implied logic since no direct stats endpoint)
        """
        # Since there is no direct "stats" endpoint in the widget API,
        # we will fetch hotel params to get total categories and make a sample search
        # to estimate availability. This is a BEST EFFORT implementation.
        
        params = await self.get_hotel_params()
        categories = params.get("categories", [])
        
        # Estimate total rooms (Widget API doesn't give total count per category, assume 10 per cat for mockup/estimation if missing)
        # Realistically, we can't know total rooms via Widget API easily.
        # We will use the count of categories as a proxy or fixed number if not available.
        total_rooms = len(categories) * 10 if categories else 50
        
        # Check availability for TOMORROW
        check_in = date.today()
        check_out = check_in + timedelta(days=1)
        variants = await self.get_variants(check_in, check_out, adults=2)
        
        available_rooms = sum(v.available_count for v in variants)
        occupied_rooms = max(0, total_rooms - available_rooms)
        occupancy_rate = occupied_rooms / total_rooms if total_rooms > 0 else 0.0
        
        return HotelStats(
            total_rooms=total_rooms,
            occupied_rooms=occupied_rooms,
            available_rooms=available_rooms,
            occupancy_rate=occupancy_rate,
            last_updated=datetime.now()
        )

    async def get_room_availability(self) -> List[RoomAvailability]:
        """
        Get availability by category
        """
        check_in = date.today()
        check_out = check_in + timedelta(days=1)
        variants = await self.get_variants(check_in, check_out, adults=2)
        
        availability_list = []
        # Create a map of updated availability from search
        variant_map = {v.category_name: v for v in variants}
        
        # Get all categories to show even those with 0 availability
        params = await self.get_hotel_params()
        categories = params.get("categories", [])
        
        for cat in categories:
            name = cat.get("name", "Unknown")
            variant = variant_map.get(name)
            
            is_available = False
            price = None
            capacity = None
            
            if variant:
                is_available = variant.available_count > 0
                price = variant.price
                capacity = variant.capacity
            
            availability_list.append(RoomAvailability(
                room_name=name,
                is_available=is_available,
                price=price,
                capacity=capacity
            ))
            
        return availability_list


class ShelterPMSClient:
    """Shelter PMS API client for reservation and guest sync."""
    PAGE_SIZE = 50

    def __init__(
        self,
        base_url: str | None = None,
        pms_token: str | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.shelter_pms_base_url).rstrip("/")
        self.pms_token = pms_token or settings.shelter_pms_token
        self._timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)

        if not self.pms_token:
            logger.warning("No Shelter PMS token configured. PMS sync calls will fail.")

    async def _pms_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[dict[str, Any]] = None,
    ) -> Any:
        if not self.pms_token:
            raise ShelterAPIError(message="No Shelter PMS token configured")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.pms_token}",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"

        candidate_endpoints = [endpoint]
        if endpoint.startswith("/api/"):
            candidate_endpoints.append(endpoint[4:])

        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                last_error: ShelterAPIError | None = None
                for candidate in candidate_endpoints:
                    url = f"{self.base_url}{candidate}"
                    async with session.request(
                        method,
                        url,
                        headers=headers,
                        json=data,
                    ) as response:
                        raw_body = await response.text()
                        parsed: Any = None
                        if raw_body.strip():
                            try:
                                parsed = json.loads(raw_body)
                            except json.JSONDecodeError:
                                parsed = raw_body

                        if response.status == 404 and candidate != candidate_endpoints[-1]:
                            continue

                        if response.status >= 400:
                            snippet = (raw_body or "").strip().replace("\n", " ")[:300]
                            last_error = ShelterAPIError(
                                code=str(response.status),
                                message=f"Shelter PMS API error ({response.status})",
                                description=snippet or None,
                            )
                            break

                        return parsed

                if last_error is not None:
                    raise last_error
        except aiohttp.ClientError as exc:
            raise ShelterAPIError(message=f"PMS network error: {exc}") from exc

    def _parse_reservation(self, item: dict[str, Any]) -> PMSReservation | None:
        reservation_id = _coerce_str(
            item.get("id")
            or item.get("reservationId")
            or item.get("reservation_id")
            or item.get("Id")
        )
        check_in = _parse_date_value(
            item.get("checkIn")
            or item.get("check_in")
            or item.get("arrivalDate")
            or item.get("from")
            or item.get("livedFrom")
            or item.get("beginDate")
        )
        check_out = _parse_date_value(
            item.get("checkOut")
            or item.get("check_out")
            or item.get("departureDate")
            or item.get("until")
            or item.get("livedTo")
            or item.get("endDate")
        )
        if not reservation_id or not check_in or not check_out:
            return None

        status = _coerce_str(
            item.get("status")
            or item.get("reservationStatus")
            or item.get("state")
        ) or "UNKNOWN"
        guest_name = _coerce_str(
            item.get("guestName")
            or item.get("customerName")
            or item.get("fullName")
            or item.get("name")
        )
        is_annulled = _coerce_bool(
            item.get("isAnnul")
            or item.get("is_annul")
            or item.get("annulled")
            or item.get("isCanceled")
            or item.get("cancelled")
        ) or any(token in status.lower() for token in ("annul", "cancel"))

        return PMSReservation(
            id=reservation_id,
            status=status,
            check_in=check_in,
            check_out=check_out,
            room_number=_extract_room_number(item),
            guest_name=guest_name,
            is_annulled=is_annulled,
            guests=_extract_guest_items(item),
        )

    def _parse_guest(self, item: dict[str, Any]) -> PMSGuest | None:
        guest_id = _coerce_str(
            item.get("id")
            or item.get("guestId")
            or item.get("guest_id")
            or item.get("Id")
        ) or "unknown"
        return PMSGuest(
            id=guest_id,
            first_name=_coerce_str(item.get("firstName") or item.get("first_name") or item.get("name")),
            last_name=_coerce_str(item.get("lastName") or item.get("last_name") or item.get("surname")),
            phone=_coerce_str(item.get("phone") or item.get("phoneNumber") or item.get("mobilePhone")),
            email=_coerce_str(item.get("email") or item.get("emailAddress")),
        )

    async def get_reservations_by_filter(
        self,
        lived_from: date,
        lived_to: date,
        is_annul: bool = False,
    ) -> list[PMSReservation]:
        lived_from_dt = datetime.combine(lived_from, time.min).isoformat()
        lived_to_dt = datetime.combine(lived_to, time.max.replace(microsecond=0)).isoformat()
        reservations: list[PMSReservation] = []
        offset = 0

        while True:
            payload = {
                "livedFrom": lived_from_dt,
                "livedTo": lived_to_dt,
                "isAnnul": is_annul,
                "pagination": {
                    "from": offset,
                    "count": self.PAGE_SIZE,
                },
            }
            result = await self._pms_request("/api/Reservations/ByFilter", method="POST", data=payload)
            items = _extract_items(result)
            for item in items:
                reservation = self._parse_reservation(item)
                if reservation:
                    reservations.append(reservation)

            total_count = result.get("count") if isinstance(result, dict) else None
            if not items:
                break
            offset += len(items)
            if isinstance(total_count, int) and offset >= total_count:
                break
            if len(items) < self.PAGE_SIZE:
                break

        return reservations

    async def get_reservation_guests(self, reservation_id: str) -> list[PMSGuest]:
        try:
            result = await self._pms_request(f"/api/Reservations/{reservation_id}/Guests")
            items = _extract_items(result)
        except ShelterAPIError as exc:
            if exc.code != "404":
                raise
            result = await self._pms_request(f"/api/Reservations/{reservation_id}")
            if isinstance(result, dict):
                items = _extract_guest_items(result)
            else:
                nested_items = _extract_items(result)
                items = _extract_guest_items(nested_items[0]) if nested_items else []

        guests: list[PMSGuest] = []
        for item in items:
            guest = self._parse_guest(item)
            if guest:
                guests.append(guest)
        return guests

    async def get_reservation(self, reservation_id: str) -> PMSReservation | None:
        result = await self._pms_request(f"/api/Reservations/{reservation_id}")
        if isinstance(result, dict):
            return self._parse_reservation(result)
        items = _extract_items(result)
        if not items:
            return None
        return self._parse_reservation(items[0])


# Singleton instance
_shelter_client: Optional[ShelterClient] = None
_shelter_pms_client: Optional[ShelterPMSClient] = None


def get_shelter_client() -> ShelterClient:
    """Get Shelter API client instance"""
    global _shelter_client
    if _shelter_client is None:
        _shelter_client = ShelterClient()
    return _shelter_client


def get_shelter_pms_client() -> ShelterPMSClient:
    """Get Shelter PMS API client instance."""
    global _shelter_pms_client
    if _shelter_pms_client is None:
        _shelter_pms_client = ShelterPMSClient()
    return _shelter_pms_client
