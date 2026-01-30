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
        # Пытаемся получить параметры отеля
        params = await client.get_hotel_params()
        
        if params:
            print("\nSUCCESS! Data received from frontdesk24.ru")
            data = params.get('data', {})
            
            # В версии v2 данные обычно в data
            if isinstance(data, dict):
                hotel_name = data.get('hotelName') or data.get('name')
                print(f"Hotel Name: {hotel_name}")
                
                categories = data.get('categories', [])
                if categories:
                    print(f"\nFound {len(categories)} room categories:")
                    for cat in categories[:5]:
                        print(f"- {cat.get('name')} (ID: {cat.get('id')})")
            else:
                print(f"Data content: {str(data)[:200]}...")
            
            # Извлекаем категории номеров для доказательства
            categories = params.get('categories', [])
            if categories:
                print("\nRoom Categories from your Shelter system:")
                for cat in categories:
                    print(f"- {cat.get('name')} (ID: {cat.get('id')})")
            
            # Извлекаем способы оплаты
            payments = params.get('paymentTypes', [])
            if payments:
                print("\nPayment Options:")
                for p in payments:
                    print(f"- {p.get('name')} (ID: {p.get('id')})")
        else:
            print("\nError: Server returned empty response.")
            
    except ShelterAPIError as e:
        print(f"\nAPI Error: {e.message}")
        if e.description:
            print(f"Details: {e.description}")
        if e.code:
            print(f"Error Code: {e.code}")
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection())
