"""
Menu ordering handler with shopping cart functionality.
"""
from __future__ import annotations

from datetime import datetime, time

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import (
    build_menu_categories_keyboard,
    build_menu_items_keyboard,
    build_cart_keyboard,
    build_order_confirm_keyboard,
    build_in_house_menu,
)
from bot.states import FlowState
from bot.navigation import VIEW_MENU, nav_push
from db.models import MenuItem, MenuCategory, MenuCategorySetting, TicketType
from db.session import SessionLocal
from services.content import content_manager
from services.admins import notify_admins_about_ticket
from services.guest_context import get_active_room_number
from services.tickets import TicketRateLimitExceededError, create_ticket


router = Router()

# Breakfast ordering time window
BREAKFAST_START_HOUR = 9
BREAKFAST_CUTOFF_HOUR = 17
BREAKFAST_CUTOFF_MINUTE = 45


def is_breakfast_available() -> bool:
    """Check if breakfast ordering is available (9:00 - 17:45)."""
    now = datetime.now().time()
    start = time(BREAKFAST_START_HOUR, 0)
    cutoff = time(BREAKFAST_CUTOFF_HOUR, BREAKFAST_CUTOFF_MINUTE)
    return start <= now <= cutoff


def get_menu_items_by_category(category: str) -> list[MenuItem]:
    """Get available menu items for a category."""
    with SessionLocal() as db:
        items = db.query(MenuItem).filter(
            MenuItem.category == category,
            MenuItem.is_available == True
        ).all()
        # Detach from session
        for item in items:
            db.expunge(item)
        return items


def get_menu_item_by_id(item_id: int) -> MenuItem | None:
    """Get menu item by ID."""
    with SessionLocal() as db:
        item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if item:
            db.expunge(item)
        return item


def is_menu_category_enabled(category: str) -> bool:
    try:
        cat_value = MenuCategory(category).value
    except ValueError:
        return False
    with SessionLocal() as db:
        row = db.query(MenuCategorySetting).filter(MenuCategorySetting.category == cat_value).first()
        if row is None:
            return category == "breakfast"
        return bool(row.is_enabled)


async def _show_category_menu(message: Message, state: FSMContext, category: str) -> None:
    """Render menu items for a specific category with cart controls."""
    if not is_menu_category_enabled(category):
        await message.answer(
            "Эта категория сейчас недоступна.",
            reply_markup=build_menu_categories_keyboard()
        )
        return

    if category == "breakfast" and not is_breakfast_available():
        await message.answer(
            content_manager.get_text("menu.breakfast_unavailable"),
            reply_markup=build_menu_categories_keyboard()
        )
        return

    items = get_menu_items_by_category(category)
    if not items:
        await message.answer(
            content_manager.get_text("menu.no_items_in_category"),
            reply_markup=build_menu_categories_keyboard()
        )
        return

    await state.update_data(current_category=category)
    await state.set_state(FlowState.menu_item_selection)

    data = await state.get_data()
    cart = data.get("cart", {})
    category_names = {
        "breakfast": "🍳 Завтрак",
        "lunch": "🍽 Обед",
        "dinner": "🌙 Ужин"
    }
    text = f"<b>{category_names.get(category, category)}</b>\n\nВыберите блюда:"
    await message.answer(
        text,
        reply_markup=build_menu_items_keyboard(items, category, cart),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "in_restaurant")
async def handle_menu_entry(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry point for menu/restaurant ordering."""
    await callback.answer()

    # Show current breakfast composition from real menu data.
    from bot.handlers.in_house import _build_breakfast_composition_from_menu
    await callback.message.answer(_build_breakfast_composition_from_menu(), parse_mode="HTML")
    
    # Initialize empty cart if not exists
    data = await state.get_data()
    if "cart" not in data:
        await state.update_data(cart={})
    await state.update_data(menu_entry_source="in_restaurant")
    await nav_push(state, VIEW_MENU)

    # Breakfast should open directly without extra "choose breakfast" click.
    await _show_category_menu(callback.message, state, "breakfast")


@router.callback_query(F.data == "menu_back_categories")
async def handle_back_to_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to category selection."""
    await callback.answer()
    data = await state.get_data()
    if data.get("menu_entry_source") == "in_restaurant":
        await state.set_state(FlowState.in_house_menu)
        await callback.message.answer(
            content_manager.get_text("menus.in_house_title"),
            reply_markup=build_in_house_menu(),
        )
        return

    await state.set_state(FlowState.menu_category_choice)
    text = content_manager.get_text("menu.category_prompt")
    try:
        await callback.message.edit_text(text, reply_markup=build_menu_categories_keyboard())
    except Exception:
        pass


@router.callback_query(F.data.startswith("menu_cat_"))
async def handle_category_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle category selection (breakfast, lunch, dinner)."""
    await callback.answer()
    category = callback.data.replace("menu_cat_", "")
    await _show_category_menu(callback.message, state, category)


@router.callback_query(F.data.startswith("menu_item_info_"))
async def handle_item_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Show detailed info about a menu item with full composition."""
    await callback.answer()
    
    item_id = int(callback.data.replace("menu_item_info_", ""))
    item = get_menu_item_by_id(item_id)
    
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    
    text = f"<b>{item.name}</b>\n\n"
    if item.description:
        text += f"{item.description}\n\n"
    
    # Show composition with quantities
    if item.composition:
        text += "<b>Состав:</b>\n"
        if isinstance(item.composition, list):
            for comp_item in item.composition:
                if isinstance(comp_item, dict):
                    comp_name = comp_item.get('name', '')
                    comp_qty = comp_item.get('quantity', '')
                    comp_unit = comp_item.get('unit', '')
                    if comp_qty and comp_unit:
                        text += f"• {comp_name} - {comp_qty} {comp_unit}\n"
                    else:
                        text += f"• {comp_name}\n"
                elif isinstance(comp_item, str):
                    text += f"• {comp_item}\n"
        elif isinstance(item.composition, str):
             text += f"{item.composition}\n"
        text += "\n"
    
    text += f"<b>Цена:</b> {item.price}₽"
    if item.admin_comment:
        text += f"\n\n💬 {item.admin_comment}"
    
    # Send as a message since alert is limited to 200 chars
    try:
        await callback.message.answer(text, parse_mode="HTML")
    except Exception:
        await callback.answer(text[:200], show_alert=True)


@router.callback_query(F.data.startswith("menu_item_plus_"))
async def handle_item_plus(callback: CallbackQuery, state: FSMContext) -> None:
    """Add item to cart."""
    await callback.answer("Добавлено в корзину")
    
    item_id = int(callback.data.replace("menu_item_plus_", ""))
    
    data = await state.get_data()
    cart = data.get("cart", {})
    cart[item_id] = cart.get(item_id, 0) + 1
    await state.update_data(cart=cart)
    
    # Refresh the menu display
    category = data.get("current_category", "breakfast")
    items = get_menu_items_by_category(category)
    
    category_names = {
        "breakfast": "🍳 Завтрак",
        "lunch": "🍽 Обед",
        "dinner": "🌙 Ужин"
    }
    text = f"<b>{category_names.get(category, category)}</b>\n\nВыберите блюда:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=build_menu_items_keyboard(items, category, cart),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("menu_item_minus_"))
async def handle_item_minus(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove item from cart."""
    item_id = int(callback.data.replace("menu_item_minus_", ""))
    
    data = await state.get_data()
    cart = data.get("cart", {})
    
    if item_id in cart and cart[item_id] > 0:
        cart[item_id] -= 1
        if cart[item_id] == 0:
            del cart[item_id]
        await state.update_data(cart=cart)
        await callback.answer("Удалено из корзины")
    else:
        await callback.answer()
    
    # Refresh the menu display
    category = data.get("current_category", "breakfast")
    items = get_menu_items_by_category(category)
    
    category_names = {
        "breakfast": "🍳 Завтрак",
        "lunch": "🍽 Обед",
        "dinner": "🌙 Ужин"
    }
    text = f"<b>{category_names.get(category, category)}</b>\n\nВыберите блюда:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=build_menu_items_keyboard(items, category, cart),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data == "menu_view_cart")
async def handle_view_cart(callback: CallbackQuery, state: FSMContext) -> None:
    """Display shopping cart."""
    await callback.answer()
    await state.set_state(FlowState.menu_cart_review)
    
    data = await state.get_data()
    cart = data.get("cart", {})
    
    cart_items = []
    total = 0
    
    for item_id, qty in cart.items():
        try:
            item_id = int(item_id)
        except ValueError:
            continue
        item = get_menu_item_by_id(item_id)
        if item:
            cart_items.append((item, qty))
            total += item.price * qty
    
    if cart_items:
        text = "<b>🛒 Ваша корзина:</b>\n\n"
        for item, qty in cart_items:
            text += f"• {item.name} x{qty} = {item.price * qty}₽\n"
        text += f"\n<b>💰 Итого: {total}₽</b>"
    else:
        text = "🛒 Корзина пуста\n\nДобавьте блюда из меню"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=build_cart_keyboard(cart_items, total),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=build_cart_keyboard(cart_items, total),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("cart_remove_"))
async def handle_cart_remove(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove item completely from cart."""
    await callback.answer("Удалено")
    
    item_id = int(callback.data.replace("cart_remove_", ""))
    
    data = await state.get_data()
    cart = data.get("cart", {})
    
    if item_id in cart:
        del cart[item_id]
        await state.update_data(cart=cart)
    
    # Refresh cart view
    await handle_view_cart(callback, state)


@router.callback_query(F.data == "cart_clear")
async def handle_cart_clear(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear entire cart."""
    await callback.answer("Корзина очищена")
    await state.update_data(cart={})
    await handle_view_cart(callback, state)


@router.callback_query(F.data == "cart_checkout")
async def handle_cart_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Proceed to checkout - first ask for guest name."""
    await callback.answer()
    await state.set_state(FlowState.menu_guest_name)
    
    await callback.message.answer("👤 Введите ваше имя:")


@router.message(FlowState.menu_guest_name)
async def handle_guest_name(message: Message, state: FSMContext) -> None:
    """Handle guest name and reuse saved room number when possible."""
    guest_name = message.text or ""
    await state.update_data(order_guest_name=guest_name)

    room_number = get_active_room_number(str(message.from_user.id))
    if room_number:
        await state.update_data(order_room_number=room_number)
        await state.set_state(FlowState.menu_guest_comment)
        await message.answer(
            f"🏨 Номер комнаты: {room_number}\n"
            "📝 Добавьте комментарий к заказу (или напишите '-' чтобы пропустить):"
        )
        return

    await state.set_state(FlowState.menu_room_number)
    
    await message.answer("🏨 Введите номер вашей комнаты:")


@router.message(FlowState.menu_room_number)
async def handle_room_number(message: Message, state: FSMContext) -> None:
    """Handle room number and ask for comment."""
    room_number = message.text or ""
    await state.update_data(order_room_number=room_number)
    await state.set_state(FlowState.menu_guest_comment)
    
    await message.answer("📝 Добавьте комментарий к заказу (или напишите '-' чтобы пропустить):")


@router.message(FlowState.menu_guest_comment)
async def handle_guest_comment(message: Message, state: FSMContext) -> None:
    """Handle guest comment and show order confirmation."""
    comment = message.text or ""
    if comment.lower() in ["-", ".", "нет", "пропустить"]:
        comment = ""
    await state.update_data(guest_comment=comment)
    await state.set_state(FlowState.menu_confirm_order)
    
    data = await state.get_data()
    cart = data.get("cart", {})
    guest_name = data.get("order_guest_name", "")
    room_number = data.get("order_room_number", "")
    
    # Build order summary with full composition
    cart_items = []
    total = 0
    
    for item_id, qty in cart.items():
        try:
            item_id = int(item_id)
        except ValueError:
            continue
        item = get_menu_item_by_id(item_id)
        if item:
            cart_items.append((item, qty))
            total += item.price * qty
    
    text = "<b>📋 Подтвердите заказ:</b>\n\n"
    
    if guest_name:
        text += f"👤 <b>Гость:</b> {guest_name}\n"
    if room_number:
        text += f"🏨 <b>Комната:</b> {room_number}\n"
    text += "\n"
    
    for item, qty in cart_items:
        text += f"🍽 <b>{item.name}</b> x{qty} = {item.price * qty}₽\n"
        # Show composition
        if item.composition and isinstance(item.composition, list):
            for comp_item in item.composition:
                comp_name = comp_item.get('name', '')
                comp_qty = comp_item.get('quantity', '')
                comp_unit = comp_item.get('unit', '')
                if comp_qty and comp_unit:
                    text += f"   • {comp_name} - {comp_qty} {comp_unit}\n"
                else:
                    text += f"   • {comp_name}\n"
        text += "\n"
    
    text += f"<b>💰 Итого: {total}₽</b>"
    
    if comment:
        text += f"\n\n💬 Комментарий: {comment}"
    
    await message.answer(text, reply_markup=build_order_confirm_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "order_confirm_yes")
async def handle_order_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and create the order."""
    await callback.answer()
    
    data = await state.get_data()
    cart = dict(data.get("cart", {}))
    # Сразу очищаем корзину, чтобы предотвратить дублирование при повторном нажатии
    await state.update_data(cart={})
    comment = data.get("guest_comment", "")
    guest_name = data.get("order_guest_name", "") or callback.from_user.full_name
    room_number = data.get("order_room_number", "")
    
    # Build order details
    cart_items = []
    total = 0
    order_lines = []
    
    for item_id, qty in cart.items():
        try:
            item_id = int(item_id)
        except ValueError:
            continue
        item = get_menu_item_by_id(item_id)
        if item:
            cart_items.append((item, qty))
            total += item.price * qty
            
            # Formulate line item
            line = f"{item.name} x{qty} = {item.price * qty}₽"
            
            # Add composition to order lines if available
            if item.composition:
                if isinstance(item.composition, list):
                    ingredients = []
                    for comp in item.composition:
                        if isinstance(comp, dict):
                            c_name = comp.get('name', '')
                            c_qty = comp.get('quantity', '')
                            c_unit = comp.get('unit', '')
                            if c_qty and c_unit:
                                ingredients.append(f"{c_name} {c_qty}{c_unit}")
                            else:
                                ingredients.append(c_name)
                        elif isinstance(comp, str):
                            ingredients.append(comp)
                    if ingredients:
                        line += f" ({', '.join(ingredients)})"
                elif isinstance(item.composition, str):
                    line += f" ({item.composition})"
            
            order_lines.append(line)
    
    if not cart_items:
        await callback.message.answer("Корзина пуста")
        await state.clear()
        return
    
    # Create payload
    payload = {
        "branch": "menu_order",
        "items": [{
            "id": item.id,
            "name": item.name,
            "qty": qty,
            "price": item.price,
            "subtotal": item.price * qty,
            "composition": item.composition
        } for item, qty in cart_items],
        "total": total,
        "guest_name": guest_name,
        "room_number": room_number,
        "guest_comment": comment,
    }
    
    # Detailed summary for admins
    summary = f"Заказ из меню:\nГость: {guest_name}\nКомната: {room_number}\n\n" + "\n".join(order_lines) + f"\n\n💰 Итого: {total}₽"
    if comment:
        summary += f"\n💬 Комментарий: {comment}"
    
    try:
        ticket = create_ticket(
            type_=TicketType.MENU_ORDER,
            guest_chat_id=str(callback.from_user.id),
            guest_name=guest_name,
            room_number=room_number,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        await callback.message.answer(content_manager.get_text("tickets.rate_limited"))
        await state.clear()
        return
    
    # Build confirmation message for USER with full composition (formatted nicely)
    confirmation = f"✅ <b>Заказ оформлен!</b>\n\n"
    confirmation += f"<b>Заказ #{ticket.id}</b>\n"
    confirmation += f"👤 <b>Гость:</b> {guest_name}\n"
    confirmation += f"🏨 <b>Комната:</b> {room_number}\n\n"
    
    for item, qty in cart_items:
        confirmation += f"🍽 <b>{item.name}</b> x{qty}\n"
        if item.composition and isinstance(item.composition, list):
            for comp_item in item.composition:
                if isinstance(comp_item, dict):
                    comp_name = comp_item.get('name', '')
                    comp_qty = comp_item.get('quantity', '')
                    comp_unit = comp_item.get('unit', '')
                    if comp_qty and comp_unit:
                        confirmation += f"   • {comp_name} - {comp_qty} {comp_unit}\n"
                    else:
                        confirmation += f"   • {comp_name}\n"
                elif isinstance(comp_item, str):
                     confirmation += f"   • {comp_item}\n"
        elif item.composition and isinstance(item.composition, str):
            confirmation += f"<i>{item.composition}</i>\n"
        confirmation += "\n"
    
    confirmation += f"<b>💰 Итого: {total}₽</b>\n"
    if comment:
        confirmation += f"\n💬 Комментарий: {comment}\n"
    confirmation += "\nМы свяжемся с вами для уточнения времени доставки."
    
    await callback.message.answer(confirmation, parse_mode="HTML")
    
    # Notify admins
    bot: Bot = callback.bot  # type: ignore
    await notify_admins_about_ticket(bot, ticket, summary)
    
    # Clear cart and state
    await state.clear()


@router.callback_query(F.data == "order_confirm_no")
async def handle_order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel order - go back to cart."""
    await callback.answer("Заказ отменён")
    await state.set_state(FlowState.menu_cart_review)
    await handle_view_cart(callback, state)


@router.callback_query(F.data == "menu_noop")
@router.callback_query(F.data == "cart_noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """No-op callback for display-only buttons."""
    await callback.answer()
