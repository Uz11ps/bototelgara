import asyncio
from db.session import SessionLocal
from db.models import MenuItem, GuideItem, User
from datetime import datetime

async def seed():
    db = SessionLocal()
    
    # 1. Seed Guide (Sortavala)
    guide_items = [
        GuideItem(category="nature", name="Парк Рускеала", description="Мраморный каньон, жемчужина Карелии. В 30 км от Сортавала.", map_url="https://yandex.ru/maps/-/CDu6Y-ZJ"),
        GuideItem(category="nature", name="Гора Паасо", description="Панорамный вид на город и Ладожские шхеры. Легкий подъем.", map_url="https://yandex.ru/maps/-/CDu6Y-ZJ"),
        GuideItem(category="cafes", name="Лоухи", description="Карельская кухня, знаменитые калитки и уха на сливках.", map_url="https://yandex.ru/maps/-/CDu6Y-ZJ"),
        GuideItem(category="rent", name="Ладожские шхеры", description="Аренда катеров и прогулки по островам Ладожского озера.", map_url="https://yandex.ru/maps/-/CDu6Y-ZJ")
    ]
    db.add_all(guide_items)
    
    # 2. Seed Menu
    menu_items = [
        MenuItem(category="breakfast", name="Завтрак 'Карельский'", description="Калитки с картофелем, форель м/с, каша на выбор.", price=650),
        MenuItem(category="main", name="Форель по-карельски", description="Запеченная форель с картофелем и травами.", price=850),
        MenuItem(category="drinks", name="Иван-чай", description="Традиционный карельский травяной чай.", price=250)
    ]
    db.add_all(menu_items)
    
    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
