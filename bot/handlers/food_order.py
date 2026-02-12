"""
Food ordering handlers for menu items.
"""
from __future__ import annotations

import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import FlowState
from db.models import TicketType
from db.session import SessionLocal
from services.admins import notify_admins_about_ticket
from services.tickets import create_ticket, TicketRateLimitExceededError
from services.content import content_manager

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(FlowState.in_house_menu, F.data == "in_restaurant")
async def start_food_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Start food ordering process."""
    from db.models import MenuItem
    
    await state.set_state(FlowState.food_ordering)
    await state.update_data(cart={})
    
    # Load menu from database
    with SessionLocal() as session:
        menu_items = session.query(MenuItem).filter(MenuItem.is_available == True).all()
        
        if not menu_items:
            await callback.message.answer("Меню временно недоступно. Пожалуйста, свяжитесь с администратором.")
            await callback.answer()
            return
        
        # Build menu keyboard
        builder = InlineKeyboardBuilder()
        for item in menu_items:
            builder.button(text=f"{item.name} - {item.price}₽", callback_data=f"menu_item_{item.id}")
        builder.button(text="🛒 Корзина", callback_data="view_cart")
        builder.button(text="↩️ Назад", callback_data="back_to_in_house")
        builder.adjust(1)
        
        await callback.message.answer(
            "🍽️ <b>Меню ресторана GORA</b>\n\n"
            "Выберите блюда для заказа. Они добавятся в корзину.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(FlowState.food_ordering, F.data.startswith("menu_item_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext) -> None:
    """Add item to cart."""
    from db.models import MenuItem
    
    item_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cart = data.get("cart", {})
    
    with SessionLocal() as session:
        item = session.query(MenuItem).filter(MenuItem.id == item_id).first()
        
        if not item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Add or increment quantity
        if str(item_id) in cart:
            cart[str(item_id)]["quantity"] += 1
        else:
            cart[str(item_id)] = {
                "name": item.name,
                "price": item.price,
                "quantity": 1
            }
        
        await state.update_data(cart=cart)
        
        total_items = sum(item["quantity"] for item in cart.values())
        await callback.answer(f"✅ {item.name} добавлено в корзину ({total_items} шт.)", show_alert=False)


@router.callback_query(FlowState.food_ordering, F.data == "view_cart")
async def view_cart(callback: CallbackQuery, state: FSMContext) -> None:
    """View cart and checkout."""
    data = await state.get_data()
    cart = data.get("cart", {})
    
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    
    # Calculate total
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    
    # Build cart display
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for item_id, item in cart.items():
        cart_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
    cart_text += f"\n<b>Итого: {total}₽</b>"
    
    # Build keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оформить заказ", callback_data="confirm_order")
    builder.button(text="🗑️ Очистить корзину", callback_data="clear_cart")
    builder.button(text="◀️ Продолжить выбор", callback_data="continue_shopping")
    builder.adjust(1)
    
    await callback.message.edit_text(
        cart_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(FlowState.food_ordering, F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear cart."""
    await state.update_data(cart={})
    await callback.answer("Корзина очищена", show_alert=True)
    await start_food_order(callback, state)


@router.callback_query(FlowState.food_ordering, F.data == "continue_shopping")
async def continue_shopping(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to menu."""
    await start_food_order(callback, state)


@router.callback_query(FlowState.food_ordering, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and create food order."""
    from aiogram import Bot
    
    data = await state.get_data()
    cart = data.get("cart", {})
    
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    
    # Calculate total
    items = [{"name": item["name"], "price": item["price"], "quantity": item["quantity"]} for item in cart.values()]
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    
    # Create order summary
    summary = "🍽️ Заказ из ресторана:\n\n"
    for item in items:
        summary += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
    summary += f"\nИтого: {total}₽"
    
    payload = {
        "items": items,
        "total": total
    }
    
    try:
        ticket = create_ticket(
            type_=TicketType.FOOD_ORDER,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=None,
            payload=payload,
            initial_message=summary
        )
    except TicketRateLimitExceededError:
        await callback.message.answer("Вы отправили слишком много заказов. Пожалуйста, подождите.")
        await state.clear()
        await callback.answer()
        return
    
    confirmation = (
        f"✅ <b>Заказ #{ticket.id} принят!</b>\n\n"
        f"Ваш заказ передан на кухню. "
        f"Ожидайте доставку в течение 30-40 минут.\n\n"
        f"Сумма: {total}₽"
    )
    await callback.message.edit_text(confirmation, parse_mode="HTML")
    
    bot: Bot = callback.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, f"🔥 Новый заказ еды #{ticket.id} на сумму {total}₽")
    
    await state.clear()
    await callback.answer()
