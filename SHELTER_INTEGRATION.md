# Shelter Cloud PMS Integration

## Overview
Integration with Shelter Cloud PMS system to fetch hotel occupancy data, room availability, and booking information.

## Configuration

### API Tokens
Two tokens are configured in `.env`:

```env
SHELTER_WIDGET_TOKEN="3D3AED88-3D9E-4B8D-AED8-3FAF58FC1310"
SHELTER_PMS_TOKEN="FCCB6C4B-BB7E-4D27-90EF-37D639AC9BA3"
```

### API Base URL
```
https://cloud.shelter.ru
```

## Implementation

### Service Layer
- **File**: `services/shelter.py`
- **Main Class**: `ShelterClient`
- **Features**:
  - API connectivity testing (`ping`)
  - Hotel information retrieval
  - Room availability checking
  - Occupancy statistics

### Bot Commands

#### `/hotelstatus` or `/status`
Shows current hotel occupancy:
- Total rooms
- Occupied rooms
- Available rooms
- Occupancy rate with visual bar
- Last update timestamp

#### `/rooms` or `/availability`
Shows detailed room availability:
- List of available rooms with prices
- Room capacity information
- Count of occupied rooms

#### `/sheltertest`
Admin command for API testing:
- Tests API ping
- Tests hotel info endpoint
- Tests room availability endpoint
- Shows connection status

## Current Status

### ✅ Completed
- Service layer implementation
- Bot command handlers
- Environment configuration
- Mock data fallback

### ⚠️ Pending
The provided API tokens have been tested, but **actual Shelter API endpoints are not yet discovered**. 

**Test Results:**
- ✅ `/api/Ping` - Works (connectivity OK)
- ❌ `/api/Booking` - Returns 403 Forbidden (controller exists but auth fails)
- ❌ Other endpoints - Return 404 Not Found

**Mock Data Currently Used:**
- Total rooms: 50
- Occupied: 32
- Available: 18
- Sample rooms: "Стандарт" and "Люкс"

### 📋 Next Steps

To enable real data from Shelter Cloud:

1. **Contact Shelter Support**
   - Request official API documentation
   - Verify correct API endpoints for:
     - Hotel information
     - Room availability
     - Occupancy statistics
   - Confirm authentication method

2. **Verify Tokens**
   - Widget token: `3D3AED88-3D9E-4B8D-AED8-3FAF58FC1310`
   - PMS token: `FCCB6C4B-BB7E-4D27-90EF-37D639AC9BA3`
   - Ensure tokens are activated in Shelter admin panel
   - Check if tokens need specific permissions/scopes

3. **Update Implementation**
   - Replace placeholder endpoints in `services/shelter.py`
   - Update response parsing based on actual API format
   - Remove mock data fallbacks

## API Documentation References

- **Widget API**: https://shelter.ru/knowledge/api-dlya-vidzhetov-bronirovaniya-na-sayte-dlya-shelter-cloud/
- **Main PMS API**: https://shelter.ru/knowledge/api-pms-shelter-cloud/

## Technical Notes

- The Shelter Cloud API uses .NET WebAPI framework
- Base URL is accessible and responds to `/api/Ping`
- Authentication appears to support Bearer tokens
- Multiple endpoint naming patterns tested (REST, RPC-style)
- Current implementation uses `aiohttp` for async HTTP requests

## Usage Example

```python
from services.shelter import get_shelter_client

# Get client instance
shelter = get_shelter_client()

# Test connection
ping_result = await shelter.ping()

# Get hotel stats
stats = await shelter.get_hotel_stats()
print(f"Occupancy: {stats.occupancy_rate:.1%}")

# Get room availability
rooms = await shelter.get_room_availability()
for room in rooms:
    if room.is_available:
        print(f"{room.room_name}: {room.price} ₽")
```

## Troubleshooting

If commands show mock data:
1. Check `.env` file has correct tokens
2. Run `/sheltertest` to diagnose API connection
3. Check bot logs for API errors
4. Contact Shelter support for API access

## Files Modified/Created

- ✅ `services/shelter.py` - Shelter API client
- ✅ `bot/handlers/admin.py` - Admin commands
- ✅ `bot/handlers/__init__.py` - Handler registration
- ✅ `.env` - API tokens configuration
- ✅ `requirements.txt` - Added aiohttp dependency
