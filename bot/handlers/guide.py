from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from db.session import SessionLocal
from db.models import GuideItem

router = Router()

@router.callback_query(F.data == "in_guide")
async def show_guide_categories(callback: CallbackQuery):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌲 Природа и Парки", callback_data="guide_cat_nature")],
        [InlineKeyboardButton(text="☕ Кафе и Рестораны", callback_data="guide_cat_cafes")],
        [InlineKeyboardButton(text="🚤 Активности и Прокат", callback_data="guide_cat_rent")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_in_house")]
    ])
    try:
        await callback.message.edit_text("🗺 Гид по Сортавала и Карелии\nВыберите категорию:", reply_markup=keyboard)
    except Exception:
        pass  # Ignore if message unchanged

@router.callback_query(F.data.startswith("guide_cat_"))
async def show_guide_items(callback: CallbackQuery):
    category = callback.data.replace("guide_cat_", "")
    
    with SessionLocal() as db:
        items = db.query(GuideItem).filter(GuideItem.category == category).all()
        
        if not items:
            await callback.answer("В этой категории пока нет мест", show_alert=True)
            return

        text = "📍 Рекомендуемые места:\n\n"
        buttons = []
        for item in items:
            text += f"<b>{item.name}</b>\n{item.description}\n\n"
            if item.map_url:
                buttons.append([InlineKeyboardButton(text=f"🗺 {item.name} на карте", url=item.map_url)])
        
        buttons.append([InlineKeyboardButton(text="↩️ К категориям", callback_data="in_guide")])
    
    await callback.answer()  # Acknowledge callback
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass  # Ignore if message unchanged
