"""
Shelter Cloud PMS API Integration
Provides hotel room availability and booking data
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
import aiohttp

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
class ShelterAPIError(Exception):
    """Shelter API error"""
    code: Optional[str] = None
    message: Optional[str] = None
    description: Optional[str] = None


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
            "Authorization": self.widget_token,
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
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_data = result.get("error", {})
                        raise ShelterAPIError(
                            code=str(error_data.get("code", response.status)),
                            message=error_data.get("message", "API Error"),
                            description=error_data.get("description")
                        )
                    
                    if isinstance(result, dict) and "error" in result:
                        error_data = result["error"]
                        raise ShelterAPIError(
                            code=str(error_data.get("code", "0")),
                            message=error_data.get("message", "Unknown API error"),
                            description=error_data.get("description")
                        )
                        
                    return result
        
        except aiohttp.ClientError as e:
            raise ShelterAPIError(message=f"Network error: {str(e)}")
        except Exception as e:
            if isinstance(e, ShelterAPIError):
                raise
            raise ShelterAPIError(message=f"Unexpected error: {str(e)}")

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
        if isinstance(result, list):
            for item in result:
                variants.append(RoomVariant(
                    signature_id=item.get("signatureId"),
                    category_id=item.get("categoryId"),
                    category_name=item.get("categoryName"),
                    category_description=item.get("categoryDescription", ""),
                    price=float(item.get("price", 0)),
                    available_count=item.get("availableCount", 0),
                    capacity=item.get("capacity", 0),
                    images=item.get("images", []),
                    rate_id=item.get("rateId"),
                    rate_name=item.get("rateName")
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


# Singleton instance
_shelter_client: Optional[ShelterClient] = None


def get_shelter_client() -> ShelterClient:
    """Get Shelter API client instance"""
    global _shelter_client
    if _shelter_client is None:
        _shelter_client = ShelterClient()
    return _shelter_client
