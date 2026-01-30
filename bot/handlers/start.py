from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from bot.keyboards.main_menu import build_segment_keyboard
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
async def cmd_start(message: Message, state: FSMContext) -> None:
    from db.session import SessionLocal
    from services.tickets import is_user_admin
    from bot.keyboards.main_menu import build_admin_panel_menu
    
    user_id = str(message.from_user.id)
    
    # Check if user is admin
    with SessionLocal() as session:
        if is_user_admin(session, user_id):
            # Show admin panel instead of guest menu
            from services.tickets import get_pending_tickets, get_all_active_tickets
            pending_count = len(get_pending_tickets(session))
            all_count = len(get_all_active_tickets(session))
            
            admin_greeting = (
                f"👨‍💼 <b>Добро пожаловать в админ-панель отеля GORA</b>\n\n"
                f"📊 Активных заявок: {all_count}\n"
                f"⏳ Ожидают решения: {pending_count}\n\n"
                f"Выберите действие:"
            )
            
            await state.clear()
            await message.answer(admin_greeting, reply_markup=build_admin_panel_menu(), parse_mode="HTML")
            return
    
    # Regular guest flow
    greeting = content_manager.get_text("greeting.start")
    season = get_current_season()
    seasonal_text = content_manager.get_text(f"seasons.{season}")
    
    choice_prompt = content_manager.get_text("menus.segment_choice_prompt")

    await state.set_state(FlowState.choosing_segment)
    await message.answer(f"{greeting}\n\n{seasonal_text}")
    await message.answer(choice_prompt, reply_markup=build_segment_keyboard())


@router.callback_query(F.data.in_({"segment_pre_arrival", "segment_in_house"}))
async def segment_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    # Handlers moved to check_in.py to avoid state conflicts
    pass


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
