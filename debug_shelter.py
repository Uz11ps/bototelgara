import asyncio
import os
import json
from services.shelter import get_shelter_client
from dotenv import load_dotenv

async def debug_params():
    load_dotenv()
    client = get_shelter_client()
    try:
        params = await client.get_hotel_params()
        print(json.dumps(params, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_params())
