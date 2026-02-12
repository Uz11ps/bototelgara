import asyncio
import json
from db.models import MenuItem
from db.session import SessionLocal
from fastapi.encoders import jsonable_encoder

def test_serialization():
    db = SessionLocal()
    try:
        items = db.query(MenuItem).all()
        print(f"Found {len(items)} items")
        if not items:
            print("No items found. Create one?")
            return

        # Serialize
        serialized = jsonable_encoder(items)
        
        # Check composition
        for item in serialized:
            print(f"Item {item['id']} ({item['name']}): Composition type={type(item.get('composition'))} -> {item.get('composition')}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_serialization()
