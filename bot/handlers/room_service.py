from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from db.models import TicketType
from services.admins import notify_admins_about_ticket
from services.content import content_manager
from services.guest_context import get_active_room_number
from services.tickets import TicketRateLimitExceededError, create_ticket
from bot.keyboards.main_menu import build_room_service_cleaning_slots_keyboard


router = Router()

TECH_ALLOWED = {
    "отопление": "отопление",
    "вода": "вода",
    "электричество": "электричество",
    "wi-fi": "Wi-Fi",
    "wifi": "Wi-Fi",
    "оборудование": "оборудование",
}

EXTRA_ALLOWED = {
    "вода": "питьевая вода",
    "питьевая вода": "питьевая вода",
    "чай": "чай",
    "кофе": "кофе-капсулы",
    "кофе-капсулы": "кофе-капсулы",
    "кофе капсулы": "кофе-капсулы",
}

PILLOW_ALLOWED = {
    "ортопедическая": "ортопедическая",
    "memory foam": "memory foam",
    "мягкая": "мягкая",
    "гипоаллергенная": "гипоаллергенная",
}


async def _continue_room_service_flow(message: Message, state: FSMContext, branch: str) -> None:
    if branch == "technical_problem":
        await state.set_state(FlowState.room_service_technical_category)
        await message.answer("Выберите тип проблемы:\n• отопление\n• вода\n• электричество\n• Wi‑Fi\n• оборудование")
        return
    if branch == "extra_to_room":
        await state.set_state(FlowState.room_service_extra_item)
        await message.answer(
            "🚰 Дополнительно в номер\n"
            "• питьевая вода\n• чай\n• кофе-капсулы\n\n"
            "С удовольствием подготовим всё необходимое для вашего комфорта.\n"
            "Пожалуйста, выберите нужные позиции (можно несколько через запятую)."
        )
        return
    if branch == "cleaning":
        await state.set_state(FlowState.room_service_cleaning_time)
        await message.answer(
            content_manager.get_text("room_service.cleaning.prompt_time"),
            reply_markup=build_room_service_cleaning_slots_keyboard(),
        )
        return
    if branch == "pillow_menu":
        await state.set_state(FlowState.room_service_pillow_choice)
        await message.answer("💤 Выберите подушку:\n• ортопедическая\n• memory foam\n• мягкая\n• гипоаллергенная")
        return
    if branch == "other":
        await state.set_state(FlowState.room_service_other_text)
        await message.answer(content_manager.get_text("room_service.other.prompt_text"))


@router.callback_query(FlowState.room_service_choosing_branch)
async def choose_room_service_branch(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    key = callback.data or ""

    mapping = {
        "rs_technical_problem": "technical_problem",
        "rs_extra_to_room": "extra_to_room",
        "rs_cleaning": "cleaning",
        "rs_pillow_menu": "pillow_menu",
        "rs_other": "other",
    }
    branch = mapping.get(key)
    if not branch:
        return

    await state.update_data(service_branch=branch)
    room_number = get_active_room_number(str(callback.from_user.id))
    if room_number:
        await state.update_data(room_number=room_number)
        await _continue_room_service_flow(callback.message, state, branch)
        return

    await state.set_state(FlowState.room_service_room_number)
    await callback.message.answer("🏠 Укажите номер вашей комнаты:")


@router.message(FlowState.room_service_room_number)
async def room_service_room_number(message: Message, state: FSMContext) -> None:
    room_number = message.text or ""
    await state.update_data(room_number=room_number)
    
    data = await state.get_data()
    branch = data.get("service_branch", "")
    await _continue_room_service_flow(message, state, branch)


@router.message(FlowState.room_service_technical_category)
async def room_service_technical_category(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lower()
    category = TECH_ALLOWED.get(raw, "")
    if not category:
        await message.answer("Пожалуйста, выберите одно из значений: отопление, вода, электричество, Wi‑Fi, оборудование.")
        return
    await state.update_data(technical_category=category)
    await state.set_state(FlowState.room_service_technical_details)
    await message.answer("Опишите, пожалуйста, что произошло (кратко).")


@router.message(FlowState.room_service_technical_details)
async def room_service_technical_details(message: Message, state: FSMContext) -> None:
    details = message.text or ""
    data = await state.get_data()
    category = data.get("technical_category", "")
    room_number = data.get("room_number", "")

    payload = {
        "branch": "technical_problem",
        "category": category,
        "details": details,
    }

    summary_template = content_manager.get_text("room_service.technical_problem.summary")
    summary = summary_template.format(category=category, details=details)

    try:
        ticket = create_ticket(
            type_=TicketType.ROOM_SERVICE,
            guest_chat_id=str(message.from_user.id),
            guest_name=message.from_user.full_name,
            room_number=room_number,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        warning = content_manager.get_text("tickets.rate_limited")
        await message.answer(warning)
        from bot.keyboards.main_menu import build_main_reply_keyboard
        await state.clear()
        await message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=build_main_reply_keyboard()
        )
        return

    await message.answer(
        "Благодарим за обращение.\n"
        "Мы уже передали информацию администратору, и он займётся вопросом в ближайшее время."
    )

    from aiogram import Bot

    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )


@router.message(FlowState.room_service_extra_item)
async def room_service_extra_item(message: Message, state: FSMContext) -> None:
    raw_items = [(x or "").strip().lower() for x in (message.text or "").split(",")]
    items = []
    for raw in raw_items:
        mapped = EXTRA_ALLOWED.get(raw)
        if mapped and mapped not in items:
            items.append(mapped)

    if not items:
        await message.answer("Выберите позиции из списка: питьевая вода, чай, кофе-капсулы (можно через запятую).")
        return

    data = await state.get_data()
    room_number = data.get("room_number", "")

    payload = {
        "branch": "extra_to_room",
        "items": items,
    }

    summary = f"Дополнительно в номер: {', '.join(items)}."

    ticket = create_ticket(
        type_=TicketType.ROOM_SERVICE,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        room_number=room_number,
        payload=payload,
        initial_message=summary,
    )

    await message.answer(
        "С удовольствием подготовим всё необходимое для вашего комфорта.\n"
        "Заявка передана администратору."
    )

    from aiogram import Bot

    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )


@router.message(FlowState.room_service_cleaning_time)
async def room_service_cleaning_time(message: Message, state: FSMContext) -> None:
    cleaning_time = (message.text or "").strip()
    allowed_slots = {
        "09:00-10:30",
        "10:30-12:00",
        "12:00-13:30",
        "13:30-15:00",
        "15:00-16:30",
    }
    if cleaning_time not in allowed_slots:
        await message.answer(
            "Уборка доступна только в слотах 09:00–16:30. Выберите один из предложенных слотов:",
            reply_markup=build_room_service_cleaning_slots_keyboard(),
        )
        return
    await state.update_data(cleaning_time=cleaning_time)
    await state.set_state(FlowState.room_service_cleaning_comments)
    await message.answer("В какое время вам будет удобно провести уборку номера?\nПри необходимости добавьте комментарии.")


@router.callback_query(FlowState.room_service_cleaning_time, F.data.startswith("rs_cleaning_slot:"))
async def room_service_cleaning_slot(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    cleaning_time = (callback.data or "").split(":", 1)[1]
    await state.update_data(cleaning_time=cleaning_time)
    await state.set_state(FlowState.room_service_cleaning_comments)
    await callback.message.answer(
        f"Вы выбрали слот: {cleaning_time}\n"
        "При необходимости добавьте комментарии к уборке (или отправьте «-»)."
    )


@router.message(FlowState.room_service_cleaning_comments)
async def room_service_cleaning_comments(message: Message, state: FSMContext) -> None:
    comments = (message.text or "").strip()
    if comments in {"-", "нет", "Нет"}:
        comments = ""
    data = await state.get_data()
    cleaning_time = data.get("cleaning_time", "")
    room_number = data.get("room_number", "")

    payload = {
        "branch": "cleaning",
        "cleaning_time": cleaning_time,
        "comments": comments,
    }

    summary_template = content_manager.get_text("room_service.cleaning.summary")
    room_display = room_number or "не указан"
    summary = summary_template.format(
        room_number=room_display,
        cleaning_time=cleaning_time,
        comments=comments or "—",
    )

    ticket = create_ticket(
        type_=TicketType.ROOM_SERVICE,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        room_number=room_number,
        payload=payload,
        initial_message=summary,
    )

    confirmation = content_manager.get_text("tickets.created_confirmation")
    await message.answer(confirmation.format(ticket_id=ticket.id))

    from aiogram import Bot

    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )


@router.message(FlowState.room_service_pillow_choice)
async def room_service_pillow_choice(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lower()
    choice = PILLOW_ALLOWED.get(raw, "")
    if not choice:
        await message.answer("Пожалуйста, выберите один вариант: ортопедическая, memory foam, мягкая, гипоаллергенная.")
        return
    data = await state.get_data()
    room_number = data.get("room_number", "")

    payload = {
        "branch": "pillow_menu",
        "choice": choice,
    }

    summary_template = content_manager.get_text("room_service.pillow_menu.summary")
    summary = summary_template.format(choice=choice)

    ticket = create_ticket(
        type_=TicketType.ROOM_SERVICE,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        room_number=room_number,
        payload=payload,
        initial_message=summary,
    )

    confirmation = content_manager.get_text("tickets.created_confirmation")
    await message.answer(confirmation.format(ticket_id=ticket.id))

    from aiogram import Bot

    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )


@router.message(FlowState.room_service_other_text)
async def room_service_other_text(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    data = await state.get_data()
    room_number = data.get("room_number", "")

    payload = {
        "branch": "other",
        "text": text,
    }

    summary_template = content_manager.get_text("room_service.other.summary")
    summary = summary_template.format(text=text)

    ticket = create_ticket(
        type_=TicketType.ROOM_SERVICE,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        room_number=room_number,
        payload=payload,
        initial_message=summary,
    )

    confirmation = content_manager.get_text("tickets.created_confirmation")
    await message.answer(confirmation.format(ticket_id=ticket.id))

    from aiogram import Bot

    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )
