"""Script to update guide items with correct Yandex Maps links."""
from db.session import SessionLocal
from db.models import GuideItem

def update_guide():
    db = SessionLocal()
    
    # Delete all existing guide items
    db.query(GuideItem).delete()
    db.commit()
    
    # Add updated guide items with correct links
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
    db.commit()
    db.close()
    print("Guide items updated successfully!")
    print(f"Total items: {len(guide_items)}")

if __name__ == "__main__":
    update_guide()
