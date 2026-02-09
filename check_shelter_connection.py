import asyncio
import os
import json
import sys
from services.shelter import get_shelter_client, ShelterAPIError
from dotenv import load_dotenv

# Принудительно ставим UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

async def test_connection():
    load_dotenv()
    print("--- Test: Connecting to Shelter Cloud API ---")
    
    client = get_shelter_client()
    try:
        # 1. Test Ping
        print("\n1. Testing Ping...")
        ping_result = await client.ping()
        print(f"Ping Result: {ping_result}")

        # 2. Test Hotel Params
        print("\n2. Testing get_hotel_params...")
        params = await client.get_hotel_params()
        
        if params:
            print("SUCCESS! Data received.")
            data = params.get('data', {})
            if isinstance(data, dict):
                hotel_name = data.get('hotelName') or data.get('name')
                print(f"Hotel Name: {hotel_name}")
        else:
            print("Error: Server returned empty response.")
            
        # 3. Test Hotel Stats
        print("\n3. Testing get_hotel_stats (Best Effort)...")
        stats = await client.get_hotel_stats()
        print(f"Total Rooms (est): {stats.total_rooms}")
        print(f"Occupied (est): {stats.occupied_rooms}")
        print(f"Available (est): {stats.available_rooms}")
        print(f"Occupancy Rate: {stats.occupancy_rate:.1%}")

        # 4. Test Room Availability
        print("\n4. Testing get_room_availability...")
        availability = await client.get_room_availability()
        print(f"Found {len(availability)} categories.")
        for room in availability[:5]:
            status = "✅ Available" if room.is_available else "❌ Full"
            print(f"- {room.room_name}: {status} (Price: {room.price}, Cap: {room.capacity})")

    except ShelterAPIError as e:
        print(f"\nAPI Error: {e.message}")
        if e.description:
            print(f"Details: {e.description}")
        if e.code:
            print(f"Error Code: {e.code}")
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
