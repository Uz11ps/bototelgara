from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from db.models import TicketType
from services.admins import notify_admins_about_ticket
from services.content import content_manager
from services.tickets import TicketRateLimitExceededError, create_ticket


router = Router()


@router.callback_query(FlowState.room_service_choosing_branch)
async def choose_room_service_branch(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    key = callback.data or ""

    if key == "rs_technical_problem":
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch="technical_problem")
        await callback.message.answer("Укажите номер вашей комнаты:")
    elif key == "rs_extra_to_room":
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch="extra_to_room")
        await callback.message.answer("Укажите номер вашей комнаты:")
    elif key == "rs_cleaning":
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch="cleaning")
        await callback.message.answer("Укажите номер вашей комнаты:")
    elif key == "rs_pillow_menu":
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch="pillow_menu")
        await callback.message.answer("Укажите номер вашей комнаты:")
    elif key == "rs_other":
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch="other")
        await callback.message.answer("Укажите номер вашей комнаты:")


@router.message(FlowState.room_service_room_number)
async def room_service_room_number(message: Message, state: FSMContext) -> None:
    room_number = message.text or ""
    await state.update_data(room_number=room_number)
    
    data = await state.get_data()
    branch = data.get("service_branch", "")
    
    if branch == "technical_problem":
        await state.set_state(FlowState.room_service_technical_category)
        await message.answer(
            content_manager.get_text("room_service.technical_problem.prompt_category"),
        )
    elif branch == "extra_to_room":
        await state.set_state(FlowState.room_service_extra_item)
        await message.answer(
            content_manager.get_text("room_service.extra_to_room.prompt_item"),
        )
    elif branch == "cleaning":
        await state.set_state(FlowState.room_service_cleaning_time)
        await message.answer(
            content_manager.get_text("room_service.cleaning.prompt_time"),
        )
    elif branch == "pillow_menu":
        await state.set_state(FlowState.room_service_pillow_choice)
        await message.answer(
            content_manager.get_text("room_service.pillow_menu.prompt_choice"),
        )
    elif branch == "other":
        await state.set_state(FlowState.room_service_other_text)
        await message.answer(
            content_manager.get_text("room_service.other.prompt_text"),
        )


@router.message(FlowState.room_service_technical_category)
async def room_service_technical_category(message: Message, state: FSMContext) -> None:
    category = message.text or ""
    await state.update_data(technical_category=category)
    await state.set_state(FlowState.room_service_technical_details)
    await message.answer(content_manager.get_text("room_service.technical_problem.prompt_details"))


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


@router.message(FlowState.room_service_extra_item)
async def room_service_extra_item(message: Message, state: FSMContext) -> None:
    item = message.text or ""
    await state.update_data(extra_item=item)
    await state.set_state(FlowState.room_service_extra_quantity)
    await message.answer(content_manager.get_text("room_service.extra_to_room.prompt_quantity"))


@router.message(FlowState.room_service_extra_quantity)
async def room_service_extra_quantity(message: Message, state: FSMContext) -> None:
    quantity_raw = message.text or "1"
    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 1

    data = await state.get_data()
    item = data.get("extra_item", "")
    room_number = data.get("room_number", "")

    payload = {
        "branch": "extra_to_room",
        "item": item,
        "quantity": quantity,
    }

    summary_template = content_manager.get_text("room_service.extra_to_room.summary")
    summary = summary_template.format(item=item, quantity=quantity)

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


@router.message(FlowState.room_service_cleaning_time)
async def room_service_cleaning_time(message: Message, state: FSMContext) -> None:
    cleaning_time = message.text or ""
    await state.update_data(cleaning_time=cleaning_time)
    await state.set_state(FlowState.room_service_cleaning_comments)
    await message.answer(content_manager.get_text("room_service.cleaning.prompt_comments"))


@router.message(FlowState.room_service_cleaning_comments)
async def room_service_cleaning_comments(message: Message, state: FSMContext) -> None:
    comments = message.text or ""
    data = await state.get_data()
    cleaning_time = data.get("cleaning_time", "")
    room_number = data.get("room_number", "")

    payload = {
        "branch": "cleaning",
        "cleaning_time": cleaning_time,
        "comments": comments,
    }

    summary_template = content_manager.get_text("room_service.cleaning.summary")
    summary = summary_template.format(cleaning_time=cleaning_time, comments=comments)

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
    choice = message.text or ""
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
