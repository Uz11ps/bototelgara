from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from services.content import content_manager


router = Router()


from datetime import datetime

def get_current_season() -> str:
    month = datetime.now().month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    from db.session import SessionLocal
    from services.tickets import is_user_admin
    from bot.keyboards.main_menu import build_admin_panel_menu, build_main_reply_keyboard
    
    user_id = str(message.from_user.id)
    
    # 1. Always send the main menu (Persistent Reply Keyboard) to ensure it's installed
    greeting = content_manager.get_text("greeting.start")
    season = get_current_season()
    seasonal_text = content_manager.get_text(f"seasons.{season}")
    choice_prompt = content_manager.get_text("menus.segment_choice_prompt")

    await message.answer(
        f"{greeting}\n\n{seasonal_text}\n\n{choice_prompt}", 
        reply_markup=build_main_reply_keyboard()
    )
    
    # 2. Check if user is admin and show admin panel as a separate message
    with SessionLocal() as session:
        if is_user_admin(session, user_id):
            from services.tickets import get_pending_tickets, get_all_active_tickets
            pending_count = len(get_pending_tickets(session))
            all_count = len(get_all_active_tickets(session))
            
            admin_greeting = (
                f"👨‍💼 <b>Добро пожаловать в админ-панель отеля GORA</b>\n\n"
                f"📊 Активных заявок: {all_count}\n"
                f"⏳ Ожидают решения: {pending_count}\n\n"
                f"Выберите действие:"
            )
            
            await message.answer(admin_greeting, reply_markup=build_admin_panel_menu(), parse_mode="HTML")


@router.callback_query(F.data == "back_to_segment")
async def back_to_segment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FlowState.choosing_segment)
    # Since main menu is a persistent reply keyboard, we just delete the sub-menu message
    # and remind the user to use the bottom menu.
    await callback.message.delete()
    choice_prompt = content_manager.get_text("menus.segment_choice_prompt")
    await callback.message.answer(choice_prompt)


@router.message(F.text == "🏠 Главное меню")
async def reply_main_menu(message: Message, state: FSMContext) -> None:
    await cmd_start(message)


@router.message(F.text == "📞 Администратор")
async def reply_admin_contact(message: Message, state: FSMContext) -> None:
    from bot.keyboards.main_menu import build_contact_admin_type_menu
    await state.set_state(FlowState.contact_admin_type)
    await message.answer(
        "Выберите, кто вы:",
        reply_markup=build_contact_admin_type_menu()
    )


@router.message(F.text == "🛎 Рум-сервис")
async def reply_room_service(message: Message, state: FSMContext) -> None:
    from bot.keyboards.main_menu import build_room_service_menu
    await state.set_state(FlowState.room_service_choosing_branch)
    text = content_manager.get_text("room_service.what_do_you_need")
    await message.answer(text, reply_markup=build_room_service_menu())


# NOTE: segment_pre_arrival and segment_in_house callbacks are handled in check_in.py


@router.message(Command("reload_content"))
async def reload_content(message: Message) -> None:
    from db.session import SessionLocal
    from db.models import AdminUser

    user_id = str(message.from_user.id)

    with SessionLocal() as session:
        admin = (
            session.query(AdminUser)
            .filter(AdminUser.telegram_id == user_id, AdminUser.is_active == 1)
            .first()
        )

    if admin is None:
        text = content_manager.get_text("system.not_authorized")
        await message.answer(text)
        return

    content_manager.reload()
    text = content_manager.get_text("system.content_reloaded")
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands"""
    from db.session import SessionLocal
    from services.tickets import is_user_admin
    
    user_id = str(message.from_user.id)
    
    # Check if user is admin
    with SessionLocal() as session:
        is_admin = is_user_admin(session, user_id)
    
    if is_admin:
        help_text = (
            "📋 <b>Команды администратора:</b>\n\n"
            "<b>Управление заявками:</b>\n"
            "/admin или /panel - Админ-панель\n"
            "/view_ticket ID - Просмотр заявки\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n\n"
            "<b>Система:</b>\n"
            "/sheltertest - Проверка подключения к Shelter API\n"
            "/reload_content - Перезагрузить контент\n"
            "/help - Показать эту справку\n"
        )
    else:
        help_text = (
            "📋 <b>Доступные команды:</b>\n\n"
            "<b>Основные:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n"
        )
    
    await message.answer(help_text, parse_mode="HTML")
