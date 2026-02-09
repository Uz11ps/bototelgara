import asyncio
from db.session import SessionLocal
from db.models import MenuItem, GuideItem, User, MenuCategory
from datetime import datetime

async def seed():
    db = SessionLocal()
    
    # 1. Seed Guide (Sortavala)
    guide_items = [
        # Nature & Parks
        GuideItem(
            category="nature", 
            name="Горный Парк Рускеала", 
            description="Мраморный каньон, жемчужина Карелии. В 30 км от Сортавала. Подземные маршруты, катера по каньону, зип-лайн.", 
            map_url="https://yandex.ru/maps/-/CPEVeFOJ"
        ),
        GuideItem(
            category="nature", 
            name="Водопады Ахинкоски", 
            description="Красивые водопады в 20 км от Сортавала. Отличное место для фото.", 
            map_url="https://yandex.ru/maps/-/CPEVeK8G"
        ),
        
        # Cafes & Restaurants
        GuideItem(
            category="cafes", 
            name="Ресторан Gard", 
            description="П. Кирьявалахти. Авторская кухня, вид на Ладожское озеро. Рейтинг 4.8", 
            map_url="https://yandex.ru/maps/-/CPEVe0yX"
        ),
        GuideItem(
            category="cafes", 
            name="Приладожье", 
            description="П. Рауталахти. Кафе-ресторан с карельской кухней и видом на озеро. Рейтинг 4.7", 
            map_url="https://yandex.ru/maps/-/CPEVe2Ia"
        ),
        GuideItem(
            category="cafes", 
            name="Ресторан Пиипун Пиха", 
            description="г. Сортавала. Карельская и финская кухня, уютная атмосфера. Рейтинг 4.6", 
            map_url="https://yandex.ru/maps/-/CDFxuRCa"
        ),
        GuideItem(
            category="cafes", 
            name="Кафе Карельская Горница", 
            description="г. Сортавала. Традиционные калитки, уха на сливках, домашняя выпечка. Рейтинг 4.8", 
            map_url="https://yandex.ru/maps/-/CDFxuS3c"
        ),
        
        # Activities & Rent
        GuideItem(
            category="rent", 
            name="Ладожские шхеры", 
            description="Аренда катеров и прогулки по островам Ладожского озера. Незабываемые виды!", 
            map_url="https://yandex.ru/maps/-/CPEViFIy"
        ),
        GuideItem(
            category="rent", 
            name="Ретро-поезд Рускеальский экспресс", 
            description="Путешествие на старинном паровозе до парка Рускеала через живописные места.", 
            map_url="https://yandex.ru/maps/-/CDFxuVRt"
        )
    ]
    db.add_all(guide_items)
    
    # 2. Seed Menu with categories - composition as JSON array
    menu_items = [
        # Breakfast items
        MenuItem(
            category="breakfast",
            category_type=MenuCategory.BREAKFAST,
            name="Завтрак 'Классический'",
            description="Полный завтрак с выбором блюд",
            composition=[
                {"name": "Яйца (яичница/омлет)", "quantity": 2, "unit": "шт"},
                {"name": "Бекон", "quantity": 50, "unit": "г"},
                {"name": "Тост", "quantity": 2, "unit": "шт"},
                {"name": "Сок апельсиновый", "quantity": 200, "unit": "мл"},
                {"name": "Кофе/Чай", "quantity": 1, "unit": "порция"}
            ],
            price=650,
            is_available=True
        ),
        MenuItem(
            category="breakfast",
            category_type=MenuCategory.BREAKFAST,
            name="Карельский завтрак",
            description="Традиционные карельские блюда",
            composition=[
                {"name": "Калитки с картофелем", "quantity": 3, "unit": "шт"},
                {"name": "Сметана", "quantity": 50, "unit": "г"},
                {"name": "Иван-чай с медом", "quantity": 200, "unit": "мл"}
            ],
            price=450,
            is_available=True
        ),
        
        # Lunch items
        MenuItem(
            category="lunch",
            category_type=MenuCategory.LUNCH,
            name="Уха по-карельски",
            description="Суп из свежей форели на сливках",
            composition=[
                {"name": "Форель", "quantity": 150, "unit": "г"},
                {"name": "Сливки", "quantity": 100, "unit": "мл"},
                {"name": "Картофель", "quantity": 100, "unit": "г"},
                {"name": "Зелень", "quantity": None, "unit": None}
            ],
            price=550,
            is_available=True
        ),
        MenuItem(
            category="lunch",
            category_type=MenuCategory.LUNCH,
            name="Стейк из форели",
            description="Запеченная форель с овощами",
            composition=[
                {"name": "Филе форели", "quantity": 200, "unit": "г"},
                {"name": "Овощи гриль", "quantity": 150, "unit": "г"},
                {"name": "Лимонный соус", "quantity": 30, "unit": "мл"}
            ],
            price=850,
            is_available=True
        ),
        
        # Dinner items
        MenuItem(
            category="dinner",
            category_type=MenuCategory.DINNER,
            name="Оленина с брусничным соусом",
            description="Тушеная оленина с ягодным соусом",
            composition=[
                {"name": "Оленина", "quantity": 200, "unit": "г"},
                {"name": "Брусничный соус", "quantity": 50, "unit": "мл"},
                {"name": "Картофельное пюре", "quantity": 150, "unit": "г"}
            ],
            price=1200,
            is_available=True,
            admin_comment="Хит сезона!"
        ),
        MenuItem(
            category="dinner",
            category_type=MenuCategory.DINNER,
            name="Паста с морепродуктами",
            description="Спагетти с креветками в сливочном соусе",
            composition=[
                {"name": "Спагетти", "quantity": 200, "unit": "г"},
                {"name": "Креветки", "quantity": 100, "unit": "г"},
                {"name": "Сливочный соус", "quantity": 80, "unit": "мл"},
                {"name": "Пармезан", "quantity": 20, "unit": "г"}
            ],
            price=750,
            is_available=True
        ),
        MenuItem(
            category="dinner",
            category_type=MenuCategory.DINNER,
            name="Иван-чай",
            description="Традиционный карельский чай",
            composition=[
                {"name": "Иван-чай", "quantity": 300, "unit": "мл"},
                {"name": "Мед", "quantity": 30, "unit": "г"}
            ],
            price=250,
            is_available=True
        ),
    ]
    db.add_all(menu_items)
    
    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
